import pandas as pd
from backend.app.services.file_service import infer_column_type

def test_infer_numeric_column():
    # Ints and floats
    s1 = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    s2 = pd.Series([1.5, 2.3, 3.1, 4.8, 5.0, 6.2, 7.8, 8.9, 9.1, 10.5])
    assert infer_column_type("sales", s1) == "Numeric"
    assert infer_column_type("ratio", s2) == "Numeric"

def test_infer_boolean_column():
    # Actual booleans
    s1 = pd.Series([True, False, True, False])
    # Boolean mapping representation strings/ints
    s2 = pd.Series(["yes", "no", "yes", "yes"])
    s3 = pd.Series([1, 0, 0, 1, 1, 0])
    
    assert infer_column_type("flag", s1) == "Boolean"
    assert infer_column_type("active", s2) == "Boolean"
    assert infer_column_type("status_bin", s3) == "Boolean"

def test_infer_identifier_column():
    # Unique sequential ids
    s1 = pd.Series(range(1, 101))
    s2 = pd.Series([f"USR_{i}" for i in range(100)])
    
    assert infer_column_type("user_id", s1) == "Identifier"
    assert infer_column_type("pk_code", s2) == "Identifier"

def test_infer_date_column():
    # Datetime objects
    s1 = pd.Series(pd.date_range("2026-01-01", periods=10))
    # String dates
    s2 = pd.Series(["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09", "2026-01-10"])
    
    assert infer_column_type("created_at", s1) == "Date/time"
    assert infer_column_type("transaction_date", s2) == "Date/time"

def test_infer_geographic_column():
    s1 = pd.Series(["USA", "Canada", "India", "UK", "France"])
    s2 = pd.Series([40.7128, 34.0522, 51.5074, 48.8566])
    
    assert infer_column_type("country", s1) == "Geographic candidate"
    assert infer_column_type("customer_city", s1) == "Geographic candidate"
    assert infer_column_type("latitude", s2) == "Geographic candidate"

def test_infer_categorical_column():
    # Repeated categories
    s1 = pd.Series(["High", "Medium", "Low", "High", "Low", "Medium"] * 10)
    assert infer_column_type("priority", s1) == "Categorical"

def test_infer_text_column():
    # Highly unique text sentences
    s1 = pd.Series([
        f"This is a long description message details for event log number {i} containing descriptive words." 
        for i in range(100)
    ])
    assert infer_column_type("description", s1) == "Text"
