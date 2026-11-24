# SiteSense Backend - Integration & Orchestration Layer

## Overview
SiteSense is a **Multimodal Operations Intelligence Platform** that automates physical site compliance and condition inspections.

The backend acts as the central **integration and orchestration layer** connecting all 8 core disciplines:
- **M1 – Computer Vision**: Detections, tracking, spatial zones, text-in-images, and visual evidence generation.
- **M2 – Knowledge / Document Intelligence**: Policy chunking, embeddings, hybrid retrieval (dense + BM25), reranking, and document extraction.
- **M3 – GenAI**: Grounded Q&A with citations, multimodal visual QA, and inspection report generation.
- **M4 – Agentic Layer**: ReAct loop, tool registry, query router, human-in-the-loop approvals, and guardrails.
- **M5 – Backend and APIs**: API gateway, auth & RBAC, SSE streaming, async job queue, and audit trails.
- **M6 – Frontend**: Multi-format upload, inspection detail view, trace viewer, review queue, and dashboards.
- **M7 – Evaluation and Observability**: Golden test sets, automated eval harness, end-to-end tracing, and cost/latency tracking.
- **M8 – Security, Deployment and Documentation**: Environment config, PII protection, containerization, and seed data.

---

## Component 1 – Backend Foundation
- FastAPI base framework with lifespan and graceful connection pooling.
- Versioned endpoints (`/api/v1`).
- Centralized exception handling enforcing the uniform shape:
  ```json
  { "error": { "code": "NOT_FOUND", "message": "...", "detail": null } }
  ```
- Request correlation tracking via `X-Request-ID` and timing (`X-Process-Time-Ms`).
- Interactive Swagger documentation at `/docs` and OpenAPI schema at `/api/v1/openapi.json`.

---

## Component 2 – Database and Data Models
PostgreSQL (Neon) + SQLAlchemy 2.0 + Alembic schema across 6 operational groups (24 tables):
- **Group A (User & Site)**: `users`, `sites`, `site_memberships`, `refresh_tokens`
- **Group B (Inspection & Media)**: `inspections`, `media`, `jobs`
- **Group C (Computer Vision)**: `detections`, `tracking_results`, `zone_configs`
- **Group D (Knowledge & Compliance)**: `policies`, `policy_chunks`, `extractions`, `rules`, `findings`
- **Group E (Agent & Human Review)**: `chat_sessions`, `chat_messages`, `agent_runs`, `agent_tool_calls`, `reviews`, `tickets`
- **Group F (System Management)**: `reports`, `notifications`, `audit_logs`

---

## Component 3 – Authentication and RBAC

### Security Architecture
- **Password Hashing**: Direct `bcrypt` with work factor 12.
- **Access Tokens**: Short-lived JWT Bearer tokens signed with HMAC-SHA256.
- **Refresh Tokens**: Long-lived cryptographic tokens with unique `jti` nonces, tracked in `refresh_tokens`.
- **Token Rotation**: Every `/auth/refresh` request revokes the previous refresh token and issues a new pair, mitigating replay attacks.
- **Revocation on Logout**: `POST /auth/logout` explicitly invalidates the refresh token in PostgreSQL.

### RBAC Hierarchy & Permissions
Enforced at the API level via `RoleChecker` dependency injection (`app/api/deps.py`):
1. **Admin**: Unrestricted superuser access across all sites, rules, and system administration.
2. **Manager**: Management dashboard, cross-site analytics, and ticket approval authority.
3. **Field User**: Field media upload and inspection submission, scoped to permitted sites.
4. **Reviewer**: Document extraction and low-confidence detection human review queue.

> **Acid Test Acceptance Criteria**: A field user calling a manager-only endpoint directly receives **HTTP 403 Forbidden** (`code: FORBIDDEN`).

### Authentication Endpoints (`/api/v1/auth`)
| Method | Endpoint | Purpose | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain token pair | Public |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token for a new access token | Public (valid token) |
| `POST` | `/api/v1/auth/logout` | Revoke active refresh token session | Public |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Authenticated |
| `POST` | `/api/v1/auth/change-password` | Update user password and revoke all sessions | Authenticated |
| `GET` | `/api/v1/auth/rbac-test/manager-only` | Verify Manager / Admin role access | Manager, Admin |
| `GET` | `/api/v1/auth/rbac-test/admin-only` | Verify Admin role access | Admin |

### Default Demo Accounts (Neon PostgreSQL)
All accounts initialized with default password: `SiteSense@2026`
- **Admin**: `admin@sitesense.io` (Role: `admin`)
- **Operations Manager**: `manager@sitesense.io` (Role: `manager`)
- **Field Supervisor**: `field1@sitesense.io` (Role: `field`)
- **Compliance Reviewer**: `reviewer1@sitesense.io` (Role: `reviewer`)

---

