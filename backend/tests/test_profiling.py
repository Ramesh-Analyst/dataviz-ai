import pandas as pd
import numpy as np
from backend.app.services.profiling_service import get_dataset_stats, get_column_stats
from backend.app.services.data_quality_service import evaluate_data_quality

def test_dataset_profiling_and_quality_score():
    # 1. Create a dummy DataFrame with known anomalies
    # Total rows: 10, Columns: 4 (id, val, category, constant)
    # - Row 9 and 10 are duplicates
    # - Null cells: 3 missing values in 'val' column
    # - Outliers: value '999.0' is a clear outlier in 'val'
    # - Column 'constant' is completely constant (all 'static')
    data = {
        "id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 9],
        "val": [10.0, 12.0, 11.5, None, 14.2, None, 13.0, 999.0, 15.0, 15.0],
        "category": ["A", "B", "A", "B", "C", "A", None, "B", "A", "A"],
        "constant": ["static"] * 10
    }
    df = pd.DataFrame(data)
    
    # 2. Test Dataset Stats
    stats = get_dataset_stats(df)
    assert stats["row_count"] == 10
    assert stats["col_count"] == 4
    assert stats["duplicate_rows"] == 1
    assert stats["missing_cells"] == 3 # 2 in 'val', 1 in 'category'
    assert stats["memory_usage"] > 0
    
    # 3. Test Column Stats
    col_stats = get_column_stats(df)
    assert col_stats["constant"]["unique_count"] == 1
    assert col_stats["val"]["detected_type"] == "Numeric"
    assert col_stats["category"]["detected_type"] == "Categorical"
    
    # Numeric column statistics validations
    val_stats = col_stats["val"]
    assert val_stats["min"] == 10.0
    assert val_stats["max"] == 999.0
    assert "mean" in val_stats
    assert "median" in val_stats
    assert "q25" in val_stats
    assert "q75" in val_stats
    
    # Mode verification
    cat_freq = col_stats["category"]["top_frequent"]
    assert cat_freq[0]["value"] == "A"
    assert cat_freq[0]["count"] == 5 # 5 counts of A
    
    # 4. Test Data Quality Evaluation
    quality = evaluate_data_quality(df, col_stats)
    
    # Check that score is computed and bounded
    assert 0.0 <= quality["score"] <= 100.0
    
    # Explainable deductions validations
    deductions_keys = [d["issue"] for d in quality["deductions"]]
    assert "Missing Values" in deductions_keys
    assert "Duplicate Rows" in deductions_keys
    assert "Constant Columns" in deductions_keys
    assert "Statistical Outliers" in deductions_keys # '999.0' is detected as outlier
    
    # Verify that constant column deduction names the right one
    issues_msgs = [i["message"] for i in quality["issues_list"]]
    assert any("constant" in msg.lower() for msg in issues_msgs)
