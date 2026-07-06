import os
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models import models
from backend.app.schemas import schemas
from backend.app.api.routes.auth import get_current_user
from backend.app.services.file_service import save_uploaded_file, load_dataframe, infer_column_type
from backend.app.utils.json_cleaner import clean_nans_for_json

router = APIRouter()

@router.post("/upload", response_model=schemas.DatasetPreviewResponse)
def upload_dataset(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a CSV/Excel file, parses it, extracts metadata/schema,
    saves the record inside the database linked to the user, and returns a preview.
    """
    file_path, file_size = save_uploaded_file(file)
    
    try:
        # Load and parse DataFrame
        df = load_dataframe(file_path)
        
        row_count = len(df)
        col_count = len(df.columns)
        
        # Link to current authenticated user
        db_dataset = models.Dataset(
            user_id=current_user.id,
            filename=file.filename,
            storage_path=file_path,
            mime_type=file.content_type,
            file_size=file_size,
            row_count=row_count,
            col_count=col_count
        )
        db.add(db_dataset)
        db.flush()  # Acquire auto-generated dataset ID
        
        columns_schema_list = []
        
        for col_name in df.columns:
            series = df[col_name]
            detected_type = infer_column_type(str(col_name), series)
            
            missing_count = int(series.isna().sum())
            unique_count = int(series.nunique(dropna=True))
            is_nullable = bool(series.isna().any())
            
            db_column = models.DatasetColumn(
                dataset_id=db_dataset.id,
                name=str(col_name),
                detected_type=detected_type,
                unique_count=unique_count,
                missing_count=missing_count,
                is_nullable=is_nullable
            )
            db.add(db_column)
            
            columns_schema_list.append(
                schemas.DatasetColumnSchema(
                    name=str(col_name),
                    detected_type=detected_type,
                    unique_count=unique_count,
                    missing_count=missing_count,
                    is_nullable=is_nullable
                )
            )
            
        db.commit()
        db.refresh(db_dataset)
        
        preview_rows = df.head(10).to_dict(orient="records")
        
        metadata_res = schemas.DatasetMetadataSchema(
            id=db_dataset.id,
            filename=db_dataset.filename,
            mime_type=db_dataset.mime_type,
            file_size=db_dataset.file_size,
            row_count=db_dataset.row_count,
            col_count=db_dataset.col_count,
            created_at=db_dataset.created_at,
            columns=columns_schema_list
        )
        
        preview_data = schemas.DatasetPreviewResponse(
            metadata=metadata_res,
            preview_rows=preview_rows
        )
        return clean_nans_for_json(preview_data.model_dump())
        
    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("", response_model=List[schemas.DatasetMetadataSchema])
def list_datasets(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all datasets uploaded by the current authenticated user.
    """
    return db.query(models.Dataset).filter(
        models.Dataset.user_id == current_user.id
    ).order_by(models.Dataset.created_at.desc()).all()

@router.get("/{id}", response_model=schemas.DatasetPreviewResponse)
def get_dataset(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches details and top 10 preview rows of a specific dataset owned by the user.
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
        preview_rows = df.head(10).to_dict(orient="records")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading stored dataset file: {str(e)}"
        )
        
    columns_schema_list = [
        schemas.DatasetColumnSchema(
            name=col.name,
            detected_type=col.detected_type,
            unique_count=col.unique_count,
            missing_count=col.missing_count,
            is_nullable=col.is_nullable
        ) for col in db_dataset.columns
    ]
    
    metadata_res = schemas.DatasetMetadataSchema(
        id=db_dataset.id,
        filename=db_dataset.filename,
        mime_type=db_dataset.mime_type,
        file_size=db_dataset.file_size,
        row_count=db_dataset.row_count,
        col_count=db_dataset.col_count,
        created_at=db_dataset.created_at,
        columns=columns_schema_list
    )
    
    preview_data = schemas.DatasetPreviewResponse(
        metadata=metadata_res,
        preview_rows=preview_rows
    )
    return clean_nans_for_json(preview_data.model_dump())

@router.delete("/{id}")
def delete_dataset(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a user's dataset from DB metadata registry and removes its filesystem binary file.
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
        
    # Delete binary file from disk
    if os.path.exists(db_dataset.storage_path):
        try:
            os.remove(db_dataset.storage_path)
        except Exception as e:
            # Continue deleting from DB even if OS fail (so UI cleans up)
            pass
            
    db.delete(db_dataset)
    db.commit()
    return {"detail": "Dataset and all associated records deleted successfully."}

def run_aggregation_query(df: Any, x_axis: str, y_axis: Optional[str], aggregate: str, group_by: Optional[str], filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    import pandas as pd
    query_df = df.copy()
    
    # Apply filters
    for f in filters:
        col = f["column"]
        op = f["operator"]
        val = f["value"]
        if col in query_df.columns:
            if op == "equals":
                query_df = query_df[query_df[col].astype(str) == str(val)]
            elif op == "not_equals":
                query_df = query_df[query_df[col].astype(str) != str(val)]
            elif op == "greater_than":
                query_df = query_df[pd.to_numeric(query_df[col], errors="coerce") > float(val)]
            elif op == "greater_than_or_equal":
                query_df = query_df[pd.to_numeric(query_df[col], errors="coerce") >= float(val)]
            elif op == "less_than":
                query_df = query_df[pd.to_numeric(query_df[col], errors="coerce") < float(val)]
            elif op == "less_than_or_equal":
                query_df = query_df[pd.to_numeric(query_df[col], errors="coerce") <= float(val)]
            elif op == "in":
                vals_list = [str(v).strip() for v in val] if isinstance(val, list) else [str(val).strip()]
                query_df = query_df[query_df[col].astype(str).isin(vals_list)]
                
    # Fill missing values
    query_df[x_axis] = query_df[x_axis].fillna("Missing")
    if group_by:
        query_df[group_by] = query_df[group_by].fillna("None")
        
    group_keys = [x_axis]
    if group_by:
        group_keys.append(group_by)
        
    agg = aggregate.lower().strip() if aggregate else "none"
    if agg in ["count", "count instances", "occurrence_count"]:
        agg = "count"
        
    if agg == "none":
        select_cols = [x_axis]
        if y_axis:
            select_cols.append(y_axis)
        if group_by:
            select_cols.append(group_by)
        result_df = query_df[select_cols].head(1000)
    else:
        if agg == "count":
            result_df = query_df.groupby(group_keys).size().reset_index(name="value")
        else:
            if not y_axis:
                return []
            query_df[y_axis] = pd.to_numeric(query_df[y_axis], errors="coerce")
            if agg in ["sum", "total"]:
                result_df = query_df.groupby(group_keys)[y_axis].sum().reset_index()
            elif agg in ["average", "mean", "avg"]:
                result_df = query_df.groupby(group_keys)[y_axis].mean().reset_index()
            elif agg == "min":
                result_df = query_df.groupby(group_keys)[y_axis].min().reset_index()
            elif agg == "max":
                result_df = query_df.groupby(group_keys)[y_axis].max().reset_index()
            elif agg == "median":
                result_df = query_df.groupby(group_keys)[y_axis].median().reset_index()
            else:
                return []
            result_df.rename(columns={y_axis: "value"}, inplace=True)
            
    from backend.app.utils.json_cleaner import clean_nans_for_json
    return clean_nans_for_json(result_df.to_dict(orient="records"))

@router.post("/{id}/ask", response_model=schemas.NLQueryResponse)
def ask_dataset_question(
    id: uuid.UUID,
    req_body: schemas.NLQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts a natural language question about the dataset, parses it, validates it against
    the dataset schema, runs the query, and generates a factual explanation.
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
        
    from backend.app.services.profiling_service import get_column_stats
    column_metadata = get_column_stats(df)
    
    from backend.app.services.nl_query_service import parse_question
    parse_result = parse_question(req_body.question, df, column_metadata)
    
    if parse_result.status == "error":
        return parse_result
        
    if parse_result.status == "ambiguous":
        return parse_result
        
    chart_spec = parse_result.chart_spec
    
    try:
        x_axis = chart_spec.x_axis
        y_axis = chart_spec.y_axis
        agg = chart_spec.aggregation
        chart_type = chart_spec.chart_type
        group_by = chart_spec.group_by
        filters = [f.model_dump() for f in chart_spec.filters]
        
        if x_axis not in df.columns:
            raise ValueError(f"Column '{x_axis}' does not exist in dataset.")
            
        x_type = column_metadata[x_axis]["detected_type"]
        
        if y_axis:
            if y_axis not in df.columns:
                raise ValueError(f"Column '{y_axis}' does not exist in dataset.")
            y_type = column_metadata[y_axis]["detected_type"]
        else:
            y_type = None
            
        if agg in ["sum", "average", "median", "min", "max"]:
            if not y_axis:
                raise ValueError(f"Y-axis is required for '{agg}' aggregation.")
            if y_type != "Numeric":
                raise ValueError(f"Aggregation '{agg}' requires numeric Y-axis, but '{y_axis}' is {y_type}.")
                
        if chart_type == "scatter":
            if not y_axis:
                raise ValueError("Scatter plot requires both X-axis and Y-axis variables.")
            if x_type != "Numeric" or y_type != "Numeric":
                raise ValueError("Scatter plot requires both X-axis and Y-axis variables to be Numeric.")
                
        if chart_type == "histogram":
            if x_type != "Numeric":
                raise ValueError("Histogram requires a Numeric column on the X-axis.")
                
        if chart_type == "pie":
            if x_type not in ["Categorical", "Boolean", "Identifier", "Geographic candidate"]:
                raise ValueError("Pie chart requires a categorical or boolean X-axis.")
                
        for f in chart_spec.filters:
            f_col = f.column
            f_op = f.operator
            f_val = f.value
            if f_col not in df.columns:
                raise ValueError(f"Filter column '{f_col}' does not exist in dataset.")
            f_type = column_metadata[f_col]["detected_type"]
            if f_type == "Numeric" and f_op in ["greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal"]:
                try:
                    float(f_val)
                except (ValueError, TypeError):
                    raise ValueError(f"Filter value '{f_val}' for numeric column '{f_col}' must be a valid number.")
                    
    except ValueError as val_err:
        return schemas.NLQueryResponse(
            question=req_body.question,
            status="error",
            clarification=schemas.NLQueryClarification(
                reason=f"Visualization specification failed validation: {str(val_err)}",
                suggested_columns=list(column_metadata.keys())[:3],
                suggested_charts=["bar", "line", "pie"]
            )
        )
        
    try:
        chart_data = run_aggregation_query(df, x_axis, y_axis, agg, group_by, filters)
    except Exception as run_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(run_err)}"
        )
        
    from backend.app.services.explanation_service import generate_insights
    insight = generate_insights(chart_spec, chart_data)
    
    parse_result.chart_data = chart_data
    parse_result.insight = insight
    return parse_result

