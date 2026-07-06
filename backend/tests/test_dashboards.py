import io
import uuid
import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    email = f"dash_test_{uuid.uuid4().hex[:6]}@datavizai.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Dash Tester"}
    )
    login_res = client.post(
        "/api/auth/login",
        data={"username": email, "password": "password123"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def dataset_id(auth_headers):
    csv_content = (
        "country,sales,category\n"
        "USA,100,Furniture\n"
        "USA,150,Electronics\n"
        "Canada,200,Furniture\n"
        "Canada,300,Electronics\n"
    )
    file_payload = {"file": ("test_dash.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert upload_res.status_code == 200
    return upload_res.json()["metadata"]["id"]

def test_dashboard_lifecycle(auth_headers, dataset_id):
    # 1. Create a Dashboard
    dash_payload = {
        "dataset_id": dataset_id,
        "title": "Corporate Sales Performance",
        "description": "Enterprise-wide sales analytics board"
    }
    create_res = client.post("/api/dashboards", json=dash_payload, headers=auth_headers)
    assert create_res.status_code == 200
    dash_data = create_res.json()
    assert "id" in dash_data
    assert dash_data["title"] == "Corporate Sales Performance"
    # It should have auto-generated widgets since the dataset had no saved charts
    assert len(dash_data["widgets"]) > 0
    dash_uuid = dash_data["id"]
    widget_uuid = dash_data["widgets"][0]["id"]
    
    # 2. List Dashboards
    list_res = client.get(f"/api/dashboards?dataset_id={dataset_id}", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == dash_uuid
    
    # 3. Update Dashboard properties
    update_res = client.put(
        f"/api/dashboards/{dash_uuid}",
        json={"title": "Updated Sales Board", "description": "New description"},
        headers=auth_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Sales Board"
    
    # 4. Update Widget layout
    layout_payload = [
        {"id": widget_uuid, "layout": '{"x": 2, "y": 2, "w": 4, "h": 4}'}
    ]
    layout_res = client.put(f"/api/dashboards/{dash_uuid}/layouts", json=layout_payload, headers=auth_headers)
    assert layout_res.status_code == 200
    assert layout_res.json()["detail"] == "Widget layouts updated successfully."
    
    # 5. Get Dashboard details (and filter)
    details_res = client.get(f"/api/dashboards/{dash_uuid}", headers=auth_headers)
    assert details_res.status_code == 200
    details_data = details_res.json()
    assert details_data["title"] == "Updated Sales Board"
    # Verify lay out changes saved
    assert details_data["widgets"][0]["layout"] == '{"x": 2, "y": 2, "w": 4, "h": 4}'
    
    # Get dashboard details with global filters (country = USA)
    filtered_res = client.get(
        f"/api/dashboards/{dash_uuid}?filters={json.dumps({'country': 'USA'})}",
        headers=auth_headers
    )
    assert filtered_res.status_code == 200
    filtered_data = filtered_res.json()
    # Check that widget dynamic query resolved
    widget_datapoints = filtered_data["widgets"][0]["datapoints"]
    assert len(widget_datapoints) > 0
    # Every data point should be restricted to country = USA if country was used as x_axis/group_by
    for dp in widget_datapoints:
        if "country" in dp:
            assert dp["country"] == "USA"
            
    # 6. Delete Dashboard
    delete_res = client.delete(f"/api/dashboards/{dash_uuid}", headers=auth_headers)
    assert delete_res.status_code == 200
    
    # Get again should be 404
    get_again = client.get(f"/api/dashboards/{dash_uuid}", headers=auth_headers)
    assert get_again.status_code == 404

def test_pin_chart_syncs_to_existing_dashboard(auth_headers, dataset_id):
    dash_payload = {
        "dataset_id": dataset_id,
        "title": "Board with Custom Pin",
        "description": "Board to test live pins"
    }
    create_res = client.post("/api/dashboards", json=dash_payload, headers=auth_headers)
    assert create_res.status_code == 200
    dash_uuid = create_res.json()["id"]
    initial_widgets_count = len(create_res.json()["widgets"])
    
    chart_payload = {
        "title": "Custom Pinned Sales by Category",
        "chart_type": "bar",
        "x_axis": "category",
        "y_axis": "sales",
        "aggregate": "sum",
        "group_by": None
    }
    pin_res = client.post(f"/api/datasets/{dataset_id}/visualizations", json=chart_payload, headers=auth_headers)
    assert pin_res.status_code == 200
    
    details_res = client.get(f"/api/dashboards/{dash_uuid}", headers=auth_headers)
    assert details_res.status_code == 200
    widgets = details_res.json()["widgets"]
    assert len(widgets) == initial_widgets_count + 1
    assert widgets[-1]["title"] == "Custom Pinned Sales by Category"

def test_duplicate_pin_protection(auth_headers, dataset_id):
    chart_payload = {
        "title": "Duplicate Pin Test Chart",
        "chart_type": "bar",
        "x_axis": "category",
        "y_axis": None,
        "aggregate": "count",
        "group_by": None
    }
    pin1 = client.post(f"/api/datasets/{dataset_id}/visualizations", json=chart_payload, headers=auth_headers)
    assert pin1.status_code == 200
    id1 = pin1.json()["id"]
    
    pin2 = client.post(f"/api/datasets/{dataset_id}/visualizations", json=chart_payload, headers=auth_headers)
    assert pin2.status_code == 200
    id2 = pin2.json()["id"]
    
    assert id1 == id2
