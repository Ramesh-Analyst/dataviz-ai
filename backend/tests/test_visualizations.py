import io
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    # Register and login a unique test user
    email = f"vis_test_{uuid.uuid4().hex[:6]}@datavizai.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Viz Tester"}
    )
    login_res = client.post(
        "/api/auth/login",
        data={"username": email, "password": "password123"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def dataset_id(auth_headers):
    # Upload a small CSV dataset
    csv_content = (
        "year,sales,category\n"
        "2020,100,Electronics\n"
        "2020,150,Furniture\n"
        "2021,200,Electronics\n"
        "2021,300,Furniture\n"
        "2022,400,Electronics\n"
        "2022,100,Furniture\n"
    )
    file_payload = {"file": ("test_sales.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=file_payload, headers=auth_headers)
    assert upload_res.status_code == 200
    return upload_res.json()["metadata"]["id"]

def test_visualization_flow(auth_headers, dataset_id):
    # 1. Test Recommendations Engine
    rec_res = client.get(f"/api/datasets/{dataset_id}/visualizations/recommendations", headers=auth_headers)
    assert rec_res.status_code == 200
    recs = rec_res.json()
    assert len(recs) >= 3
    assert "title" in recs[0]
    assert "chart_type" in recs[0]
    assert "x_axis" in recs[0]
    assert "reason" in recs[0]
    
    # 2. Test Aggregation Query Executor
    query_payload = {
        "x_axis": "category",
        "y_axis": "sales",
        "aggregate": "average",
        "group_by": "year"
    }
    query_res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=query_payload, headers=auth_headers)
    assert query_res.status_code == 200
    data = query_res.json()
    assert "datapoints" in data
    datapoints = data["datapoints"]
    assert len(datapoints) > 0
    # Average of sales for Electronics in 2020 should be 100
    # Group keys should exist
    assert "category" in datapoints[0]
    assert "year" in datapoints[0]
    assert "value" in datapoints[0]
    
    # 3. Test Saving a Custom Chart
    chart_payload = {
        "title": "Category Sales Performance Chart",
        "chart_type": "bar",
        "x_axis": "category",
        "y_axis": "sales",
        "aggregate": "sum",
        "group_by": "year"
    }
    save_res = client.post(f"/api/datasets/{dataset_id}/visualizations", json=chart_payload, headers=auth_headers)
    assert save_res.status_code == 200
    chart_data = save_res.json()
    assert "id" in chart_data
    assert chart_data["title"] == "Category Sales Performance Chart"
    chart_uuid = chart_data["id"]
    
    # 4. Test Listing Saved Charts
    list_res = client.get(f"/api/datasets/{dataset_id}/visualizations", headers=auth_headers)
    assert list_res.status_code == 200
    charts = list_res.json()
    assert len(charts) == 1
    assert charts[0]["id"] == chart_uuid
    
    # 5. Test Deleting Saved Chart
    delete_res = client.delete(f"/api/datasets/{dataset_id}/visualizations/{chart_uuid}", headers=auth_headers)
    assert delete_res.status_code == 200
    
    # List again to verify removal
    list_again_res = client.get(f"/api/datasets/{dataset_id}/visualizations", headers=auth_headers)
    assert len(list_again_res.json()) == 0

def test_count_only_query_no_y(auth_headers, dataset_id):
    query_payload = {
        "x_axis": "year",
        "y_axis": None,
        "aggregate": "count",
        "group_by": None
    }
    query_res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=query_payload, headers=auth_headers)
    assert query_res.status_code == 200
    data = query_res.json()
    assert "datapoints" in data
    datapoints = data["datapoints"]
    # We uploaded:
    # 2020: 2 rows
    # 2021: 2 rows
    # 2022: 2 rows
    year_to_count = {row["year"]: row["value"] for row in datapoints}
    assert year_to_count[2020] == 2
    assert year_to_count[2021] == 2
    assert year_to_count[2022] == 2

def test_query_aggregations_normalization_and_median(auth_headers, dataset_id):
    # Test median
    query_payload = {
        "x_axis": "year",
        "y_axis": "sales",
        "aggregate": "median",
        "group_by": None
    }
    query_res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=query_payload, headers=auth_headers)
    assert query_res.status_code == 200
    datapoints = query_res.json()["datapoints"]
    year_to_val = {row["year"]: row["value"] for row in datapoints}
    assert year_to_val[2020] == 125.0

    # Test normalization of Count Instances
    query_payload_norm = {
        "x_axis": "year",
        "y_axis": None,
        "aggregate": "Count Instances",
        "group_by": None
    }
    query_res_norm = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=query_payload_norm, headers=auth_headers)
    assert query_res_norm.status_code == 200
    assert "datapoints" in query_res_norm.json()

