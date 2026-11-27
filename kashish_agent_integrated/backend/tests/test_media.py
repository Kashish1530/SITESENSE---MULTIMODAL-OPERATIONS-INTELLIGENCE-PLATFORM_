import io
from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.inspections_media import Inspection, Media
from app.models.users_sites import Site, SiteMembership, User
from app.services.storage_service import storage_service

settings = get_settings()


def create_test_image_bytes(width: int = 640, height: int = 480, format: str = "JPEG") -> bytes:
    """Helper to generate mock image in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(255, 100, 50))
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture(scope="module")
def media_test_setup():
    """Seed users, site, and inspection for media tests."""
    session: Session = SessionLocal()
    default_pw = hash_password("SiteSense@2026")

    # 1. Users
    manager = User(
        name="Media Manager",
        email=f"media_mgr_{uuid.uuid4().hex[:6]}@sitesense.io",
        role="manager",
        password_hash=default_pw,
    )
    field_user = User(
        name="Media Field",
        email=f"media_field_{uuid.uuid4().hex[:6]}@sitesense.io",
        role="field",
        password_hash=default_pw,
    )
    unauthorized_field = User(
        name="Unauthorized Field",
        email=f"media_unauth_{uuid.uuid4().hex[:6]}@sitesense.io",
        role="field",
        password_hash=default_pw,
    )
    session.add_all([manager, field_user, unauthorized_field])
    session.flush()

    # 2. Main Site
    site = Site(
        name="Media Test Site",
        type="warehouse",
        location="Depot 12, West Zone",
        active=True,
    )
    session.add(site)
    session.flush()

    # Membership for authorized field user
    session.add(SiteMembership(user_id=field_user.id, site_id=site.id))

    # 3. Main Inspection
    inspection = Inspection(
        site_id=site.id,
        user_id=field_user.id,
        status="pending",
        summary="Media test inspection",
    )
    session.add(inspection)
    session.flush()

    # 4. Restricted Site & Inspection (field user does not have membership)
    restricted_site = Site(
        name="Restricted Site B",
        type="construction",
        location="Restricted Tower C",
        active=True,
    )
    session.add(restricted_site)
    session.flush()

    restricted_inspection = Inspection(
        site_id=restricted_site.id,
        status="pending",
        summary="Restricted inspection",
    )
    session.add(restricted_inspection)
    session.commit()

    context = {
        "manager_email": manager.email,
        "field_email": field_user.email,
        "unauthorized_email": unauthorized_field.email,
        "site_id": str(site.id),
        "inspection_id": str(inspection.id),
        "restricted_inspection_id": str(restricted_inspection.id),
    }
    session.close()
    return context


def get_token(client: TestClient, email: str) -> str:
    res = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": email, "password": "SiteSense@2026"},
    )
    assert res.status_code == 200, res.text
    return res.json()["token"]


def test_upload_image_and_metadata_extraction(client: TestClient, media_test_setup):
    token = get_token(client, media_test_setup["manager_email"])
    img_bytes = create_test_image_bytes(800, 600, "JPEG")

    files = {
        "file": ("site_photo.jpg", img_bytes, "image/jpeg"),
    }
    data = {
        "inspection_id": media_test_setup["inspection_id"],
    }

    res = client.post(
        f"{settings.API_V1_PREFIX}/media/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert "media" in body
    media = body["media"]
    assert media["type"] == "image"
    assert media["filename"] == "site_photo.jpg"
    assert media["file_size_bytes"] == len(img_bytes)
    assert media["metadata"]["width"] == 800
    assert media["metadata"]["height"] == 600
    assert "sha256" in media["metadata"]
    assert "download_url" in media


def test_download_and_stream_media_file(client: TestClient, media_test_setup):
    token = get_token(client, media_test_setup["manager_email"])
    img_bytes = create_test_image_bytes(320, 240, "PNG")

    # 1. Upload
    upload_res = client.post(
        f"{settings.API_V1_PREFIX}/media/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"inspection_id": media_test_setup["inspection_id"]},
        files={"file": ("test_capture.png", img_bytes, "image/png")},
    )
    assert upload_res.status_code == 201
    media_id = upload_res.json()["media"]["id"]

    # 2. Download via /download
    download_res = client.get(
        f"{settings.API_V1_PREFIX}/media/{media_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert download_res.status_code == 200
    assert "image/png" in download_res.headers["content-type"]
    assert len(download_res.content) == len(img_bytes)

    # 3. Retrieve metadata via GET /media/{media_id}
    meta_res = client.get(
        f"{settings.API_V1_PREFIX}/media/{media_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert meta_res.status_code == 200
    assert meta_res.json()["id"] == media_id


def test_batch_upload_media_files(client: TestClient, media_test_setup):
    token = get_token(client, media_test_setup["field_email"])
    img1 = create_test_image_bytes(200, 200, "JPEG")
    img2 = create_test_image_bytes(400, 400, "PNG")

    files = [
        ("files", ("cam1.jpg", img1, "image/jpeg")),
        ("files", ("cam2.png", img2, "image/png")),
    ]
    data = {
        "inspection_id": media_test_setup["inspection_id"],
    }

    res = client.post(
        f"{settings.API_V1_PREFIX}/media/batch-upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["total_uploaded"] == 2
    assert len(body["uploaded"]) == 2


def test_nested_inspection_media_routes(client: TestClient, media_test_setup):
    token = get_token(client, media_test_setup["manager_email"])
    pdf_bytes = b"%PDF-1.4 mock compliance delivery ticket document content"
    inspection_id = media_test_setup["inspection_id"]

    # Direct nested upload: POST /api/v1/inspections/{id}/media
    upload_res = client.post(
        f"{settings.API_V1_PREFIX}/inspections/{inspection_id}/media",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("permit_document.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201
    media_data = upload_res.json()["media"]
    assert media_data["type"] == "doc"

    # Direct nested list: GET /api/v1/inspections/{id}/media
    list_res = client.get(
        f"{settings.API_V1_PREFIX}/inspections/{inspection_id}/media",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(m["filename"] == "permit_document.pdf" for m in items)


def test_disallowed_file_extension_rejection(client: TestClient, media_test_setup):
    token = get_token(client, media_test_setup["manager_email"])
    malicious_bytes = b"MZ\x90\x00executable content"

    res = client.post(
        f"{settings.API_V1_PREFIX}/media/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"inspection_id": media_test_setup["inspection_id"]},
        files={"file": ("malware.exe", malicious_bytes, "application/octet-stream")},
    )
    assert res.status_code == 400
    err = res.json()["error"]
    assert err["code"] == "BAD_REQUEST"
    assert "Unsupported file format" in err["message"]


def test_rbac_and_site_boundary_enforcement(client: TestClient, media_test_setup):
    token = get_token(client, media_test_setup["unauthorized_email"])
    img_bytes = create_test_image_bytes(100, 100, "JPEG")

    # Unauthorized field user attempts to upload to Site A (no membership) -> Must receive 403 Forbidden
    res = client.post(
        f"{settings.API_V1_PREFIX}/media/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"inspection_id": media_test_setup["inspection_id"]},
        files={"file": ("unauthorized.jpg", img_bytes, "image/jpeg")},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_delete_media_removes_db_and_disk_file(client: TestClient, media_test_setup):
    token = get_token(client, media_test_setup["manager_email"])
    img_bytes = create_test_image_bytes(250, 250, "JPEG")

    # 1. Upload
    upload_res = client.post(
        f"{settings.API_V1_PREFIX}/media/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"inspection_id": media_test_setup["inspection_id"]},
        files={"file": ("to_delete.jpg", img_bytes, "image/jpeg")},
    )
    assert upload_res.status_code == 201
    media_id = upload_res.json()["media"]["id"]
    rel_path = upload_res.json()["media"]["path"]

    # 2. Verify disk file exists
    assert storage_service.file_exists(rel_path) is True

    # 3. Delete
    del_res = client.delete(
        f"{settings.API_V1_PREFIX}/media/{media_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 200

    # 4. Verify GET returns 404
    get_res = client.get(
        f"{settings.API_V1_PREFIX}/media/{media_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 404

    # 5. Verify deleted from disk
    assert storage_service.file_exists(rel_path) is False
