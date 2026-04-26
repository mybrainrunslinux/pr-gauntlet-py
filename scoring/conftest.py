"""Pytest fixtures for FlowForge scoring tests.

Starts a real uvicorn server on port 9201 with an isolated SQLite DB per session.
"""

import os
import subprocess
import sys
import tempfile
import time

import httpx
import pytest

BASE_URL = "http://127.0.0.1:9201"
APP_DIR = os.path.join(os.path.dirname(__file__), "..")


def _get_token() -> str:
    r = httpx.post(f"{BASE_URL}/token", json={"username": "testbot", "password": "x"}, timeout=5)
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def server():
    tmpdir = tempfile.mkdtemp(prefix="flowforge_test_")
    env = {**os.environ, "PYTHONPATH": APP_DIR}
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1",
            "--port", "9201",
            "--log-level", "warning",
        ],
        cwd=tmpdir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for readiness — poll GET /workflows
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE_URL}/workflows", timeout=2)
            if r.status_code in (200, 401, 422):
                break
        except Exception:
            pass
        time.sleep(0.3)
    else:
        proc.terminate()
        raise RuntimeError("FlowForge server did not start in time")

    yield BASE_URL

    proc.terminate()
    proc.wait(timeout=5)
    # Clean up temp DB
    db_path = os.path.join(tmpdir, "flowforge.db")
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client(server):
    """httpx client pre-configured with base URL."""
    with httpx.Client(base_url=server, timeout=10) as c:
        yield c


@pytest.fixture
def auth_headers(server):
    token = _get_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_workflow(client, auth_headers):
    """Factory: create a workflow and return its dict."""
    def _make(name="test-wf", steps=None):
        if steps is None:
            steps = [{"name": "step-a", "depends_on": [], "max_retries": 0}]
        r = client.post("/workflows", json={"name": name, "description": "", "steps": steps},
                        headers=auth_headers)
        r.raise_for_status()
        return r.json()
    return _make
