import httpx
import sys
import os

BASE_URL = "http://localhost:8000"

def run_smoke_test():
    print("Starting DataViz AI Backend API Smoke Test...")
    
    # 1. Registration
    print("\n[1] Testing Registration...")
    email = "smoketest@example.com"
    password = "Password123!"
    full_name = "Smoke Test User"
    
    with httpx.Client(base_url=BASE_URL) as client:
        # Register user
        res = client.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": full_name
        })
        if res.status_code == 201:
            print("Registration: Success (Created new user)")
        elif res.status_code == 400 and "already registered" in res.json().get("detail", ""):
            print("Registration: Success (User already exists)")
        else:
            print(f"Registration Failed: {res.status_code} - {res.text}")
            sys.exit(1)
            
        # 2. Login
        print("\n[2] Testing Login...")
        res = client.post("/api/auth/login", data={
            "username": email,
            "password": password
        })
        if res.status_code != 200:
            print(f"Login Failed: {res.status_code} - {res.text}")
            sys.exit(1)
            
        auth_data = res.json()
        token = auth_data["access_token"]
        print("Login: Success (Token acquired)")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Upload Dataset
        print("\n[3] Testing Dataset Upload...")
        csv_path = r"c:\Users\kandu\OneDrive\Desktop\PROJECTS BY SRG\backend\tests\sample_data.csv"
        if not os.path.exists(csv_path):
            print(f"Error: csv path not found: {csv_path}")
            sys.exit(1)
            
        with open(csv_path, "rb") as f:
            files = {"file": ("sample_data.csv", f, "text/csv")}
            res = client.post("/api/datasets/upload", files=files, headers=headers)
            
        if res.status_code != 200:
            print(f"Upload Failed: {res.status_code} - {res.text}")
            sys.exit(1)
            
        upload_data = res.json()
        dataset_id = upload_data["metadata"]["id"]
        print(f"Upload: Success (Dataset ID: {dataset_id})")
        
        # 4. Dataset Overview
        print("\n[4] Testing Dataset Overview...")
        res = client.get(f"/api/datasets/{dataset_id}", headers=headers)
        if res.status_code != 200:
            print(f"Dataset Overview GET Failed: {res.status_code} - {res.text}")
            sys.exit(1)
        dataset_meta = res.json()["metadata"]
        print(f"Overview: Success (Rows: {dataset_meta['row_count']}, Columns: {dataset_meta['col_count']})")
        
        # 5. Data Quality
        print("\n[5] Testing Data Quality Profile...")
        res = client.get(f"/api/datasets/{dataset_id}/profile", headers=headers)
        if res.status_code != 200:
            print(f"Profile GET Failed: {res.status_code} - {res.text}")
            sys.exit(1)
        profile_data = res.json()
        print(f"Profile: Success (Quality Score: {profile_data['quality_report']['score']})")
        
        # 6. Smart Visualization Chart Types and Configurations
        print("\n[6] Testing Smart Visualization Chart Type Queries...")
        # Chart 1: Bar
        print("  - Testing Bar chart query (country x sales sum)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "country",
            "y_axis": "sales",
            "aggregate": "sum",
            "chart_type": "bar"
        })
        assert res.status_code == 200, f"Bar chart query failed: {res.text}"
        print(f"    Success: Returned {len(res.json()['datapoints'])} data points")
        
        # Chart 2: Line
        print("  - Testing Line chart query (created_at x sales avg)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "created_at",
            "y_axis": "sales",
            "aggregate": "average",
            "chart_type": "line"
        })
        assert res.status_code == 200, f"Line chart query failed: {res.text}"
        print(f"    Success: Returned {len(res.json()['datapoints'])} data points")
        
        # Chart 3: Pie
        print("  - Testing Pie chart query (active x count)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "active",
            "aggregate": "count",
            "chart_type": "pie"
        })
        assert res.status_code == 200, f"Pie chart query failed: {res.text}"
        print(f"    Success: Returned {len(res.json()['datapoints'])} data points")

        # Chart 4: Scatter
        print("  - Testing Scatter plot query (sales x sales)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "sales",
            "y_axis": "sales",
            "aggregate": "none",
            "chart_type": "scatter"
        })
        assert res.status_code == 200, f"Scatter chart query failed: {res.text}"
        print(f"    Success: Returned {len(res.json()['datapoints'])} data points")
        
        # Chart 5: Histogram
        print("  - Testing Histogram query (sales x none)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "sales",
            "chart_type": "histogram"
        })
        assert res.status_code == 200, f"Histogram chart query failed: {res.text}"
        print(f"    Success: Returned {len(res.json()['datapoints'])} data points")
        
        # 6b. Validation Blocks (Invalid combinations should fail with 400)
        print("\n[6b] Testing Visualizer Compiler Validation Rules...")
        
        # Invalid Scatter (non-numeric x)
        print("  - Verifying Scatter validation: non-numeric X (country) and Y (sales)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "country",
            "y_axis": "sales",
            "aggregate": "none",
            "chart_type": "scatter"
        })
        assert res.status_code == 400, f"Validation bypass! Scatter with non-numeric X succeeded: {res.text}"
        print("    Passed validation: Succeeded blocking (HTTP 400)")
        
        # Invalid Scatter (missing y)
        print("  - Verifying Scatter validation: missing Y-axis...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "sales",
            "chart_type": "scatter"
        })
        assert res.status_code == 400, f"Validation bypass! Scatter with missing Y succeeded: {res.text}"
        print("    Passed validation: Succeeded blocking (HTTP 400)")

        # Invalid Histogram (non-numeric)
        print("  - Verifying Histogram validation: non-numeric X (country)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "country",
            "chart_type": "histogram"
        })
        assert res.status_code == 400, f"Validation bypass! Histogram with non-numeric X succeeded: {res.text}"
        print("    Passed validation: Succeeded blocking (HTTP 400)")

        # Invalid Pie (numeric x)
        print("  - Verifying Pie validation: numeric X (sales)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "sales",
            "chart_type": "pie"
        })
        assert res.status_code == 400, f"Validation bypass! Pie with numeric X succeeded: {res.text}"
        print("    Passed validation: Succeeded blocking (HTTP 400)")

        # Invalid Line (non-ordered x)
        print("  - Verifying Line validation: non-ordered X (country)...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations/query", headers=headers, json={
            "x_axis": "country",
            "chart_type": "line"
        })
        assert res.status_code == 400, f"Validation bypass! Line with non-ordered X succeeded: {res.text}"
        print("    Passed validation: Succeeded blocking (HTTP 400)")
        
        # 7. Ask Your Data
        print("\n[7] Testing Ask Your Data (Natural Language Parser)...")
        res = client.post(f"/api/datasets/{dataset_id}/ask", headers=headers, json={
            "question": "What is the average sales per country?"
        })
        if res.status_code != 200:
            print(f"Ask Your Data Failed: {res.status_code} - {res.text}")
            sys.exit(1)
        ask_data = res.json()
        print(f"Ask Your Data: Success (Status: {ask_data['status']}, Interpretation: {ask_data['interpretation']})")
        print(f"    Factual summary generated: {ask_data['insight']['summary']}")
        
        # 8. Saved Charts & Pin to Dashboard
        print("\n[8] Testing Pin to Dashboard...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations", headers=headers, json={
            "title": "Sales by Country Chart",
            "chart_type": "bar",
            "x_axis": "country",
            "y_axis": "sales",
            "aggregate": "sum"
        })
        if res.status_code not in [200, 201]:
            print(f"Pin Chart Failed: {res.status_code} - {res.text}")
            sys.exit(1)
        saved_chart_1 = res.json()
        print(f"    Pin Chart: Success (Chart ID: {saved_chart_1['id']})")
        
        # Test Duplicate Pin Protection
        print("  - Testing duplicate-pin protection...")
        res = client.post(f"/api/datasets/{dataset_id}/visualizations", headers=headers, json={
            "title": "Sales by Country Chart",
            "chart_type": "bar",
            "x_axis": "country",
            "y_axis": "sales",
            "aggregate": "sum"
        })
        saved_chart_2 = res.json()
        assert saved_chart_1["id"] == saved_chart_2["id"], "Duplicate chart was created! Protection failed."
        print("    Duplicate Pin Protection: Success (No duplicate chart created, original ID returned)")
        
        # 9. Dashboard Persistence & Interactive Filters
        print("\n[9] Testing Dashboard Persistence & Filters...")
        # Create dashboard if not exists
        res = client.post("/api/dashboards", headers=headers, json={
            "dataset_id": dataset_id,
            "title": "Test Dashboard",
            "description": "Main workspace view"
        })
        if res.status_code not in [200, 201]:
            print(f"Dashboard Creation Failed: {res.status_code} - {res.text}")
            sys.exit(1)
        dashboard_id = res.json()["id"]
        print(f"    Dashboard: Created (ID: {dashboard_id})")
        
        # Retrieve Dashboard details
        res = client.get(f"/api/dashboards/{dashboard_id}", headers=headers)
        assert res.status_code == 200, f"Fetch Dashboard failed: {res.text}"
        dash_details = res.json()
        print(f"    Dashboard details: Retrieved (Widgets count: {len(dash_details['widgets'])})")
        assert len(dash_details["widgets"]) > 0, "No widgets found on dashboard!"
        
        # Retrieve with Interactive Filters
        print("  - Testing Interactive Dashboard Category Filter...")
        res = client.get(f"/api/dashboards/{dashboard_id}", headers=headers, params={
            "filters": '{"country": "USA"}'
        })
        assert res.status_code == 200, f"Filter query failed: {res.text}"
        filtered_dash_details = res.json()
        print("    Success: Filtered query completed successfully")
        
        # 10. Statistical Insights
        print("\n[10] Testing Statistical Insights (Heatmap & Skewness)...")
        res = client.get(f"/api/datasets/{dataset_id}/insights", headers=headers)
        if res.status_code != 200:
            print(f"Insights GET Failed: {res.status_code} - {res.text}")
            sys.exit(1)
        insights = res.json()
        print(f"    Insights count: {len(insights)}")
        for insight in insights[:3]:
            print(f"    * [{insight['insight_type']}] {insight['message']}")
            
        print("\n================================================")
        print("ALL END-TO-END BACKEND API SMOKE TESTS PASSED!")
        print("================================================")

if __name__ == "__main__":
    run_smoke_test()
