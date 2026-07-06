import pandas as pd
import numpy as np
from typing import Dict, Any, List
from backend.app.services.file_service import infer_column_type

def get_dataset_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes dataset-level statistics.
    """
    row_count = len(df)
    col_count = len(df.columns)
    total_cells = row_count * col_count
    
    duplicate_rows = int(df.duplicated().sum())
    missing_cells = int(df.isna().sum().sum())
    missing_percentage = float((missing_cells / total_cells) * 100) if total_cells > 0 else 0.0
    memory_usage = int(df.memory_usage(deep=True).sum())
    
    return {
        "row_count": row_count,
        "col_count": col_count,
        "duplicate_rows": duplicate_rows,
        "missing_cells": missing_cells,
        "missing_percentage": round(missing_percentage, 2),
        "memory_usage": memory_usage
    }

def get_column_stats(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Computes detailed profiling metrics for each column.
    """
    stats = {}
    
    for col_name in df.columns:
        series = df[col_name]
        detected_type = infer_column_type(str(col_name), series)
        
        unique_count = int(series.nunique(dropna=True))
        missing_count = int(series.isna().sum())
        missing_percentage = float((missing_count / len(series)) * 100) if len(series) > 0 else 0.0
        
        col_stats = {
            "name": str(col_name),
            "detected_type": detected_type,
            "unique_count": unique_count,
            "missing_count": missing_count,
            "missing_percentage": round(missing_percentage, 2)
        }
        
        # Clean nulls for mathematical operations
        non_null = series.dropna()
        
        if detected_type == "Numeric" and not non_null.empty:
            try:
                # Convert to standard numeric type to avoid numpy serialization problems
                non_null_numeric = pd.to_numeric(non_null, errors="coerce").dropna()
                if not non_null_numeric.empty:
                    col_stats.update({
                        "min": float(non_null_numeric.min()),
                        "max": float(non_null_numeric.max()),
                        "mean": round(float(non_null_numeric.mean()), 4),
                        "median": float(non_null_numeric.median()),
                        "std": round(float(non_null_numeric.std()), 4) if len(non_null_numeric) > 1 else 0.0,
                        "q25": float(non_null_numeric.quantile(0.25)),
                        "q50": float(non_null_numeric.quantile(0.50)),
                        "q75": float(non_null_numeric.quantile(0.75))
                    })
            except Exception:
                pass
                
        # Top frequent values (mode) for all classifications
        if not non_null.empty:
            value_counts = non_null.value_counts()
            top_frequent = []
            for val, count in value_counts.head(5).items():
                top_frequent.append({
                    "value": str(val),
                    "count": int(count),
                    "percentage": round(float((count / len(df)) * 100), 2)
                })
            col_stats["top_frequent"] = top_frequent
            
        stats[str(col_name)] = col_stats
        
    return stats
