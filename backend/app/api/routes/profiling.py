import uuid
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models import models
from backend.app.api.routes.auth import get_current_user
from backend.app.services.file_service import load_dataframe
from backend.app.services.profiling_service import get_dataset_stats, get_column_stats
from backend.app.services.data_quality_service import evaluate_data_quality
from backend.app.utils.json_cleaner import clean_nans_for_json

router = APIRouter()

@router.get("/{id}/profile")
def get_dataset_profile(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes statistical profiling, data quality ratings, correlations,
    and missing values ratios for a user's uploaded dataset.
    """
    # Fetch dataset metadata registry record
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
            detail=f"Error reading file from storage: {str(e)}"
        )
        
    # 1. Dataset stats & Column profiles
    dataset_stats = get_dataset_stats(df)
    column_stats = get_column_stats(df)
    
    # 2. Quality evaluation & deductions
    quality_report = evaluate_data_quality(df, column_stats)
    
    # 3. Numeric Correlation Analysis
    # Get numeric columns
    numeric_df = df.select_dtypes(include=[np.number])
    correlations = {}
    if len(numeric_df.columns) >= 2:
        try:
            # Drop rows with nulls for correlation or calculate pairwise
            corr_df = numeric_df.corr(method="pearson")
            # Replace NaNs/Infs for JSON compliance
            corr_df = corr_df.replace({np.nan: None, np.inf: None, -np.inf: None})
            correlations = corr_df.to_dict()
        except Exception:
            pass
            
    # 4. Missingness Analysis per column (null rates for visual plots)
    missingness = {}
    for col_name, stats in column_stats.items():
        missingness[col_name] = {
            "missing_count": stats["missing_count"],
            "missing_percentage": stats["missing_percentage"]
        }

    profile_data = {
        "dataset_id": id,
        "filename": db_dataset.filename,
        "dataset_stats": dataset_stats,
        "column_stats": column_stats,
        "quality_report": quality_report,
        "correlations": correlations,
        "missingness": missingness
    }
    return clean_nans_for_json(profile_data)