## Component 4 – REST API Layer

Provides clean, typed, RESTful endpoints wrapping all business domains without raw database logic in handlers:

### 1. Sites (`/api/v1/sites`)
- `GET /api/v1/sites`: List accessible sites with pagination. Scoped by site membership for field users; global for managers/admins.
- `GET /api/v1/sites/{id}`: Site detail including active zone count and inspection statistics.
- `POST /api/v1/sites`: Create physical site (*Admin only*).
- `PUT /api/v1/sites/{id}`: Update site metadata (*Admin only*).

### 2. Inspections (`/api/v1/inspections`)
- `GET /api/v1/inspections`: Filterable list by `site_id`, `status` (`pending`, `processing`, `completed`, `failed`), and date range (`from_date`, `to_date`).
- `GET /api/v1/inspections/{id}`: Multi-discipline inspection view aggregating media items, CV detections with pixel coordinates `[x1, y1, x2, y2]`, compliance findings, policy citations, human reviews, and remediation tickets.
- `POST /api/v1/inspections`: Initialize new inspection session (*Field, Manager, Admin*).
- `PATCH /api/v1/inspections/{id}`: Update inspection status and metadata.

### 3. Compliance Rules (`/api/v1/rules`)
- `GET /api/v1/rules`: List machine-readable compliance rules evaluated against detections and extractions (*Manager, Admin*).
- `GET /api/v1/rules/{id}`: Get specific rule parameters, severity, and policy clause citation.
- `POST /api/v1/rules`: Create compliance rule (*Admin only*).
- `PUT /api/v1/rules/{id}`: Update rule configuration (*Admin only*).

### 4. Spatial Zones & Counting Lines (`/api/v1/zones`)
- `GET /api/v1/zones?site_id=...`: Retrieve spatial clear zones (polygons) and crossing/counting lines for CV spatial logic.
- `POST /api/v1/zones`: Register new polygon zone or counting line geometry (*Admin only*).

### 5. Remediation Tickets (`/api/v1/tickets`)
- `GET /api/v1/tickets`: List remediation tickets with status and finding filters (*Manager, Admin*).
- `POST /api/v1/tickets`: Raise remediation ticket linked to a compliance finding.
- `POST /api/v1/tickets/{id}/approve`: Human-in-the-loop review workflow to approve or reject proposed tickets with reviewer notes (*Manager, Admin*).

---

## Component 5 – Media and File Management

Enforces the core rule: **Original binary files are stored outside PostgreSQL; metadata and storage paths are stored in PostgreSQL.**

### Architecture & Security
- **Path Isolation & Sanitization**: Filenames are sanitized and isolated inside subfolders partitioned by inspection ID (`media_storage/<inspection_id>/<hash>_<filename>`), eliminating directory traversal risks.
- **Streaming & Buffer Limits**: Large video and multi-megabyte photo uploads stream in 1MB chunks directly to disk with active byte accounting, preventing server memory spikes.
- **Automated Metadata Extraction**: Image files are analyzed via Pillow during upload to automatically record pixel dimensions (`width`, `height`), color mode, format, and SHA256 checksum in `metadata_json`.
- **Validation**: Enforces allowed extensions (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.mp4`, `.mov`, `.avi`, `.pdf`, `.csv`, `.json`) and maximum upload limits (`MAX_UPLOAD_SIZE_MB`, default 100MB).
- **Site-Scoped Access & Ownership**: Field users can only upload media to inspections at sites where they hold active membership; downloading and deletion respect site and ownership boundaries.

### Media Endpoints (`/api/v1/media` & `/api/v1/inspections/{id}/media`)
| Method | Endpoint | Purpose | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/media/upload` | Multipart form upload (`inspection_id` + `file`) | Field, Manager, Admin |
| `POST` | `/api/v1/media/batch-upload` | Batch upload multiple files simultaneously | Field, Manager, Admin |
| `POST` | `/api/v1/inspections/{id}/media` | Direct upload nested under an inspection session | Field, Manager, Admin |
| `GET` | `/api/v1/inspections/{id}/media` | List all media files attached to an inspection | Authenticated (site access) |
| `GET` | `/api/v1/media/{id}` | Retrieve media record metadata and download URL | Authenticated (site access) |
| `GET` | `/api/v1/media/{id}/download` | Stream raw media binary with correct MIME type | Authenticated (site access) |
| `GET` | `/api/v1/media/{id}/annotated` | Stream annotated media with rendered YOLO bounding boxes | Authenticated (site access) |
| `DELETE` | `/api/v1/media/{id}` | Permanently delete media record and storage file | Manager, Admin, or Author |

---

## Running Automated Tests
```powershell
pytest -v
```
All 35 foundation, database model, authentication RBAC, REST API, and media storage tests pass:
```text
============================= 35 passed in 10.48s =============================
```
