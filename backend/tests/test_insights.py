import io
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    email = f"insight_test_{uuid.uuid4().hex[:6]}@datavizai.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Insight Tester"}
    )
    login_res = client.post(
        "/api/auth/login",
        data={"username": email, "password": "password123"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def dataset_id(auth_headers):
    # Small CSV dataset with correlation, missingness, constant value, and skewness
    csv_content = (
        "x_coord,y_coord,constant_col,skewed_col,missing_col\n"
        "1.0,2.0,2026,Active,10\n"
        "2.0,4.0,2026,Active,\n"
        "3.0,6.0,2026,Active,30\n"
        "4.0,8.0,2026,Pending,\n"
        "5.0,10.0,2026,Active,50\n"
    )
    file_payload = {"file": ("test_insights.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert upload_res.status_code == 200
    return upload_res.json()["metadata"]["id"]

def test_generate_insights_flow(auth_headers, dataset_id):
    insights_res = client.get(f"/api/datasets/{dataset_id}/insights", headers=auth_headers)
    assert insights_res.status_code == 200
    insights = insights_res.json()
    
    assert len(insights) > 0
    # Check shape of insights
    for insight in insights:
        assert "insight_type" in insight
        assert "message" in insight
        assert "significance" in insight
        assert "severity" in insight
        
    # Check that we have a correlation insight (x_coord and y_coord correlate 100%!)
    corr_insights = [i for i in insights if i["insight_type"] == "correlation"]
    assert len(corr_insights) > 0
    assert "x_coord" in corr_insights[0]["message"]
    assert "y_coord" in corr_insights[0]["message"]
    
    # Check constant column alert
    const_insights = [i for i in insights if i["insight_type"] == "constant"]
    assert len(const_insights) > 0
    assert "constant_col" in const_insights[0]["message"]
    
    # Check skewed column alert
    skew_insights = [i for i in insights if i["insight_type"] == "skewness"]
    assert len(skew_insights) > 0
    assert "skewed_col" in skew_insights[0]["message"]
    
    # Check missingness alert
    missing_insights = [i for i in insights if i["insight_type"] == "missingness"]
    assert len(missing_insights) > 0
    assert "missing_col" in missing_insights[0]["message"]
