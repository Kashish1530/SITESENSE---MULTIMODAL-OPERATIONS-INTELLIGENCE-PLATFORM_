import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal
from app.models.users_sites import User


@pytest.fixture(scope="module")
def setup_auth_users():
    """Ensure demo users exist in the test database with known passwords."""
    session: Session = SessionLocal()
    default_pwd_hash = hash_password("SiteSense@2026")

    users_data = [
        {"name": "Admin Tester", "email": "admin_test@sitesense.io", "role": "admin"},
        {"name": "Manager Tester", "email": "manager_test@sitesense.io", "role": "manager"},
        {"name": "Field Tester", "email": "field_test@sitesense.io", "role": "field"},
        {"name": "Reviewer Tester", "email": "reviewer_test@sitesense.io", "role": "reviewer"},
    ]

    created_users = []
    for data in users_data:
        existing = session.query(User).filter(User.email == data["email"]).first()
        if not existing:
            u = User(
                name=data["name"],
                email=data["email"],
                role=data["role"],
                password_hash=default_pwd_hash,
            )
            session.add(u)
            session.flush()
            created_users.append(u)
        else:
            existing.password_hash = default_pwd_hash
            created_users.append(existing)

    session.commit()
    session.close()
    return created_users


def test_password_hashing():
    """Verify bcrypt password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password(password, None) is False


def test_login_success(client: TestClient, setup_auth_users):
    """Verify POST /api/v1/auth/login issues valid access & refresh token pair."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "manager_test@sitesense.io", "password": "SiteSense@2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "manager_test@sitesense.io"
    assert data["user"]["role"] == "manager"


def test_login_invalid_credentials(client: TestClient, setup_auth_users):
    """Verify POST /api/v1/auth/login fails on invalid credentials with standard error format."""
    # 1. Wrong password
    res_wrong_pw = client.post(
        "/api/v1/auth/login",
        json={"email": "manager_test@sitesense.io", "password": "IncorrectPassword"},
    )
    assert res_wrong_pw.status_code == 401
    err_data = res_wrong_pw.json()
    assert err_data["error"]["code"] == "UNAUTHORIZED"

    # 2. Non-existent email
    res_no_user = client.post(
        "/api/v1/auth/login",
        json={"email": "non_existent@sitesense.io", "password": "SiteSense@2026"},
    )
    assert res_no_user.status_code == 401
    assert res_no_user.json()["error"]["code"] == "UNAUTHORIZED"


def test_get_me_endpoint(client: TestClient, setup_auth_users):
    """Verify GET /api/v1/auth/me returns caller profile with valid token, or 401 without."""
    # 1. Without token -> 401
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401

    # 2. Login to get token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "field_test@sitesense.io", "password": "SiteSense@2026"},
    )
    token = login_res.json()["token"]

    # 3. With token -> 200
    auth_res = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert auth_res.status_code == 200
    me_data = auth_res.json()
    assert me_data["email"] == "field_test@sitesense.io"
    assert me_data["role"] == "field"


def test_refresh_token_rotation(client: TestClient, setup_auth_users):
    """Verify POST /api/v1/auth/refresh rotates the token and revokes the prior one."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "reviewer_test@sitesense.io", "password": "SiteSense@2026"},
    )
    old_refresh_token = login_res.json()["refresh_token"]

    # Refresh token
    refresh_res = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert "token" in new_data
    assert "refresh_token" in new_data
    new_refresh_token = new_data["refresh_token"]
    assert new_refresh_token != old_refresh_token

    # Reusing the old refresh token must be rejected (Token Rotation)
    reuse_res = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert reuse_res.status_code == 401
    assert reuse_res.json()["error"]["code"] == "UNAUTHORIZED"


def test_logout_revokes_token(client: TestClient, setup_auth_users):
    """Verify POST /api/v1/auth/logout revokes refresh token."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_test@sitesense.io", "password": "SiteSense@2026"},
    )
    refresh_token = login_res.json()["refresh_token"]

    logout_res = client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_res.status_code == 200

    # Refreshing with logged out token fails
    retry_res = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert retry_res.status_code == 401


def test_role_based_access_control_enforcement(client: TestClient, setup_auth_users):
    """Acid Test for Acceptance Criteria:
    'A field user is refused a manager-only endpoint at the API even when calling it directly.'
    """
    # 1. Field user token
    field_login = client.post(
        "/api/v1/auth/login",
        json={"email": "field_test@sitesense.io", "password": "SiteSense@2026"},
    )
    field_token = field_login.json()["token"]

    # Field user tries to call manager-only endpoint -> 403 Forbidden
    field_attempt = client.get(
        "/api/v1/auth/rbac-test/manager-only",
        headers={"Authorization": f"Bearer {field_token}"},
    )
    assert field_attempt.status_code == 403
    assert field_attempt.json()["error"]["code"] == "FORBIDDEN"

    # Field user tries to call admin-only endpoint -> 403 Forbidden
    field_admin_attempt = client.get(
        "/api/v1/auth/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {field_token}"},
    )
    assert field_admin_attempt.status_code == 403

    # 2. Manager user token
    manager_login = client.post(
        "/api/v1/auth/login",
        json={"email": "manager_test@sitesense.io", "password": "SiteSense@2026"},
    )
    manager_token = manager_login.json()["token"]

    # Manager calls manager-only endpoint -> 200 OK
    mgr_res = client.get(
        "/api/v1/auth/rbac-test/manager-only",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert mgr_res.status_code == 200
    assert mgr_res.json()["status"] == "granted"

    # Manager tries to call admin-only endpoint -> 403 Forbidden
    mgr_admin_attempt = client.get(
        "/api/v1/auth/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert mgr_admin_attempt.status_code == 403

    # 3. Admin user token
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_test@sitesense.io", "password": "SiteSense@2026"},
    )
    admin_token = admin_login.json()["token"]

    # Admin calls manager-only -> 200 OK
    adm_mgr_res = client.get(
        "/api/v1/auth/rbac-test/manager-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert adm_mgr_res.status_code == 200

    # Admin calls admin-only -> 200 OK
    adm_res = client.get(
        "/api/v1/auth/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert adm_res.status_code == 200
