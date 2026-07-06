import uuid
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from backend.app.database.session import get_db
from backend.app.models import models
from backend.app.schemas import schemas
from backend.app.api.routes.auth import get_current_user
from backend.app.services.file_service import load_dataframe
from backend.app.services.recommendation_service import generate_recommendations
from backend.app.api.routes.visualizations import normalize_aggregation
from backend.app.utils.json_cleaner import clean_nans_for_json

router = APIRouter()

def execute_widget_query(df: pd.DataFrame, config: models.SavedChart, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Executes pandas query grouping and aggregation for a saved chart config,
    applying optional global filters.
    """
    query_df = df.copy()
    
    # Apply global filters
    if filters:
        for f_col, f_val in filters.items():
            if f_col in query_df.columns and f_val is not None and f_val != "":
                query_df = query_df[query_df[f_col].astype(str) == str(f_val)]
                
    # Fill missing values to keep keys aligned
    query_df[config.x_axis] = query_df[config.x_axis].fillna("Missing")
    if config.group_by:
        query_df[config.group_by] = query_df[config.group_by].fillna("None")
        
    group_keys = [config.x_axis]
    if config.group_by:
        group_keys.append(config.group_by)
        
    agg = normalize_aggregation(config.aggregate)
    
    if agg == "none":
        select_cols = [config.x_axis]
        if config.y_axis:
            select_cols.append(config.y_axis)
        if config.group_by:
            select_cols.append(config.group_by)
        result_df = query_df[select_cols].head(1000)
    else:
        if agg == "count":
            result_df = query_df.groupby(group_keys).size().reset_index(name="value")
        else:
            if not config.y_axis:
                return []
            query_df[config.y_axis] = pd.to_numeric(query_df[config.y_axis], errors="coerce")
            
            if agg == "sum":
                result_df = query_df.groupby(group_keys)[config.y_axis].sum().reset_index()
            elif agg == "average":
                result_df = query_df.groupby(group_keys)[config.y_axis].mean().reset_index()
            elif agg == "min":
                result_df = query_df.groupby(group_keys)[config.y_axis].min().reset_index()
            elif agg == "max":
                result_df = query_df.groupby(group_keys)[config.y_axis].max().reset_index()
            elif agg == "median":
                result_df = query_df.groupby(group_keys)[config.y_axis].median().reset_index()
            else:
                return []
            result_df.rename(columns={config.y_axis: "value"}, inplace=True)
            
    return clean_nans_for_json(result_df.to_dict(orient="records"))


@router.post("", response_model=schemas.DashboardResponse)
def create_dashboard(
    dashboard_in: schemas.DashboardCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a dashboard for a dataset. If the dataset has no saved charts,
    it automatically generates standard charts from recommendations and links them.
    """
    db_dataset = db.query(models.Dataset).filter(
        models.Dataset.id == dashboard_in.dataset_id,
        models.Dataset.user_id == current_user.id
    ).first()
    
    if not db_dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found or access denied."
        )
        
    # Check if this dataset already has saved charts
    saved_charts = db.query(models.SavedChart).filter(
        models.SavedChart.dataset_id == db_dataset.id
    ).all()
    
    # If no saved charts exist, let's create default ones from recommendations
    if not saved_charts:
        try:
            df = load_dataframe(db_dataset.storage_path)
            from backend.app.services.profiling_service import get_column_stats
            column_stats = get_column_stats(df)
            recs = generate_recommendations(df, column_stats)
            
            # Save the first 3 recommended configs
            for rec in recs[:3]:
                db_chart = models.SavedChart(
                    dataset_id=db_dataset.id,
                    title=rec["title"],
                    chart_type=rec["chart_type"],
                    x_axis=rec["x_axis"],
                    y_axis=rec["y_axis"],
                    aggregate=rec["aggregate"],
                    group_by=rec["group_by"]
                )
                db.add(db_chart)
            db.commit()
            
            saved_charts = db.query(models.SavedChart).filter(
                models.SavedChart.dataset_id == db_dataset.id
            ).all()
        except Exception as e:
            # Fallback if recommendations fail: continue with empty dashboard
            pass

    # Create Dashboard
    db_dashboard = models.Dashboard(
        user_id=current_user.id,
        dataset_id=db_dataset.id,
        title=dashboard_in.title,
        description=dashboard_in.description
    )
    db.add(db_dashboard)
    db.flush()
    
    # Auto-populate widgets for all saved charts in a side-by-side layout
    for idx, chart in enumerate(saved_charts):
        layout_dict = {
            "x": (idx % 2) * 6, # 2 columns layout: width 6 each (total grid width 12)
            "y": (idx // 2) * 4,
            "w": 6,
            "h": 4
        }
        db_widget = models.DashboardWidget(
            dashboard_id=db_dashboard.id,
            chart_config_id=chart.id,
            widget_type="chart",
            layout=json.dumps(layout_dict),
            title=chart.title
        )
        db.add(db_widget)
        
    db.commit()
    db.refresh(db_dashboard)
    return db_dashboard


@router.get("", response_model=List[schemas.DashboardResponse])
def list_dashboards(
    dataset_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all dashboards owned by the user. Optional filter by dataset_id.
    """
    query = db.query(models.Dashboard).filter(models.Dashboard.user_id == current_user.id)
    if dataset_id:
        query = query.filter(models.Dashboard.dataset_id == dataset_id)
    return query.order_by(models.Dashboard.created_at.desc()).all()


@router.get("/{id}")
def get_dashboard_details(
    id: uuid.UUID,
    filters: Optional[str] = Query(None, description="JSON string dictionary of column-level filter slices"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves dashboard metadata, widgets layout, and resolves query aggregation
    data points dynamically for each widget under optional global filter overrides.
    """
    dashboard = db.query(models.Dashboard).filter(
        models.Dashboard.id == id,
        models.Dashboard.user_id == current_user.id
    ).first()
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found or access denied."
        )
        
    parsed_filters = None
    if filters:
        try:
            parsed_filters = json.loads(filters)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filters JSON format."
            )
            
    # Load dataset to evaluate queries
    try:
        df = load_dataframe(dashboard.dataset.storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading dashboard dataset: {str(e)}"
        )
        
    # Build widget payload with dynamic chart query results
    widgets_list = []
    for widget in dashboard.widgets:
        widget_data = {
            "id": widget.id,
            "dashboard_id": widget.dashboard_id,
            "chart_config_id": widget.chart_config_id,
            "widget_type": widget.widget_type,
            "layout": widget.layout,
            "title": widget.title,
            "created_at": widget.created_at,
            "chart_config": widget.chart_config,
            "datapoints": []
        }
        
        if widget.widget_type == "chart" and widget.chart_config:
            widget_data["datapoints"] = execute_widget_query(df, widget.chart_config, parsed_filters)
            
        widgets_list.append(widget_data)
        
    # Return custom extended dictionary
    return {
        "id": dashboard.id,
        "user_id": dashboard.user_id,
        "dataset_id": dashboard.dataset_id,
        "title": dashboard.title,
        "description": dashboard.description,
        "created_at": dashboard.created_at,
        "widgets": widgets_list
    }


