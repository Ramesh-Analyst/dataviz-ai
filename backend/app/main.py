from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database.session import Base, engine, get_db
from backend.app.api.routes import datasets, auth, profiling, visualizations, dashboards, insights

# Automatically compile tables inside local SQLite database (or active PostgreSQL)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DataViz AI API",
    description="Automated Data Analysis and Visualization Platform API Backend Services",
    version="1.0.0"
)

# CORS Policy configuration to allow cross-origin React frontend inquiries
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route Registry
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
app.include_router(profiling.router, prefix="/api/datasets", tags=["profiling"])
app.include_router(visualizations.router, prefix="/api/datasets", tags=["visualizations"])
app.include_router(dashboards.router, prefix="/api/dashboards", tags=["dashboards"])
app.include_router(insights.router, prefix="/api/datasets", tags=["insights"])

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """
    Checks backend service status and verifies active SQL database connections.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "detail": str(e)
        }

@app.get("/")
def read_root():
    return {
        "message": "Welcome to DataViz AI API Services",
        "documentation": "/docs"
    }
