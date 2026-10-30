import os

import pytest
from fastapi.testclient import TestClient

# A separate disposable database is mandatory: tests delete its messages.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "guestbook")
os.environ.setdefault("DB_PASSWORD", "ci_test_password")
os.environ.setdefault("DB_NAME", "guestbook_test")

from main import app, connect


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        with connect() as conn:
            conn.execute("TRUNCATE messages RESTART IDENTITY")
        try:
            yield test_client
        finally:
            with connect() as conn:
                conn.execute("TRUNCATE messages RESTART IDENTITY")
