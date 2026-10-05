"""Functional API tests — Notifications (email/SMS setup)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.notifications


class TestNotificationSetup:
    def test_setup_status(self, client, user_headers):
        response = client.get("/api/notifications/setup", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert "emailConfigured" in body
        assert "smsConfigured" in body
        assert "smsProvider" in body
        assert "demoMode" in body

    def test_history_empty_or_list(self, client, user_headers):
        response = client.get("/api/notifications/history", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body.get("items"), list)


class TestNotificationDelivery:
    def test_test_email_demo_mode(self, client, user_headers):
        response = client.post(
            "/api/notifications/test-email",
            headers=user_headers,
            json={"email": "qa.notify@example.com"},
        )
        assert response.status_code == 200
        assert response.json().get("success") is True

    def test_test_sms_demo_mode(self, client, user_headers):
        response = client.post(
            "/api/notifications/test-sms",
            headers=user_headers,
            json={"phone": "+15555550128"},
        )
        assert response.status_code == 200
        assert response.json().get("success") is True

    def test_history_after_test(self, client, user_headers):
        client.post(
            "/api/notifications/test-email",
            headers=user_headers,
            json={"email": "qa.notify@example.com"},
        )
        history = client.get("/api/notifications/history", headers=user_headers).json()
        assert len(history.get("items", [])) >= 1


class TestNotificationPreferences:
    def test_save_sms_preferences(self, client, user_headers):
        settings = client.get("/api/user/settings", headers=user_headers).json()
        settings["notifications"]["smsNotifications"] = True
        settings["notifications"]["smsPhone"] = "+15555550199"
        response = client.put("/api/user/settings", headers=user_headers, json=settings)
        assert response.status_code == 200
        updated = client.get("/api/user/settings", headers=user_headers).json()
        assert updated["notifications"]["smsNotifications"] is True
        assert updated["notifications"]["smsPhone"] == "+15555550199"
