import datetime
import uuid
import sqlalchemy.types as types
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Boolean
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

def utcnow_naive():
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

class GUID(types.TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise CHAR(36), storing as string.
    """
    impl = types.CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID as pgUUID
            return dialect.type_descriptor(pgUUID())
        else:
            return dialect.type_descriptor(types.CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)

    datasets = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")
    dashboards = relationship("Dashboard", back_populates="user", cascade="all, delete-orphan")

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # Nullable for guest uploads
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=False)
    row_count = Column(Integer, nullable=False)
    col_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)

    user = relationship("User", back_populates="datasets")
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    saved_charts = relationship("SavedChart", back_populates="dataset", cascade="all, delete-orphan")

class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    detected_type = Column(String(100), nullable=False)
    unique_count = Column(Integer, nullable=True)
    missing_count = Column(Integer, nullable=True)
    is_nullable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow_naive)

    dataset = relationship("Dataset", back_populates="columns")

class SavedChart(Base):
    __tablename__ = "saved_charts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    chart_type = Column(String(50), nullable=False)  # bar, line, scatter, pie
    x_axis = Column(String(255), nullable=False)
    y_axis = Column(String(255), nullable=True)
    aggregate = Column(String(50), nullable=True)     # sum, average, min, max, count, none
    group_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)

    dataset = relationship("Dataset", back_populates="saved_charts")

class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)

    user = relationship("User", back_populates="dashboards")
    dataset = relationship("Dataset")
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")

class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    dashboard_id = Column(GUID(), ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False)
    chart_config_id = Column(GUID(), ForeignKey("saved_charts.id", ondelete="CASCADE"), nullable=True)
    widget_type = Column(String(50), nullable=False)  # 'chart' or 'kpi'
    layout = Column(String(512), nullable=True)        # Store serialized JSON string
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)

    dashboard = relationship("Dashboard", back_populates="widgets")
    chart_config = relationship("SavedChart")
