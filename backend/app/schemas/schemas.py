from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# --- AUTH SCHEMAS ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters.")
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[int] = None


# --- DATASET SCHEMAS ---

class DatasetColumnSchema(BaseModel):
    name: str
    detected_type: str
    unique_count: Optional[int] = None
    missing_count: Optional[int] = None
    is_nullable: bool = True

    model_config = ConfigDict(from_attributes=True)

class DatasetMetadataSchema(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: Optional[str] = None
    file_size: int
    row_count: int
    col_count: int
    created_at: datetime
    columns: List[DatasetColumnSchema] = []

    model_config = ConfigDict(from_attributes=True)

class DatasetPreviewResponse(BaseModel):
    metadata: DatasetMetadataSchema
    preview_rows: List[Dict[str, Any]]

class SavedChartCreate(BaseModel):
    title: str
    chart_type: str
    x_axis: str
    y_axis: Optional[str] = None
    aggregate: Optional[str] = None
    group_by: Optional[str] = None

class SavedChartResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    chart_type: str
    x_axis: str
    y_axis: Optional[str] = None
    aggregate: Optional[str] = None
    group_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- DASHBOARD SCHEMAS ---

class DashboardWidgetResponse(BaseModel):
    id: uuid.UUID
    dashboard_id: uuid.UUID
    chart_config_id: Optional[uuid.UUID] = None
    widget_type: str
    layout: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime
    chart_config: Optional[SavedChartResponse] = None

    model_config = ConfigDict(from_attributes=True)

class DashboardCreate(BaseModel):
    dataset_id: uuid.UUID
    title: str
    description: Optional[str] = None

class DashboardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class DashboardWidgetLayoutUpdate(BaseModel):
    id: uuid.UUID
    layout: str

class DashboardResponse(BaseModel):
    id: uuid.UUID
    user_id: int
    dataset_id: uuid.UUID
    title: str
    description: Optional[str] = None
    created_at: datetime
    widgets: List[DashboardWidgetResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --- NATURAL LANGUAGE QUERY SCHEMAS ---

class NLQueryRequest(BaseModel):
    question: str

class NLQueryFilterSpec(BaseModel):
    column: str
    operator: str  # equals, not_equals, greater_than, greater_than_or_equal, less_than, less_than_or_equal, in
    value: Any

class NLQueryChartSpec(BaseModel):
    chart_type: str  # bar, line, pie, scatter, histogram
    x_axis: str
    y_axis: Optional[str] = None
    aggregation: str  # count, sum, average, median, min, max, none
    group_by: Optional[str] = None
    filters: List[NLQueryFilterSpec] = []
    title: str

class NLQueryInsight(BaseModel):
    summary: str
    observations: List[str]

class NLQueryClarification(BaseModel):
    reason: str
    suggested_columns: List[str] = []
    suggested_charts: List[str] = []

class NLQueryResponse(BaseModel):
    question: str
    status: str = "success"  # success, ambiguous, error
    interpretation: Optional[str] = None
    chart_spec: Optional[NLQueryChartSpec] = None
    chart_data: Optional[List[Dict[str, Any]]] = None
    insight: Optional[NLQueryInsight] = None
    clarification: Optional[NLQueryClarification] = None

