"""Shared pytest fixtures for SUPER GIRL backend tests."""
import os
import pytest
import requests
from pathlib import Path

# load frontend/.env manually to get EXPO_PUBLIC_BACKEND_URL
_env_file = Path("/app/frontend/.env")
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("EXPO_PUBLIC_BACKEND_URL not set")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(api_client):
    r = api_client.post(f"{BASE_URL}/api/auth/login",
                        json={"email": "admin@supergirl.app",
                              "password": "Admin123!"})
    assert r.status_code == 200, f"admin login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def operator_token(api_client):
    r = api_client.post(f"{BASE_URL}/api/auth/login",
                        json={"email": "operatore@supergirl.app",
                              "password": "Operatore123!"})
    assert r.status_code == 200, f"operator login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"}


@pytest.fixture
def operator_headers(operator_token):
    return {"Authorization": f"Bearer {operator_token}",
            "Content-Type": "application/json"}
