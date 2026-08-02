import os
from datetime import date

from fastapi.testclient import TestClient


def build_client(tmp_path):
    os.environ["PERIOD_TRACKER_DB"] = str(tmp_path / "test.db")
    from app.main import app

    return TestClient(app)


def test_period_crud_and_insights(tmp_path):
    with build_client(tmp_path) as client:
        first = client.post(
            "/api/periods",
            json={
                "start_date": "2026-05-01",
                "end_date": "2026-05-05",
                "flow": "medium",
                "symptoms": ["Kramp"],
                "notes": "İlk kayıt",
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
        assert len(client.get("/api/periods").json()) == 2

        response = client.get("/api/insights", params={"today": "2026-06-10"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["average_cycle_length"] == 28
        assert payload["average_period_length"] == 5
        assert payload["next_period_start"] == "2026-06-26"
        assert payload["days_until_next_period"] == 16

        deleted = client.delete(f"/api/periods/{first.json()['id']}")
        assert deleted.status_code == 204
        assert len(client.get("/api/periods").json()) == 1


def test_rejects_invalid_date_range(tmp_path):
    with build_client(tmp_path) as client:
        response = client.post(
            "/api/periods",
            json={
                "start_date": "2026-05-10",
                "end_date": "2026-05-01",
                "flow": "medium",
            },
        )
        assert response.status_code == 422


def test_onboarding_creates_profile_and_personalized_prediction(tmp_path):
    with build_client(tmp_path) as client:
        assert client.get("/api/profile").json() is None

        response = client.put(
            "/api/profile",
            json={
                "name": "Ayse",
                "last_period_start": "2026-07-10",
                "average_cycle_length": 31,
                "average_period_length": 6,
            },
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Ayse"

        periods = client.get("/api/periods").json()
        assert len(periods) == 1
        assert periods[0]["start_date"] == "2026-07-10"
        assert periods[0]["end_date"] == "2026-07-15"

        insights = client.get(
            "/api/insights", params={"today": "2026-07-20"}
        ).json()
        assert insights["average_cycle_length"] == 31
        assert insights["average_period_length"] == 6
        assert insights["next_period_start"] == "2026-08-10"
