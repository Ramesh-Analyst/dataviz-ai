import uuid
import json
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.database.session import get_db
from backend.app.models import models
from backend.app.schemas import schemas
from backend.app.api.routes.auth import get_current_user
from backend.app.services.file_service import load_dataframe
from backend.app.services.profiling_service import get_column_stats
from backend.app.services.recommendation_service import generate_recommendations

router = APIRouter()

def normalize_aggregation(agg_str: Optional[str]) -> str:
    if not agg_str:
        return "none"
    agg_lower = agg_str.lower().strip()
    if agg_lower in ["count", "count instances", "occurrence_count"]:
        return "count"
    if agg_lower in ["sum", "total"]:
        return "sum"
    if agg_lower in ["average", "mean", "avg"]:
        return "average"
    if agg_lower in ["min", "minimum"]:
        return "min"
    if agg_lower in ["max", "maximum"]:
        return "max"
    if agg_lower in ["median"]:
        return "median"
    return "none"

class QueryRequest(BaseModel):
    x_axis: str
    y_axis: Optional[str] = None
    aggregate: Optional[str] = "none" # sum, average, min, max, count, none
    group_by: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    chart_type: Optional[str] = None

@router.get("/{id}/visualizations/recommendations")
def get_chart_recommendations(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes statistical metadata profiling and generates logical visualization
    recommendations for a user's dataset.
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
            detail=f"Error loading dataset: {str(e)}"
        )
        
    column_stats = get_column_stats(df)
    recommendations = generate_recommendations(df, column_stats)
    return recommendations


@router.post("/{id}/visualizations/query")
def execute_aggregation_query(
    id: uuid.UUID,
    req: QueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a Pandas grouping and aggregation query to compute plot datapoints
    for custom charts dynamically.
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
            detail=f"Error loading dataset: {str(e)}"
        )
        
    # Validation: Verify columns exist
    if req.x_axis not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Column '{req.x_axis}' does not exist in dataset."
        )
    if req.y_axis and req.y_axis not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Column '{req.y_axis}' does not exist in dataset."
        )
    if req.group_by and req.group_by not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Column '{req.group_by}' does not exist in dataset."
        )

    agg = normalize_aggregation(req.aggregate)

    # Validation: Aggregate constraints
    if agg != "count" and agg != "none":
        if not req.y_axis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Y-axis column is required for '{agg}' aggregation."
            )

    # Validation: Chart Type specific validation rules
    def get_col_type(col_name):
        series = df[col_name].dropna()
        from backend.app.services.file_service import infer_column_type
        return infer_column_type(col_name, series)

    if req.chart_type:
        chart_lower = req.chart_type.lower()
        if chart_lower == "pie":
            # Pie: Categorical dimension with count or numeric aggregation
            x_type = get_col_type(req.x_axis)
            if x_type not in ["Categorical", "Boolean", "Identifier", "Geographic candidate"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pie chart requires a categorical, boolean, or identifier dimension on the X-axis."
                )
        elif chart_lower == "scatter":
            # Scatter: Two numeric columns required
            if not req.y_axis:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Scatter plot requires both X-axis and Y-axis variables."
                )
            x_type = get_col_type(req.x_axis)
            y_type = get_col_type(req.y_axis)
            if x_type != "Numeric" or y_type != "Numeric":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Scatter plot requires both X-axis and Y-axis variables to be Numeric."
                )
        elif chart_lower == "histogram":
            # Histogram: One numeric column required
            x_type = get_col_type(req.x_axis)
            if x_type != "Numeric":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Histogram requires a Numeric column on the X-axis."
                )
        elif chart_lower == "line":
            # Line: Ordered/date/numeric X and numeric measure
            x_type = get_col_type(req.x_axis)
            if x_type not in ["Date/time", "Numeric", "Identifier"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Line chart requires an ordered variable (Date/time or Numeric) on the X-axis."
                )
            if req.y_axis:
                y_type = get_col_type(req.y_axis)
                if y_type != "Numeric" and agg != "count":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Line chart measures on the Y-axis must be Numeric."
                    )

    try:
        query_df = df.copy()
        
        # Apply global dashboard filters if supplied
        if req.filters:
            for f_col, f_val in req.filters.items():
                if f_col in query_df.columns and f_val is not None and f_val != "":
                    query_df = query_df[query_df[f_col].astype(str) == str(f_val)]
                    
        # Fill missing values of x_axis or group_by with placeholders to keep groups unified
        query_df[req.x_axis] = query_df[req.x_axis].fillna("Missing")
        if req.group_by:
            query_df[req.group_by] = query_df[req.group_by].fillna("None")

        group_keys = [req.x_axis]
        if req.group_by:
            group_keys.append(req.group_by)
            
        if agg == "none":
            # Just select raw rows, cap at 1000 records to prevent frontend lockups
            select_cols = [req.x_axis]
            if req.y_axis:
                select_cols.append(req.y_axis)
            if req.group_by:
                select_cols.append(req.group_by)
            
            result_df = query_df[select_cols].head(1000)
        else:
            if agg == "count":
                result_df = query_df.groupby(group_keys).size().reset_index(name="value")
            else:
                # Convert Y to numeric, replacing errors
                query_df[req.y_axis] = pd.to_numeric(query_df[req.y_axis], errors="coerce")
                
                if agg == "sum":
                    result_df = query_df.groupby(group_keys)[req.y_axis].sum().reset_index()
                elif agg == "average":
                    result_df = query_df.groupby(group_keys)[req.y_axis].mean().reset_index()
                elif agg == "min":
                    result_df = query_df.groupby(group_keys)[req.y_axis].min().reset_index()
                elif agg == "max":
                    result_df = query_df.groupby(group_keys)[req.y_axis].max().reset_index()
                elif agg == "median":
                    result_df = query_df.groupby(group_keys)[req.y_axis].median().reset_index()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unsupported aggregation type '{agg}'"
                    )
                result_df.rename(columns={req.y_axis: "value"}, inplace=True)
                
        # Clean infinite and NaN values for JSON output safety using json_cleaner
        from backend.app.utils.json_cleaner import clean_nans_for_json
        datapoints = clean_nans_for_json(result_df.to_dict(orient="records"))
        
        return {"datapoints": datapoints}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


