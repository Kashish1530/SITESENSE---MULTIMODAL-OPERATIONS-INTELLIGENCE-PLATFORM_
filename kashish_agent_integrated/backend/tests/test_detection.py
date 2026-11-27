import io
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.computer_vision import Detection, ZoneConfig
from app.models.inspections_media import Inspection, Media
from app.models.users_sites import Site, SiteMembership, User
from app.services.detection_service import DetectionService, MODEL_CLASSES, point_in_polygon

settings = get_settings()


def test_yolo_weights_and_classes_configured():
    """Verify that best_3.pt is loaded with the expected 16 classes."""
    weights_path = DetectionService.get_weights_path()
    assert os.path.exists(weights_path), f"Weights file missing at {weights_path}"

    assert len(MODEL_CLASSES) == 16
    assert MODEL_CLASSES[0] == "person"
    assert MODEL_CLASSES[1] == "safety_helmet"
    assert MODEL_CLASSES[2] == "safety_vest"
    assert MODEL_CLASSES[3] == "fire_extinguisher"
    assert MODEL_CLASSES[6] == "fire"
    assert MODEL_CLASSES[7] == "spill"
    assert MODEL_CLASSES[11] == "forklift"


def test_point_in_polygon_algorithm():
    """Verify point_in_polygon ray-casting logic."""
    poly = [[0, 0], [10, 0], [10, 10], [0, 10]]
    assert point_in_polygon(5, 5, poly) is True
    assert point_in_polygon(15, 15, poly) is False
    assert point_in_polygon(-1, 5, poly) is False


def test_detection_service_inference_and_annotation(tmp_path):
    """Verify inference execution and image annotation."""
    # Create test image
    img_path = str(tmp_path / "test_frame.jpg")
    img = Image.new("RGB", (640, 640), color=(100, 100, 100))
    img.save(img_path)

    dets, latency = DetectionService.run_inference_on_file(img_path)
    assert isinstance(dets, list)
    assert latency > 0

    # Test annotation rendering
    annotated_path = str(tmp_path / "annotated_frame.jpg")
    sample_dets = [
        {"bbox": [50, 50, 200, 300], "class_name": "person", "confidence": 0.92},
        {"bbox": [80, 50, 160, 100], "class_name": "safety_helmet", "confidence": 0.88},
    ]
    annotated = DetectionService.annotate_and_save_image(img_path, annotated_path, sample_dets)
    assert annotated is True
    assert os.path.exists(annotated_path)


def test_api_media_detect_and_annotated_endpoints(client: TestClient):
    """Test POST /api/v1/media/{media_id}/detect and POST /api/v1/inspections/{insp_id}/detect."""
    session: Session = SessionLocal()
    default_pw = hash_password("SiteSense@2026")

    manager = User(
        name="Detection Manager",
        email=f"det_mgr_{uuid.uuid4().hex[:6]}@sitesense.io",
        role="manager",
        password_hash=default_pw,
    )
    session.add(manager)
    session.flush()

    site = Site(
        name="Detection Test Site",
        type="manufacturing",
        location="Sector 9",
        active=True,
    )
    session.add(site)
    session.flush()

    session.add(SiteMembership(user_id=manager.id, site_id=site.id))
    insp = Inspection(
        site_id=site.id,
        user_id=manager.id,
        status="pending",
        summary="Detection test inspection",
    )
    session.add(insp)
    session.commit()

    manager_email = manager.email
    insp_id = str(insp.id)
    session.close()

    # Get login token
    login_res = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": manager_email, "password": "SiteSense@2026"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload test image
    buf = io.BytesIO()
    Image.new("RGB", (640, 480), color=(80, 80, 80)).save(buf, format="JPEG")
    buf.seek(0)

    upload_res = client.post(
        f"{settings.API_V1_PREFIX}/inspections/{insp_id}/media",
        files={"file": ("site_camera.jpg", buf, "image/jpeg")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    media_id = upload_res.json()["media"]["id"]

    # Trigger Detection on Media
    detect_res = client.post(
        f"{settings.API_V1_PREFIX}/media/{media_id}/detect",
        headers=headers,
    )
    assert detect_res.status_code == 200
    data = detect_res.json()
    assert data["media_id"] == media_id
    assert data["model_version"] == "yolo11s_sitesense_best3"
    assert "detections" in data
    assert "class_counts" in data

    # Trigger Detection on Entire Inspection Session
    insp_detect_res = client.post(
        f"{settings.API_V1_PREFIX}/inspections/{insp_id}/detect",
        headers=headers,
    )
    assert insp_detect_res.status_code == 200
    insp_data = insp_detect_res.json()
    assert insp_data["inspection_id"] == insp_id
    assert insp_data["media_processed"] >= 1
    assert "status" in insp_data
