import os

from fastapi.testclient import TestClient


def build_client(tmp_path):
    os.environ["PERIOD_TRACKER_DB"] = str(tmp_path / "test.db")
    from app.main import app

    return TestClient(app)


def register(client, **overrides):
    payload = {
        "name": "Ayse",
        "email": "ayse@example.com",
        "password": "guvenli-parola-123",
        "last_period_start": "2026-04-03",
        "average_cycle_length": 28,
        "average_period_length": 5,
    }
    payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


def test_period_crud_and_insights(tmp_path):
    with build_client(tmp_path) as client:
        assert register(client).status_code == 200

        first = client.post(
            "/api/periods",
            json={
                "start_date": "2026-05-01",
                "end_date": "2026-05-05",
                "flow": "medium",
                "symptoms": ["Kramp"],
                "notes": "Ilk kayit",
            },
        )
        second = client.post(
            "/api/periods",
            json={
                "start_date": "2026-05-29",
                "end_date": "2026-06-02",
                "flow": "light",
                "symptoms": [],
                "notes": "",
            },
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert len(client.get("/api/periods").json()) == 3

        updated = client.put(
            f"/api/periods/{first.json()['id']}",
            json={
                "start_date": "2026-05-01",
                "end_date": "2026-05-06",
                "flow": "heavy",
                "symptoms": ["Kramp", "Yorgunluk"],
                "notes": "Guncellendi",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["end_date"] == "2026-05-06"
        assert updated.json()["flow"] == "heavy"

        response = client.get("/api/insights", params={"today": "2026-06-10"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["average_cycle_length"] == 28
        assert payload["average_period_length"] == 6
        assert payload["next_period_start"] == "2026-06-26"
        assert payload["days_until_next_period"] == 16

        deleted = client.delete(f"/api/periods/{first.json()['id']}")
        assert deleted.status_code == 204
        assert len(client.get("/api/periods").json()) == 2


def test_protected_routes_and_validation(tmp_path):
    with build_client(tmp_path) as client:
        assert client.get("/api/periods").status_code == 401
        assert register(client).status_code == 200

        response = client.post(
            "/api/periods",
            json={
                "start_date": "2026-05-10",
                "end_date": "2026-05-01",
                "flow": "medium",
            },
        )
        assert response.status_code == 422


def test_register_logout_and_returning_login(tmp_path):
    with build_client(tmp_path) as client:
        assert client.get("/api/auth/session").json() is None

        response = register(
            client,
            last_period_start="2026-07-10",
            average_cycle_length=31,
            average_period_length=6,
        )
        assert response.status_code == 200
        assert response.json()["email"] == "ayse@example.com"
        assert client.get("/api/auth/session").json()["email"] == "ayse@example.com"

        profile = client.get("/api/profile").json()
        assert profile["name"] == "Ayse"
        profile_update = client.put(
            "/api/profile",
            json={
                "name": "Ayse Luna",
                "average_cycle_length": 30,
                "average_period_length": 5,
            },
        )
        assert profile_update.status_code == 200
        assert profile_update.json()["name"] == "Ayse Luna"
        assert len(client.get("/api/periods").json()) == 1
        periods = client.get("/api/periods").json()
        assert periods[0]["start_date"] == "2026-07-10"
        assert periods[0]["end_date"] == "2026-07-15"

        insights = client.get(
            "/api/insights", params={"today": "2026-07-20"}
        ).json()
        assert insights["average_cycle_length"] == 30
        assert insights["average_period_length"] == 5
        assert insights["next_period_start"] == "2026-08-09"
        assert insights["ovulation_date"] == "2026-07-26"
        assert insights["pms_window_start"] == "2026-08-02"
        assert insights["pms_window_end"] == "2026-08-08"

        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/profile").status_code == 401
        assert client.post(
            "/api/auth/login",
            json={"email": "ayse@example.com", "password": "yanlis-parola"},
        ).status_code == 401

        login = client.post(
            "/api/auth/login",
            json={
                "email": "AYSE@example.com",
                "password": "guvenli-parola-123",
            },
        )
        assert login.status_code == 200
        assert client.get("/api/profile").json()["name"] == "Ayse Luna"
        assert len(client.get("/api/periods").json()) == 1


def test_only_one_account_can_be_registered(tmp_path):
    with build_client(tmp_path) as client:
        assert register(client).status_code == 200
        client.post("/api/auth/logout")
        duplicate = register(
            client,
            email="baska@example.com",
            password="baska-guvenli-parola",
        )
        assert duplicate.status_code == 409
