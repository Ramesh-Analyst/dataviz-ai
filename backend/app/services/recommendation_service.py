from typing import List, Dict, Any
import pandas as pd

def generate_recommendations(df: pd.DataFrame, column_stats: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates at least 3 context-aware visualization recommendations based on column data types,
    relationships, and cardinality.
    """
    recommendations = []
    
    # Classify columns
    numeric_cols = []
    categorical_cols = []
    date_cols = []
    
    for col_name, stats in column_stats.items():
        dtype = stats["detected_type"]
        if dtype == "Numeric":
            numeric_cols.append(col_name)
        elif dtype == "Categorical":
            categorical_cols.append(col_name)
        elif dtype == "Date/time":
            date_cols.append(col_name)
            
    # Rule 1: Date/Time + Numeric (Time Series trend)
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        num_col = numeric_cols[0]
        recommendations.append({
            "title": f"Trend of {num_col} over Time",
            "chart_type": "line",
            "x_axis": date_col,
            "y_axis": num_col,
            "aggregate": "average",
            "group_by": None,
            "reason": f"Visualizes the historical trend and temporal changes of '{num_col}' indexed by '{date_col}'."
        })

    # Rule 2: Categorical + Numeric (Grouped aggregation comparison)
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        recommendations.append({
            "title": f"Total {num_col} by {cat_col}",
            "chart_type": "bar",
            "x_axis": cat_col,
            "y_axis": num_col,
            "aggregate": "sum",
            "group_by": None,
            "reason": f"Compares the total sum of '{num_col}' across different '{cat_col}' groups."
        })

    # Rule 3: 2 Numeric columns (Correlation / Scatter correlation)
    if len(numeric_cols) >= 2:
        num1 = numeric_cols[0]
        num2 = numeric_cols[1]
        recommendations.append({
            "title": f"Relationship: {num1} vs {num2}",
            "chart_type": "scatter",
            "x_axis": num1,
            "y_axis": num2,
            "aggregate": "none",
            "group_by": None,
            "reason": f"Examines the correlation and distribution pattern between '{num1}' and '{num2}'."
        })

    # Rule 4: 1 Categorical column (Frequency / Share count distribution)
    for cat_col in categorical_cols:
        stats = column_stats[cat_col]
        # Restrict pie charts to lower cardinality to prevent visual clutter
        if stats["unique_count"] <= 10:
            recommendations.append({
                "title": f"Distribution of {cat_col}",
                "chart_type": "pie",
                "x_axis": cat_col,
                "y_axis": None,
                "aggregate": "count",
                "group_by": None,
                "reason": f"Shows the relative proportion and share of each group within '{cat_col}'."
            })
            break

    # Rule 5: 1 Numeric column (Value distribution frequency)
    if numeric_cols and len(recommendations) < 3:
        num_col = numeric_cols[0]
        recommendations.append({
            "title": f"Distribution frequency of {num_col}",
            "chart_type": "bar",
            "x_axis": num_col,
            "y_axis": None,
            "aggregate": "count",
            "group_by": None,
            "reason": f"Details the record counts and distribution density of '{num_col}' values."
        })

    # Ensure we ALWAYS output at least 3 distinct recommendations
    # Add simple index bar count fallbacks if recommendations count < 3
    if len(recommendations) < 3:
        for col_name in list(column_stats.keys()):
            if len(recommendations) >= 3:
                break
            # Skip if already recommended as x_axis
            if any(r["x_axis"] == col_name for r in recommendations):
                continue
            recommendations.append({
                "title": f"Record Counts by {col_name}",
                "chart_type": "bar",
                "x_axis": col_name,
                "y_axis": None,
                "aggregate": "count",
                "group_by": None,
                "reason": f"Aggregates record count occurrences grouped by '{col_name}'."
            })
            
    return recommendations
