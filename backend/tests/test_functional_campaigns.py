"""Functional API tests — Campaigns (CM-* / FUNCTIONAL_TEST_CASES.md)."""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.campaigns


class TestCampaignWorkspace:
    def test_workspace_has_metrics(self, client, user_headers):
        response = client.get("/api/campaigns/workspace", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert "metrics" in body
        metrics = body["metrics"]
        assert "emailsSent" in metrics
        assert "openRate" in metrics

    def test_templates_list(self, client, user_headers):
        templates = client.get("/api/campaigns/workspace", headers=user_headers).json()["templates"]
        assert isinstance(templates, list)
        assert len(templates) >= 1
        assert "name" in templates[0]
        assert "subject" in templates[0]


class TestCampaignPreview:
    def test_preview_merge_tags(self, client, user_headers):
        response = client.post(
            "/api/campaigns/preview",
            headers=user_headers,
            json={
                "subject": "Hello {{candidate_name}}",
                "body": "<p>Skills: {{skills}}</p>",
                "recipients": ["m.torres@tcs.com"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "previewHtml" in body
        assert body["recipientCount"] >= 1

    def test_template_preview(self, client, user_headers):
        response = client.post(
            "/api/campaigns/templates/preview",
            headers=user_headers,
            json={
                "subject": "Hello {{candidate_name}}",
                "body": "<p>Skills: {{skills}}</p>",
                "fromName": "Sarah Mitchell",
                "fromEmail": "sarah@techstaff.com",
                "replyTo": "recruiter@techstaff.com",
            },
        )
        assert response.status_code == 200
        assert response.json().get("previewHtml")


class TestCampaignAdmin:
    def test_save_draft(self, client, admin_headers):
        response = client.post(
            "/api/campaigns/drafts",
            headers=admin_headers,
            json={
                "campaignName": "QA Draft Campaign",
                "subject": "Test subject line",
                "body": "<p>Test body content</p>",
                "fromName": "Sarah Mitchell",
                "fromEmail": "sarah@techstaff.com",
                "replyTo": "recruiter@techstaff.com",
            },
        )
        assert response.status_code == 200
        assert response.json().get("success") is True

    def test_import_contacts(self, client, admin_headers):
        unique_email = f"qa.contact.{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/campaigns/contacts/import",
            headers=admin_headers,
            json={
                "contacts": [
                    {
                        "name": "QA Contact",
                        "email": unique_email,
                        "company": "QA Co",
                    }
                ],
                "listName": "QA Imports",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("imported", 0) >= 1
        assert body.get("skipped", 0) == 0

    def test_create_contact_list(self, client, admin_headers):
        response = client.post(
            "/api/campaigns/lists",
            headers=admin_headers,
            json={"name": "QA List"},
        )
        assert response.status_code == 200
        assert response.json().get("name") == "QA List"
