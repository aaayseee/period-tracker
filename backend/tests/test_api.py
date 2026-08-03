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


def test_password_change_and_recovery_code_flow(tmp_path):
    with build_client(tmp_path) as client:
        registration = register(client)
        assert registration.status_code == 200
        original_recovery_code = registration.json()["recovery_code"]
        assert len(original_recovery_code.replace("-", "")) == 20

        wrong_change = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "yanlis-parola",
                "new_password": "yeni-guvenli-parola",
            },
        )
        assert wrong_change.status_code == 401

        changed = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "guvenli-parola-123",
                "new_password": "yeni-guvenli-parola",
            },
        )
        assert changed.status_code == 200
        assert client.get("/api/auth/session").json()["email"] == "ayse@example.com"

        rotated = client.post("/api/auth/recovery-code")
        assert rotated.status_code == 200
        active_recovery_code = rotated.json()["recovery_code"]
        assert active_recovery_code != original_recovery_code

        client.post("/api/auth/logout")
        assert client.post(
            "/api/auth/login",
            json={
                "email": "ayse@example.com",
                "password": "guvenli-parola-123",
            },
        ).status_code == 401
        assert client.post(
            "/api/auth/login",
            json={
                "email": "ayse@example.com",
                "password": "yeni-guvenli-parola",
            },
        ).status_code == 200
        client.post("/api/auth/logout")

        old_code = client.post(
            "/api/auth/recover",
            json={
                "email": "ayse@example.com",
                "recovery_code": original_recovery_code,
                "new_password": "kurtarilan-parola",
            },
        )
        assert old_code.status_code == 401

        recovered = client.post(
            "/api/auth/recover",
            json={
                "email": "ayse@example.com",
                "recovery_code": active_recovery_code.lower(),
                "new_password": "kurtarilan-parola",
            },
        )
        assert recovered.status_code == 200
        new_recovery_code = recovered.json()["recovery_code"]
        assert new_recovery_code != active_recovery_code
        assert client.get("/api/profile").status_code == 200

        client.post("/api/auth/logout")
        assert client.post(
            "/api/auth/login",
            json={
                "email": "ayse@example.com",
                "password": "kurtarilan-parola",
            },
        ).status_code == 200


def test_json_backup_restore_replace_and_merge(tmp_path):
    with build_client(tmp_path) as client:
        assert register(client).status_code == 200
        assert client.post(
            "/api/periods",
            json={
                "start_date": "2026-05-01",
                "end_date": "2026-05-05",
                "flow": "medium",
                "symptoms": ["Kramp"],
                "notes": "Yedeklenecek kayıt",
            },
        ).status_code == 201

        backup = client.get("/api/export").json()
        assert backup["schema_version"] == 1
        assert len(backup["periods"]) == 2

        assert client.put(
            "/api/profile",
            json={
                "name": "Yedek Sonrası",
                "average_cycle_length": 35,
                "average_period_length": 7,
            },
        ).status_code == 200
        assert client.post(
            "/api/periods",
            json={
                "start_date": "2026-06-01",
                "end_date": "2026-06-04",
                "flow": "light",
                "symptoms": [],
                "notes": "Yedekte yok",
            },
        ).status_code == 201

        restored = client.post(
            "/api/restore",
            json={"backup": backup, "mode": "replace"},
        )
        assert restored.status_code == 200
        assert restored.json() == {
            "mode": "replace",
            "imported_periods": 2,
            "skipped_periods": 0,
            "total_periods": 2,
            "profile_restored": True,
        }
        assert client.get("/api/profile").json()["name"] == "Ayse"
        assert all(
            period["start_date"] != "2026-06-01"
            for period in client.get("/api/periods").json()
        )

        assert client.put(
            "/api/profile",
            json={
                "name": "Mevcut Profil",
                "average_cycle_length": 30,
                "average_period_length": 6,
            },
        ).status_code == 200
        new_period = dict(backup["periods"][0])
        new_period.update(
            {
                "id": 999999,
                "start_date": "2026-06-15",
                "end_date": "2026-06-19",
                "notes": "Birleştirilen kayıt",
            }
        )
        merge_backup = {**backup, "periods": [*backup["periods"], new_period]}
        merged = client.post(
            "/api/restore",
            json={"backup": merge_backup, "mode": "merge"},
        )
        assert merged.status_code == 200
        assert merged.json() == {
            "mode": "merge",
            "imported_periods": 1,
            "skipped_periods": 2,
            "total_periods": 3,
            "profile_restored": False,
        }
        assert client.get("/api/profile").json()["name"] == "Mevcut Profil"
        assert any(
            period["start_date"] == "2026-06-15"
            for period in client.get("/api/periods").json()
        )

        duplicate_backup = {
            **backup,
            "periods": [backup["periods"][0], backup["periods"][0]],
        }
        assert client.post(
            "/api/restore",
            json={"backup": duplicate_backup, "mode": "replace"},
        ).status_code == 422

        assert client.post("/api/auth/logout").status_code == 204
        assert client.post(
            "/api/restore",
            json={"backup": backup, "mode": "replace"},
        ).status_code == 401


def test_secure_cookie_can_be_enabled_for_https(tmp_path, monkeypatch):
    monkeypatch.setenv("PERIOD_TRACKER_SECURE_COOKIE", "true")
    with build_client(tmp_path) as client:
        response = register(client)
        assert response.status_code == 200
        cookie_header = response.headers["set-cookie"].lower()
        assert "httponly" in cookie_header
        assert "samesite=strict" in cookie_header
        assert "secure" in cookie_header