@router.put("/{id}", response_model=schemas.DashboardResponse)
def update_dashboard(
    id: uuid.UUID,
    dashboard_in: schemas.DashboardUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates dashboard metadata (title and description).
    """
    dashboard = db.query(models.Dashboard).filter(
        models.Dashboard.id == id,
        models.Dashboard.user_id == current_user.id
    ).first()
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found or access denied."
        )
        
    if dashboard_in.title is not None:
        dashboard.title = dashboard_in.title
    if dashboard_in.description is not None:
        dashboard.description = dashboard_in.description
        
    db.commit()
    db.refresh(dashboard)
    return dashboard


@router.put("/{id}/layouts")
def update_widget_layouts(
    id: uuid.UUID,
    layouts_in: List[schemas.DashboardWidgetLayoutUpdate],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates layout dimensions and positions for dashboard widgets.
    """
    dashboard = db.query(models.Dashboard).filter(
        models.Dashboard.id == id,
        models.Dashboard.user_id == current_user.id
    ).first()
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found or access denied."
        )
        
    # Map widgets for fast lookup
    widget_map = {w.id: w for w in dashboard.widgets}
    
    for layout_update in layouts_in:
        if layout_update.id in widget_map:
            widget_map[layout_update.id].layout = layout_update.layout
            
    db.commit()
    return {"detail": "Widget layouts updated successfully."}


@router.delete("/{id}")
def delete_dashboard(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes the dashboard.
    """
    dashboard = db.query(models.Dashboard).filter(
        models.Dashboard.id == id,
        models.Dashboard.user_id == current_user.id
    ).first()
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found or access denied."
        )
        
    db.delete(dashboard)
    db.commit()
    return {"detail": "Dashboard deleted successfully."}
