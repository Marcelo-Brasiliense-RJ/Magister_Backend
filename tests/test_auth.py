import jwt

from app.core.security import create_access_token, decode_access_token


def test_login_ok(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert resp.status_code == 401


def test_protected_route_without_token(client):
    resp = client.post("/api/tutors", json={"title": "X"})
    assert resp.status_code == 401


def test_protected_route_bad_token(client):
    resp = client.get("/api/tutors", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_protected_route_with_token(client, admin_token):
    resp = client.get("/api/tutors", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_jwt_roundtrip_and_tamper():
    token = create_access_token("admin")
    assert decode_access_token(token)["role"] == "admin"
    try:
        decode_access_token(token + "x")
        raise AssertionError("token adulterado deveria falhar")
    except jwt.PyJWTError:
        pass
