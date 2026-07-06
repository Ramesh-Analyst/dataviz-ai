import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

# Use a unique email for testing to avoid collisions
import uuid
TEST_EMAIL = f"dev_{uuid.uuid4().hex[:8]}@datavizai.com"
TEST_PASSWORD = "securepassword123"
TEST_NAME = "Lead Developer"

def test_user_onboarding_lifecycle():
    # 1. Test User Registration
    reg_response = client.post(
        "/api/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "full_name": TEST_NAME}
    )
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert reg_data["email"] == TEST_EMAIL
    assert reg_data["full_name"] == TEST_NAME
    assert "id" in reg_data
    
    # 2. Test Duplicate Email Registration Blocked
    dup_response = client.post(
        "/api/auth/register",
        json={"email": TEST_EMAIL, "password": "differentpassword", "full_name": "Clone User"}
    )
    assert dup_response.status_code == 400
    assert "already registered" in dup_response.json()["detail"]

    # 3. Test Login with Incorrect Credentials
    bad_login_response = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": "wrongpassword"}
    )
    assert bad_login_response.status_code == 401
    
    # 4. Test Login with Correct Credentials
    login_response = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    assert login_data["user"]["email"] == TEST_EMAIL
    
    token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 5. Test Access Current Profile (Protected route)
    profile_response = client.get("/api/auth/me", headers=headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["email"] == TEST_EMAIL
    assert profile_data["full_name"] == TEST_NAME

    # 6. Test Profile Access without Token fails
    unauth_profile_response = client.get("/api/auth/me")
    assert unauth_profile_response.status_code == 401

    # 7. Test Ingestion Upload on Protected route (With Token)
    csv_path = os.path.join(os.path.dirname(__file__), "sample_data.csv")
    with open(csv_path, "rb") as f:
        upload_response = client.post(
            "/api/datasets/upload",
            headers=headers,
            files={"file": ("sample_data.csv", f, "text/csv")}
        )
    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert upload_data["metadata"]["filename"] == "sample_data.csv"
    assert upload_data["metadata"]["row_count"] == 10
    
    # 8. Test Ingestion Upload on Protected route (Without Token)
    with open(csv_path, "rb") as f:
        unauth_upload_response = client.post(
            "/api/datasets/upload",
            files={"file": ("sample_data.csv", f, "text/csv")}
        )
    assert unauth_upload_response.status_code == 401
