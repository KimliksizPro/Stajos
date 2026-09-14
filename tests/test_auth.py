def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json["success"] is True


def test_register_and_login_flow(client):
    # register
    r = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "secret123", "full_name": "Ali"})
    assert r.status_code == 201
    assert r.json["success"] is True

    # duplicate
    r = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "secret123", "full_name": "Ali"})
    assert r.status_code == 409
    assert r.json["success"] is False

    # login
    r = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 200
    assert "access_token" in r.json["data"]
    assert "refresh_token" in r.json["data"]
    token = r.json["data"]["access_token"]
    refresh = r.json["data"]["refresh_token"]

    # me without token -> 401 standardized
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json["success"] is False

    # me with token
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json["data"]["email"] == "a@b.com"

    # refresh
    r = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 200
    assert "access_token" in r.json["data"]

    # wrong password
    r = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401

    # standardization: 404
    r = client.get("/nope")
    assert r.json["success"] is False
    assert "errors" in r.json
