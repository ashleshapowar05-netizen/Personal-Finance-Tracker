import uuid

from app import app


app.config["TESTING"] = True
app.config["SECRET_KEY"] = "test-secret"


def test_login_page_loads():
    client = app.test_client()
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome Back" in response.data


def test_register_and_login_flow():
    client = app.test_client()
    unique_email = f"alice-{uuid.uuid4().hex[:8]}@example.com"

    register_response = client.post(
        "/register",
        data={
            "name": "Alice Test",
            "email": unique_email,
            "password": "secret123",
        },
        follow_redirects=True,
    )
    assert register_response.status_code == 200
    assert b"Registration successful" in register_response.data

    login_response = client.post(
        "/login",
        data={
            "email": unique_email,
            "password": "secret123",
        },
        follow_redirects=True,
    )
    assert login_response.status_code == 200
    assert b"Good to see you" in login_response.data
