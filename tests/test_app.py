from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict

from config import Settings
from main import app


def test_index():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Добро пожаловать в гостевую книгу!"}


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_messages(client):
    assert client.get("/messages").json() == []


def test_messages_saved_and_newest_first(client):
    messages = [
        {"author": "Матвей", "text": "Первое сообщение"},
        {"author": "O'Reilly", "text": "'); DROP TABLE messages; --"},
    ]
    for message in messages:
        response = client.post("/messages", json=message)
        assert response.status_code == 200
        assert response.json() == {"ok": True}
    assert client.get("/messages").json() == list(reversed(messages))


def test_missing_text_rejected(client):
    assert client.post("/messages", json={"author": "Матвей"}).status_code == 422
    assert client.get("/messages").json() == []


def test_password_special_characters():
    password = "p@ss:/ word'\\end"
    settings = Settings(
        _env_file=None,
        db_host="localhost",
        db_port=5432,
        db_user="guestbook",
        db_password=password,
        db_name="guestbook_test",
    )
    assert conninfo_to_dict(settings.database_url)["password"] == password
