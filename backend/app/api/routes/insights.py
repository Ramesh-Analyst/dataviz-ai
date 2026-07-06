import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from backend.app.database.session import get_db
from backend.app.models import models
from backend.app.api.routes.auth import get_current_user
from backend.app.services.file_service import load_dataframe
from backend.app.services.profiling_service import get_column_stats
from backend.app.services.data_quality_service import evaluate_data_quality

router = APIRouter()

@router.get("/{id}/insights")
def generate_dataset_insights(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes the dataset and generates a set of natural language statistical
    takeaways (correlations, missingness, outlier rates, skewness, and cardinality warnings).
    """
    db_dataset = db.query(models.Dataset).filter(
        models.Dataset.id == id,
        models.Dataset.user_id == current_user.id
    ).first()
    
    if not db_dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found or access denied."
        )
        
    try:
        df = load_dataframe(db_dataset.storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading dataset: {str(e)}"
        )
        
    column_stats = get_column_stats(df)
    quality_report = evaluate_data_quality(df, column_stats)
    
    insights = []
    total_rows = len(df)
    
    # 1. Pearson Correlation Insights
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) >= 2:
        try:
            corr_df = numeric_df.corr(method="pearson")
            columns = list(corr_df.columns)
            # Find combinations without repeating pairs (ColA vs ColB and ColB vs ColA)
            seen_pairs = set()
            for i, col1 in enumerate(columns):
                for col2 in columns[i+1:]:
                    val = corr_df.loc[col1, col2]
                    if pd.notna(val) and abs(val) >= 0.5:
                        strength = "strong" if abs(val) >= 0.75 else "moderate"
                        direction = "positive" if val > 0 else "negative"
                        message = f"Found a {strength} {direction} correlation ({round(val, 2)}) between '{col1}' and '{col2}'."
                        insights.append({
                            "insight_type": "correlation",
                            "message": message,
                            "significance": float(abs(val)),
                            "severity": "info" if abs(val) < 0.75 else "warning"
                        })
        except Exception:
            pass
            
    # 2. Skewness and Modes
    for col_name, stats in column_stats.items():
        # High missingness
        missing_pct = stats["missing_percentage"]
        if missing_pct >= 10:
            insights.append({
                "insight_type": "missingness",
                "message": f"Column '{col_name}' is missing {missing_pct}% of its rows. This may bias statistical analyses.",
                "significance": float(missing_pct / 100.0),
                "severity": "critical" if missing_pct > 25 else "warning"
            })
            
        # Constant Columns
        if stats["unique_count"] == 1 and total_rows > 1:
            insights.append({
                "insight_type": "constant",
                "message": f"Column '{col_name}' contains only one constant value. It offers no informational variance.",
                "significance": 1.0,
                "severity": "warning"
            })
            continue
            
        # Top frequent value representation (Skewness)
        if "top_frequent" in stats and stats["top_frequent"]:
            top_mode = stats["top_frequent"][0]
            top_pct = top_mode["percentage"]
            if top_pct >= 50.0 and stats["unique_count"] > 1:
                insights.append({
                    "insight_type": "skewness",
                    "message": f"Column '{col_name}' is heavily skewed: '{top_mode['value']}' accounts for {top_pct}% of all records.",
                    "significance": float(top_pct / 100.0),
                    "severity": "info"
                })
                
        # Cardinality check for Categorical columns
        if stats["detected_type"] == "Categorical" and stats["unique_count"] > 40:
            # Scale significance relative to a group ceiling of 200 (where >=200 is 100% severe)
            sig_score = min(1.0, stats["unique_count"] / 200.0)
            insights.append({
                "insight_type": "cardinality",
                "message": f"Categorical column '{col_name}' has high cardinality ({stats['unique_count']} unique groups). Consider grouping rare categories.",
                "significance": float(sig_score),
                "severity": "info"
            })
            
    # 3. Quality score overall summary insight
    score = quality_report["score"]
    if score < 70:
        insights.append({
            "insight_type": "quality",
            "message": f"Dataset data quality rating is poor ({score}/100). Consider cleaning missing values and outliers before training models.",
            "significance": float((100.0 - score) / 100.0),
            "severity": "critical"
        })
    elif score >= 90:
        insights.append({
            "insight_type": "quality",
            "message": f"Excellent dataset quality rating ({score}/100). Ready for dashboard construction and reporting.",
            "significance": float(score / 100.0),
            "severity": "info"
        })
        
    # Sort insights by significance descending
    insights.sort(key=lambda x: x["significance"], reverse=True)
    return insights
