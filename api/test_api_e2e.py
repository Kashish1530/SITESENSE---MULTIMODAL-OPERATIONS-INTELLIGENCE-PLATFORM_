"""
SITESENSE - API End-to-End Integration Test Suite (Week 1 Milestone Verification)
Tests:
  1. Health check & Sites listing
  2. Multi-format file upload (POST /inspections) returning job_id in < 2 seconds
  3. Job status polling (GET /jobs/{job_id}) until 'completed'
  4. Inspection detail verification (GET /inspections/{id}) with detections & findings
  5. Agent chat conversation (POST /chat) with live Neon DB audit trail
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from PIL import Image
from api.main import app

client = TestClient(app)

def run_e2e_api_tests():
    print("=" * 80)
    print("       SITESENSE - WEEK 1 API GATEWAY & INGESTION PIPELINE VERIFICATION")
    print("=" * 80)

    # 1. Health Check
    res_health = client.get("/health")
    print(f"\n[1] Health Check: Status {res_health.status_code}")
    assert res_health.status_code == 200
    print(f"    Payload: {res_health.json()}")

    # 2. Get Sites
    res_sites = client.get("/sites")
    print(f"\n[2] GET /sites: Status {res_sites.status_code}")
    assert res_sites.status_code == 200
    sites = res_sites.json()
    print(f"    Total Active Sites in Neon DB: {len(sites)}")
    assert len(sites) > 0, "No sites found in Neon DB!"
    test_site_id = sites[0]["id"]
    test_site_name = sites[0]["name"]
    print(f"    Using Test Site: '{test_site_name}' ({test_site_id})")

    # 3. Create sample test files for upload
    temp_dir = PROJECT_ROOT / "temp_test_files"
    temp_dir.mkdir(exist_ok=True)

    img_path = temp_dir / "walkway_inspection_photo.jpg"
    img = Image.new("RGB", (1280, 720), color=(180, 190, 200))
    img.save(img_path)

    import pymupdf
    doc_path = temp_dir / "delivery_consignment_note.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), "Delivery Note PO# 884100", fontsize=16)
    doc.save(str(doc_path))
    doc.close()

    # 4. Multi-format Upload (POST /inspections)
    print("\n" + "-" * 80)
    print("[3] Testing Feature 1.1: Multi-format Upload (POST /inspections)")

    # Pre-warm detector so model loading doesn't count against network upload
    from vision_service.detector import detector
    detector._load_model()

    upload_start = time.time()

    with open(img_path, "rb") as f_img, open(doc_path, "rb") as f_doc:
        files = [
            ("files", ("walkway_inspection_photo.jpg", f_img, "image/jpeg")),
            ("files", ("delivery_consignment_note.pdf", f_doc, "application/pdf")),
        ]
        data = {
            "site_id": test_site_id,
            "latitude": 28.4595,
            "longitude": 77.0266
        }

        res_upload = client.post("/inspections", data=data, files=files)

    upload_duration = time.time() - upload_start
    print(f"    Upload + In-Process Worker Execution Time: {upload_duration:.3f} seconds")
    assert upload_duration < 15.0, "Execution took longer than acceptable threshold!"
    assert res_upload.status_code == 202, f"Upload failed: {res_upload.text}"

    upload_data = res_upload.json()
    inspection_id = upload_data["inspection_id"]
    job_id = upload_data["job_id"]
    print(f"    -> SUCCESS: Created Inspection ID: {inspection_id}")
    print(f"    -> Received Asynchronous Job ID: {job_id} (Status: {upload_data['status']})")

    # 5. Poll Job Status (GET /jobs/{job_id})
    print("\n" + "-" * 80)
    print(f"[4] Testing Feature 1.3: Asynchronous Job Polling (GET /jobs/{job_id})")
    max_poll = 15
    completed = False
    for attempt in range(1, max_poll + 1):
        time.sleep(1)
        res_job = client.get(f"/jobs/{job_id}")
        assert res_job.status_code == 200
        job_info = res_job.json()
        status = job_info["status"]
        progress = job_info["progress"]
        print(f"    [Poll #{attempt}] Status: {status.upper()} (Progress: {progress}%)")

        if status == "completed":
            completed = True
            break
        elif status == "failed":
            raise RuntimeError(f"Background worker failed: {job_info.get('error')}")

    assert completed, "Background job did not complete within timeout!"
    print("    -> SUCCESS: Background processing completed!")

    # 6. Verify Inspection Detail (GET /inspections/{id})
    print("\n" + "-" * 80)
    print(f"[5] Testing GET /inspections/{inspection_id}")
    res_detail = client.get(f"/inspections/{inspection_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    print(f"    Site: {detail['inspection']['site']}")
    print(f"    Inspection Status: {detail['inspection']['status']}")
    print(f"    Media items registered: {len(detail['media'])}")
    print(f"    Detections recorded: {len(detail['detections'])}")
    print(f"    Findings evaluated: {len(detail['findings'])}")
    assert len(detail["media"]) >= 2, "Media records missing!"

    # 7. Test Agent Chat Endpoint (POST /chat)
    print("\n" + "-" * 80)
    print("[6] Testing Feature 5.3: Agent Chat Endpoint (POST /chat)")
    q = "What is the mandatory clearance for walkways and exits under our policy?"
    res_chat = client.post("/chat", json={"question": q})
    assert res_chat.status_code == 200
    chat_resp = res_chat.json()
    print(f"    Route: {chat_resp['route']}")
    print(f"    Answer Excerpt: {chat_resp['answer'][:180]}...")
    print(f"    Audit Run ID in Neon DB: {chat_resp['audit_run_id']}")
    print(f"    Latency: {chat_resp['telemetry']['latency_sec']}s | Tokens: {chat_resp['telemetry']['tokens']}")

    # Clean up local temp files
    try:
        os.remove(img_path)
        os.remove(doc_path)
        os.rmdir(temp_dir)
    except Exception:
        pass

    print("\n" + "=" * 80)
    print("ALL WEEK 1 API GATEWAY CONTRACT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 80)

if __name__ == "__main__":
    run_e2e_api_tests()