def test_recommendation_to_query_execution(auth_headers, dataset_id):
    # 1. Fetch Recommendations
    rec_res = client.get(f"/api/datasets/{dataset_id}/visualizations/recommendations", headers=auth_headers)
    assert rec_res.status_code == 200
    recs = rec_res.json()
    assert len(recs) > 0
    
    # 2. Iterate and execute query for each recommendation to ensure compilation correctness
    for rec in recs:
        query_payload = {
            "x_axis": rec["x_axis"],
            "y_axis": rec.get("y_axis"),
            "aggregate": rec.get("aggregate", "none"),
            "group_by": rec.get("group_by"),
            "chart_type": rec["chart_type"]
        }
        query_res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=query_payload, headers=auth_headers)
        assert query_res.status_code == 200, f"Failed recommendation query: {rec['title']} with detail {query_res.text}"
        assert "datapoints" in query_res.json()


def test_visualization_validation_rules(auth_headers, dataset_id):
    # 1. Scatter Plot invalid coordinate type (X or Y not numeric)
    payload_scatter_invalid = {
        "x_axis": "category",
        "y_axis": "sales",
        "aggregate": "none",
        "chart_type": "scatter"
    }
    res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=payload_scatter_invalid, headers=auth_headers)
    assert res.status_code == 400
    assert "both X-axis and Y-axis variables to be Numeric" in res.json()["detail"]

    # 2. Scatter Plot missing Y-axis
    payload_scatter_no_y = {
        "x_axis": "sales",
        "y_axis": None,
        "aggregate": "none",
        "chart_type": "scatter"
    }
    res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=payload_scatter_no_y, headers=auth_headers)
    assert res.status_code == 400
    assert "requires both X-axis and Y-axis variables" in res.json()["detail"]

    # 3. Pie Chart non-categorical X-axis
    payload_pie_invalid = {
        "x_axis": "sales",
        "y_axis": None,
        "aggregate": "count",
        "chart_type": "pie"
    }
    res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=payload_pie_invalid, headers=auth_headers)
    assert res.status_code == 400
    assert "Pie chart requires a categorical" in res.json()["detail"]

    # 4. Histogram non-numeric X-axis
    payload_hist_invalid = {
        "x_axis": "category",
        "y_axis": None,
        "aggregate": "count",
        "chart_type": "histogram"
    }
    res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=payload_hist_invalid, headers=auth_headers)
    assert res.status_code == 400
    assert "Histogram requires a Numeric column" in res.json()["detail"]

    # 5. Line Chart non-date/numeric/identifier X-axis
    payload_line_invalid = {
        "x_axis": "category",
        "y_axis": "sales",
        "aggregate": "sum",
        "chart_type": "line"
    }
    res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=payload_line_invalid, headers=auth_headers)
    assert res.status_code == 400
    assert "Line chart requires an ordered variable" in res.json()["detail"]

    # 6. Sum/Mean aggregate without Y-axis
    payload_agg_no_y = {
        "x_axis": "year",
        "y_axis": None,
        "aggregate": "sum",
        "chart_type": "bar"
    }
    res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=payload_agg_no_y, headers=auth_headers)
    assert res.status_code == 400
    assert "Y-axis column is required for" in res.json()["detail"]


def test_cross_user_visualization_protection(auth_headers, dataset_id):
    # Register another user
    other_email = f"other_{uuid.uuid4().hex[:6]}@datavizai.com"
    client.post(
        "/api/auth/register",
        json={"email": other_email, "password": "password123", "full_name": "Other User"}
    )
    login_res = client.post(
        "/api/auth/login",
        data={"username": other_email, "password": "password123"}
    )
    other_token = login_res.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Attempt to query user A's dataset using user B's token
    query_payload = {
        "x_axis": "category",
        "y_axis": "sales",
        "aggregate": "sum",
        "group_by": None
    }
    res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", json=query_payload, headers=other_headers)
    assert res.status_code == 404
    assert "access denied" in res.json()["detail"].lower()


def test_cascade_delete_dataset_cleans_visuals(auth_headers, dataset_id):
    # 1. Save a chart
    chart_payload = {
        "title": "Cascade Chart",
        "chart_type": "bar",
        "x_axis": "category",
        "y_axis": "sales",
        "aggregate": "sum",
        "group_by": None
    }
    chart_res = client.post(f"/api/datasets/{dataset_id}/visualizations", json=chart_payload, headers=auth_headers)
    assert chart_res.status_code == 200
    chart_id = chart_res.json()["id"]

    # 2. Create a dashboard (linking to this dataset and automatically generating widgets)
    dash_payload = {
        "dataset_id": dataset_id,
        "title": "Cascade Dashboard",
        "description": "Dashboard to test cascading deletion"
    }
    dash_res = client.post("/api/dashboards", json=dash_payload, headers=auth_headers)
    assert dash_res.status_code == 200
    dash_id = dash_res.json()["id"]

    # 3. Verify widgets count
    dash_details_res = client.get(f"/api/dashboards/{dash_id}", headers=auth_headers)
    assert len(dash_details_res.json()["widgets"]) > 0

    # 4. Delete the dataset
    delete_res = client.delete(f"/api/datasets/{dataset_id}", headers=auth_headers)
    assert delete_res.status_code == 200

    # 5. Verify the dashboard has been cascade-deleted
    get_dash_res = client.get(f"/api/dashboards/{dash_id}", headers=auth_headers)
    assert get_dash_res.status_code == 404