@router.post("/{id}/visualizations", response_model=schemas.SavedChartResponse)
def save_custom_chart(
    id: uuid.UUID,
    chart_in: schemas.SavedChartCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves a visualization config template tied to the specified dataset.
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
        
    normalized_aggregate = normalize_aggregation(chart_in.aggregate)
    
    # Duplicate check
    existing_chart = db.query(models.SavedChart).filter(
        models.SavedChart.dataset_id == db_dataset.id,
        models.SavedChart.title == chart_in.title,
        models.SavedChart.chart_type == chart_in.chart_type,
        models.SavedChart.x_axis == chart_in.x_axis,
        models.SavedChart.y_axis == chart_in.y_axis,
        models.SavedChart.aggregate == normalized_aggregate,
        models.SavedChart.group_by == chart_in.group_by
    ).first()
    
    if existing_chart:
        return existing_chart
        
    db_chart = models.SavedChart(
        dataset_id=db_dataset.id,
        title=chart_in.title,
        chart_type=chart_in.chart_type,
        x_axis=chart_in.x_axis,
        y_axis=chart_in.y_axis,
        aggregate=normalized_aggregate,
        group_by=chart_in.group_by
    )
    
    db.add(db_chart)
    db.flush()
    
    # Check if a dashboard already exists to sync widget
    db_dashboard = db.query(models.Dashboard).filter(
        models.Dashboard.dataset_id == db_dataset.id,
        models.Dashboard.user_id == current_user.id
    ).first()
    
    if db_dashboard:
        existing_widgets_count = db.query(models.DashboardWidget).filter(
            models.DashboardWidget.dashboard_id == db_dashboard.id
        ).count()
        
        layout_dict = {
            "x": (existing_widgets_count % 2) * 6,
            "y": (existing_widgets_count // 2) * 4,
            "w": 6,
            "h": 4
        }
        db_widget = models.DashboardWidget(
            dashboard_id=db_dashboard.id,
            chart_config_id=db_chart.id,
            widget_type="chart",
            layout=json.dumps(layout_dict),
            title=db_chart.title
        )
        db.add(db_widget)
        
    db.commit()
    db.refresh(db_chart)
    return db_chart


@router.get("/{id}/visualizations", response_model=List[schemas.SavedChartResponse])
def list_saved_charts(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all custom charts saved for the dataset.
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
        
    charts = db.query(models.SavedChart).filter(
        models.SavedChart.dataset_id == db_dataset.id
    ).order_by(models.SavedChart.created_at.desc()).all()
    
    return charts


@router.delete("/{id}/visualizations/{chart_id}")
def delete_saved_chart(
    id: uuid.UUID,
    chart_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a saved visualization config template.
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
        
    db_chart = db.query(models.SavedChart).filter(
        models.SavedChart.id == chart_id,
        models.SavedChart.dataset_id == db_dataset.id
    ).first()
    
    if not db_chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found."
        )
        
    db.delete(db_chart)
    db.commit()
    return {"detail": "Saved chart deleted successfully."}
