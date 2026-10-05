"""Shared fixtures for functional API tests (maps to backupfolder/FUNCTIONAL_TEST_CASES.md)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, or_

os.environ.setdefault("DICE_LIVE_SCRAPING_ENABLED", "false")
os.environ["PORTAL_APPLY_MODE"] = "demo"

from app.core.config import get_settings

get_settings.cache_clear()

from app.main import app

DEMO_USERS = {
    "user": {"email": "user@marketingmind.ai", "password": "User@123"},
    "admin": {"email": "admin@marketingmind.ai", "password": "Admin@123"},
    "super_admin": {"email": "superadmin@marketingmind.ai", "password": "Super@123"},
}

VALID_JOB_PROFILE = {
    "name": "Test Candidate",
    "email": "test.candidate@email.com",
    "phone": "+1 (555) 555-0128",
    "location": "Dallas, TX",
    "linkedin": "https://linkedin.com/in/testcandidate",
    "experience": "5-8 Years",
    "employmentType": "Both Contract & Full Time",
    "rate": "$85/hr",
    "visa": "H1B",
    "workMode": "Hybrid",
    "jobTitles": ["Java Developer", "Spring Boot Engineer"],
    "resumeSkills": ["Java", "Spring Boot", "AWS"],
}

VALID_AUTOMATION = {
    "autoApply": True,
    "matchThreshold": 75,
    "maxApplications": 20,
    "alerts": True,
    "tailorCv": False,
    "scheduleEnabled": False,
    "scheduleLabel": "Daily search",
    "scheduleTimezone": "America/New_York",
    "scheduleTime": "09:00",
}

VALID_SEARCH = {
    "titles": ["Java Developer"],
    "requiredSkills": ["Java"],
    "optionalSkills": ["AWS"],
    "location": "Remote",
    "radius": "50 miles",
    "filters": [],
    "excludeKeywords": [],
    "employmentType": "Both",
    "minMatchScore": 70,
    "postedWithin": "7",
    "experienceLevel": "Any",
    "rateMin": "",
    "rateMax": "",
    "repeatEvery": "Once daily",
}


SEEDED_USER_JOBS = [
    {"portal": "Dice", "url": "https://www.dice.com", "role": "Senior Java Developer", "company": "Pytest Dice Labs", "match": 99},
    {"portal": "Monster", "url": "https://www.monster.com", "role": "Spring Boot Engineer", "company": "Pytest Monster Works", "match": 98},
    {"portal": "CareerBuilder", "url": "https://www.careerbuilder.com", "role": "Java Microservices Engineer", "company": "Pytest CB Systems", "match": 97},
]

SEEDED_JOB_DESCRIPTION = (
    "Responsibilities: design and build Java and Spring Boot microservices on AWS, "
    "own REST APIs end to end, and collaborate with product and QA in Agile sprints. "
    "Requirements: 5+ years of Java, Spring Boot, AWS, Docker, SQL, and CI/CD experience."
)


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def seeded_user_workspace(client: TestClient):
    """Give the demo `user` role fresh (<=24h) job results and tracker rows.

    The DB seed attaches sample jobs/applications to the admin account only, so the
    user workspace is empty until a later test scrapes. Rows added here (and any
    applications tests create against them) are removed at session end.
    """
    from datetime import date

    from app.db.database import get_engine, session_scope
    from app.db.models import JobApplication, JobResult, User

    if get_engine() is None:
        yield
        return

    job_ids: list[int] = []
    application_ids: list[int] = []
    with session_scope() as session:
        user = session.query(User).filter(User.email == DEMO_USERS["user"]["email"]).one()
        user_id = user.id
        next_id = int(session.query(func.max(JobResult.id)).scalar() or 0) + 1
        for offset, job in enumerate(SEEDED_USER_JOBS):
            job_id = next_id + offset
            session.add(
                JobResult(
                    id=job_id,
                    user_id=user_id,
                    role=job["role"],
                    company=job["company"],
                    location="Remote",
                    type="Contract",
                    posted="2 hours ago",
                    rate="$85/hr",
                    match=job["match"],
                    hot=True,
                    skills=["Java", "Spring Boot", "AWS"],
                    portal_name=job["portal"],
                    portal_url=job["url"],
                    source_url=f"{job['url']}/job-detail/pytest-seed-{job_id}",
                    description=SEEDED_JOB_DESCRIPTION,
                )
            )
            job_ids.append(job_id)
        session.flush()

        for job_id, job, status in zip(job_ids, SEEDED_USER_JOBS, ("Interview", "Applied")):
            application = JobApplication(
                user_id=user_id,
                job_result_id=job_id,
                role=job["role"],
                company=job["company"],
                status=status,
                stage=status,
                updated_label=date.today().isoformat(),
                action_label="Await recruiter response",
                portal=job["portal"],
                application_date=date.today(),
                match=job["match"],
                posting_url=f"{job['url']}/job-detail/pytest-seed-{job_id}",
            )
            session.add(application)
            session.flush()
            application_ids.append(application.id)

    yield

    with session_scope() as session:
        session.query(JobApplication).filter(
            JobApplication.user_id == user_id,
            or_(JobApplication.id.in_(application_ids), JobApplication.job_result_id.in_(job_ids)),
        ).delete(synchronize_session=False)
        session.query(JobResult).filter(JobResult.id.in_(job_ids)).delete(synchronize_session=False)


def _login(client: TestClient, role: str = "user") -> dict:
    creds = DEMO_USERS[role]
    response = client.post("/api/auth/login", json=creds)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("token")
    return payload


@pytest.fixture
def user_auth(client: TestClient, seeded_user_workspace) -> dict:
    return _login(client, "user")


@pytest.fixture
def admin_auth(client: TestClient) -> dict:
    return _login(client, "admin")


@pytest.fixture
def user_headers(user_auth: dict) -> dict:
    return {"Authorization": f"Bearer {user_auth['token']}"}


@pytest.fixture
def admin_headers(admin_auth: dict) -> dict:
    return {"Authorization": f"Bearer {admin_auth['token']}"}
