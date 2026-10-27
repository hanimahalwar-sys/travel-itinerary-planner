import os
import tempfile

# Must be set before the app is imported: force local storage + built-in AI engine.
_tmp = tempfile.mkdtemp()
os.environ["LOCAL_DATA_FILE"] = os.path.join(_tmp, "trips.json")
os.environ["LLM_API_KEY"] = ""
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def headers():
    return {"X-User-Id": "test-user-001"}
