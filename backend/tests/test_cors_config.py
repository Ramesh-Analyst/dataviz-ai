import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import Settings
from backend.app.main import app

def test_cors_origins_defaults():
    # When CORS_ORIGINS is empty
    s = Settings(CORS_ORIGINS="")
    assert s.cors_origins_list == ["http://localhost:5173", "http://127.0.0.1:5173"]

def test_cors_origins_single():
    # When CORS_ORIGINS has a single origin
    s = Settings(CORS_ORIGINS="https://frontend.onrender.com")
    assert s.cors_origins_list == ["https://frontend.onrender.com"]

def test_cors_origins_multiple_whitespace():
    # When CORS_ORIGINS has multiple origins with whitespace
    s = Settings(CORS_ORIGINS=" http://localhost:5173,   https://app.com, http://example.org ")
    assert s.cors_origins_list == ["http://localhost:5173", "https://app.com", "http://example.org"]

def test_cors_origins_empty_elements():
    # When CORS_ORIGINS has extra/empty commas
    s = Settings(CORS_ORIGINS=",http://localhost:5173,,  https://app.com ,")
    assert s.cors_origins_list == ["http://localhost:5173", "https://app.com"]

def test_cors_middleware_response_headers():
    # Test using TestClient to verify the headers are returned for allowed origins
    client = TestClient(app)
    
    # 1. Allowed local origin (defaults)
    res = client.options("/api/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"
    })
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"

    # 2. Disallowed origin
    res = client.options("/api/health", headers={
        "Origin": "http://malicious-site.com",
        "Access-Control-Request-Method": "GET"
    })
    # For options CORS preflight, if origin is not allowed, it shouldn't send access-control-allow-origin
    assert res.headers.get("access-control-allow-origin") is None
