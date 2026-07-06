import pandas as pd
import numpy as np
from typing import Dict, Any, List

def evaluate_data_quality(df: pd.DataFrame, column_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes dataset quality, calculates outlier bounds using IQR, detects constant/high-cardinality columns,
    and returns a transparent 0-100 score with detailed itemized deductions.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols
    
    if total_cells == 0:
        return {"score": 0.0, "deductions": [], "issues_list": [{"severity": "critical", "message": "Empty dataset."}]}
        
    issues_list = []
    deductions = []
    
    # 1. Missing Values Analysis
    missing_cells = sum(col["missing_count"] for col in column_stats.values())
    missing_ratio = missing_cells / total_cells
    null_deduction = round(30 * missing_ratio, 2)
    if missing_cells > 0:
        deductions.append({
            "issue": "Missing Values",
            "deduction": null_deduction,
            "explanation": f"{missing_cells} cells are empty ({round(missing_ratio * 100, 2)}% of total data). (Max penalty: 30 pts)"
        })
        issues_list.append({
            "severity": "warning" if missing_ratio > 0.05 else "info",
            "message": f"Dataset is missing {missing_cells} cells ({round(missing_ratio * 100, 2)}% null rate)."
        })

    # 2. Duplicate Rows Analysis
    duplicate_rows = int(df.duplicated().sum())
    duplicate_ratio = duplicate_rows / total_rows if total_rows > 0 else 0
    dup_deduction = round(20 * duplicate_ratio, 2)
    if duplicate_rows > 0:
        deductions.append({
            "issue": "Duplicate Rows",
            "deduction": dup_deduction,
            "explanation": f"{duplicate_rows} duplicate rows detected ({round(duplicate_ratio * 100, 2)}% redundancy). (Max penalty: 20 pts)"
        })
        issues_list.append({
            "severity": "warning" if duplicate_ratio > 0.05 else "info",
            "message": f"Found {duplicate_rows} duplicate rows. Consider dropping redundant records."
        })

    # 3. Constant Columns Analysis (Columns with only 1 unique value)
    constant_cols = []
    for col_name, col in column_stats.items():
        if col["unique_count"] == 1 and total_rows > 1:
            constant_cols.append(col_name)
            
    constant_ratio = len(constant_cols) / total_cols
    constant_deduction = round(15 * constant_ratio, 2)
    if len(constant_cols) > 0:
        deductions.append({
            "issue": "Constant Columns",
            "deduction": constant_deduction,
            "explanation": f"{len(constant_cols)} columns contain only 1 unique value ({round(constant_ratio * 100, 1)}% of columns). (Max penalty: 15 pts)"
        })
        for cname in constant_cols:
            issues_list.append({
                "severity": "warning",
                "message": f"Column '{cname}' contains only one constant value. It offers no informational variance."
            })

    # 4. Outliers Analysis (IQR on numerical columns)
    total_outliers = 0
    outlier_rows_set = set()
    numeric_col_count = 0
    
    for col_name, col in column_stats.items():
        if col["detected_type"] == "Numeric" and "min" in col:
            numeric_col_count += 1
            series = df[col_name].dropna()
            try:
                numeric_series = pd.to_numeric(series, errors="coerce").dropna()
                q25 = col["q25"]
                q75 = col["q75"]
                iqr = q75 - q25
                lower_bound = q25 - 1.5 * iqr
                upper_bound = q75 + 1.5 * iqr
                
                # Identify outlier indices
                outliers = numeric_series[(numeric_series < lower_bound) | (numeric_series > upper_bound)]
                outlier_count = len(outliers)
                if outlier_count > 0:
                    total_outliers += outlier_count
                    outlier_rows_set.update(outliers.index.tolist())
                    issues_list.append({
                        "severity": "info",
                        "message": f"Column '{col_name}' has {outlier_count} statistical outliers (outside range {round(lower_bound, 2)} - {round(upper_bound, 2)})."
                    })
            except Exception:
                pass
                
    outlier_rows_count = len(outlier_rows_set)
    outlier_ratio = outlier_rows_count / total_rows if total_rows > 0 else 0
    outlier_deduction = round(15 * outlier_ratio, 2)
    if outlier_rows_count > 0:
        deductions.append({
            "issue": "Statistical Outliers",
            "deduction": outlier_deduction,
            "explanation": f"{outlier_rows_count} rows ({round(outlier_ratio * 100, 2)}%) contain statistical outliers via IQR check. (Max penalty: 15 pts)"
        })

    # 5. Invalid formats (Numeric stored as strings, or high cardinality categoricals)
    invalid_format_cols = 0
    for col_name, col in column_stats.items():
        series = df[col_name].dropna()
        dtype = col["detected_type"]
        unique = col["unique_count"]
        
        # High cardinality categoricals
        if dtype == "Categorical" and (unique > 50 or (unique / total_rows > 0.3 and total_rows > 10)):
            issues_list.append({
                "severity": "info",
                "message": f"Categorical column '{col_name}' has high cardinality ({unique} unique values). Consider treating as Text."
            })
            
        # Numeric columns stored as strings
        if dtype in ["Categorical", "Text"] and not series.empty:
            try:
                # Try parsing as float
                parsed = pd.to_numeric(series, errors="coerce")
                # If > 85% parses successfully, it's likely a numeric column stored as strings
                if parsed.notna().sum() / len(series) > 0.85:
                    invalid_format_cols += 1
                    issues_list.append({
                        "severity": "warning",
                        "message": f"Column '{col_name}' contains mostly numeric data but is stored as text. Consider converting to float/integer."
                    })
            except Exception:
                pass
                
    invalid_ratio = invalid_format_cols / total_cols
    invalid_deduction = round(20 * invalid_ratio, 2)
    if invalid_format_cols > 0:
        deductions.append({
            "issue": "Format Type Conflicts",
            "deduction": invalid_deduction,
            "explanation": f"{invalid_format_cols} column(s) store numeric data as string formats. (Max penalty: 20 pts)"
        })

    # Final Score Calculation
    total_penalty = null_deduction + dup_deduction + constant_deduction + outlier_deduction + invalid_deduction
    score = max(0.0, min(100.0, 100.0 - total_penalty))
    
    return {
        "score": round(score, 1),
        "deductions": deductions,
        "issues_list": issues_list
    }
