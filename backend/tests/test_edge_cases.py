import io
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    email = f"edge_test_{uuid.uuid4().hex[:6]}@datavizai.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Edge Tester"}
    )
    login_res = client.post(
        "/api/auth/login",
        data={"username": email, "password": "password123"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_empty_csv_fails(auth_headers):
    # Empty CSV content
    file_payload = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert res.status_code in [400, 500]

def test_one_column_csv_succeeds(auth_headers):
    # CSV with exactly one column and multiple rows
    csv_content = "sales\n100\n200\n300\n"
    file_payload = {"file": ("one_col.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["metadata"]["col_count"] == 1
    assert data["metadata"]["row_count"] == 3

def test_single_row_csv_succeeds(auth_headers):
    # CSV with multiple columns but only one data row
    csv_content = "year,sales,category\n2026,500,Furniture\n"
    file_payload = {"file": ("single_row.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["metadata"]["row_count"] == 1

def test_nulls_in_grouping_evaluation(auth_headers):
    # Grouping on columns containing nulls should not crash and group them under placeholder
    csv_content = (
        "year,category\n"
        ",Furniture\n"
        "2020,\n"
        "2020,Furniture\n"
    )
    file_payload = {"file": ("null_group.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert upload_res.status_code == 200
    ds_id = upload_res.json()["metadata"]["id"]

    query_payload = {
        "x_axis": "year",
        "y_axis": None,
        "aggregate": "count",
        "group_by": "category"
    }
    query_res = client.post(f"/api/datasets/{ds_id}/visualizations/query", json=query_payload, headers=auth_headers)
    assert query_res.status_code == 200
    datapoints = query_res.json()["datapoints"]
    
    # Placeholders should be "Missing" and "None" respectively
    years = [str(r["year"]) for r in datapoints]
    categories = [str(r["category"]) for r in datapoints]
    assert "Missing" in years or "None" in categories

def test_duplicate_rows_deduction_in_quality_score(auth_headers):
    # CSV with 100% duplicate rows (should penalize score)
    csv_content = (
        "sales,category\n"
        "100,Furniture\n"
        "100,Furniture\n"
        "100,Furniture\n"
    )
    file_payload = {"file": ("dups.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert upload_res.status_code == 200
    ds_id = upload_res.json()["metadata"]["id"]

    profile_res = client.get(f"/api/datasets/{ds_id}/profile", headers=auth_headers)
    assert profile_res.status_code == 200
    quality = profile_res.json()["quality_report"]
    # Check that duplicates are flagged and score is deducted
    assert quality["score"] < 100.0
    issues = [issue["message"] for issue in quality["issues_list"]]
    assert any("duplicate" in issue.lower() for issue in issues)

def test_all_null_column_does_not_crash_profiling(auth_headers):
    csv_content = (
        "name,age,country\n"
        "Alice,,USA\n"
        "Bob,,Canada\n"
        "Charlie,,USA\n"
    )
    file_payload = {"file": ("all_null.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert upload_res.status_code == 200
    ds_id = upload_res.json()["metadata"]["id"]
    
    profile_res = client.get(f"/api/datasets/{ds_id}/profile", headers=auth_headers)
    assert profile_res.status_code == 200
    
    profile_data = profile_res.json()
    assert "age" in profile_data["column_stats"]
    assert profile_data["column_stats"]["age"]["missing_count"] == 3
