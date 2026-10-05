"""Functional coverage for Tracker status updates and follow-ups."""


class TestApplicationTracker:
    def test_list_applications_includes_tracker_payload(self, client, user_headers):
        response = client.get("/api/job-automation/applications?limit=50", headers=user_headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert "applications" in body
        assert "tracker" in body
        assert "stats" in body["tracker"]
        assert "all" in body["tracker"]
        assert "interviews" in body["tracker"]
        assert "actionNeeded" in body["tracker"]

    def test_update_application_status_to_interview(self, client, user_headers):
        workspace = client.get("/api/job-automation/workspace", headers=user_headers)
        assert workspace.status_code == 200
        rows = workspace.json()["applications"]["all"]
        assert rows, "expected seed applications"
        app_id = rows[0]["id"]

        updated = client.patch(
            f"/api/job-automation/applications/{app_id}",
            headers=user_headers,
            json={"status": "Interview"},
        )
        assert updated.status_code == 200, updated.text
        payload = updated.json()
        assert payload["success"] is True
        assert payload["application"]["status"] == "Interview"
        assert payload["application"]["id"] == app_id

        refreshed = client.get("/api/job-automation/workspace", headers=user_headers)
        interviews = refreshed.json()["applications"]["interviews"]
        assert any(row["id"] == app_id for row in interviews)

    def test_follow_up_moves_applied_into_action_needed(self, client, user_headers):
        workspace = client.get("/api/job-automation/workspace", headers=user_headers)
        rows = workspace.json()["applications"]["all"]
        target = next((row for row in rows if row.get("status") == "Applied"), rows[0])

        # Ensure baseline status is Applied when possible.
        if target["status"] != "Applied":
            client.patch(
                f"/api/job-automation/applications/{target['id']}",
                headers=user_headers,
                json={"status": "Applied"},
            )

        follow = client.post(
            f"/api/job-automation/applications/{target['id']}/follow-up",
            headers=user_headers,
            json={"note": "Ping recruiter about timeline"},
        )
        assert follow.status_code == 200, follow.text
        body = follow.json()
        assert body["success"] is True
        assert body["application"]["status"] == "Action Needed"
        assert "Follow-up scheduled" in body["application"]["action"]

        refreshed = client.get("/api/job-automation/workspace", headers=user_headers)
        action_needed = refreshed.json()["applications"]["actionNeeded"]
        assert any(row["id"] == target["id"] for row in action_needed)
