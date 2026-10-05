#!/usr/bin/env python3
"""
Populate PostgreSQL database with sample data based on models.
"""
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import User, Campaign, Contact, JobApplication, Portal
from app.core.config import get_settings

def seed_database():
    settings = get_settings()

    if not settings.database_url:
        print("ERROR: DATABASE_URL not configured in .env")
        sys.exit(1)

    # Normalize the URL
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(db_url, echo=False, future=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Clear existing data
        print("Clearing existing data...")
        session.query(JobApplication).delete()
        session.query(Contact).delete()
        session.query(Campaign).delete()
        session.query(Portal).delete()
        session.query(User).delete()
        session.commit()

        # Insert Users
        print("Inserting users...")
        users = [
            User(
                name="Sarah Mitchell",
                email="sarah@marketingmind.ai",
                password_hash="hashed_password_123",
                role="admin",
                is_active=True,
            ),
            User(
                name="John Recruiter",
                email="john@marketingmind.ai",
                password_hash="hashed_password_456",
                role="user",
                is_active=True,
            ),
            User(
                name="Komal Sharma",
                email="komal@marketingmind.ai",
                password_hash="hashed_password_789",
                role="user",
                is_active=True,
            ),
            User(
                name="Mike Johnson",
                email="mike@marketingmind.ai",
                password_hash="hashed_password_012",
                role="admin",
                is_active=True,
            ),
        ]
        session.add_all(users)
        session.commit()
        print(f"   Created {len(users)} users")

        # Insert Portals
        print("Inserting portals...")
        portals = [
            Portal(name="LinkedIn", url="https://www.linkedin.com/jobs/", status="Active"),
            Portal(name="Indeed", url="https://www.indeed.com/jobs", status="Active"),
            Portal(name="Dice", url="https://www.dice.com/jobs", status="Active"),
            Portal(name="ZipRecruiter", url="https://www.ziprecruiter.com/Jobs/", status="Active"),
        ]
        session.add_all(portals)
        session.commit()
        print(f"   Created {len(portals)} portals")

        # Insert Campaigns
        print("Inserting campaigns...")
        campaigns = [
            Campaign(
                name="May Talent Pulse - Southwest",
                subject="Available consultants | {{candidate_name}} | {{location}} | C2C",
                body="Hi {{recruiter_name}},\n\nWe have an excellent candidate {{candidate_name}} based in {{location}} with {{skills}} experience.\n\nRate: {{rate}}/hr\nAvailability: {{availability}}\nVisa Status: {{visa_status}}\n\nWould you be interested in connecting?\n\nBest regards,\nMarketingMind AI",
                status="Active",
                scheduled_for="2025-05-01",
                sent_count=250,
                opened_count=85,
                replied_count=12,
            ),
            Campaign(
                name="Q2 Tech Talent Outreach",
                subject="Top {{skills}} Professional - {{company_name}}",
                body="Hello {{recruiter_name}},\n\nI hope this message finds you well. We have identified {{candidate_name}}, an exceptional {{skills}} professional...",
                status="Draft",
                scheduled_for="2025-06-15",
                sent_count=0,
                opened_count=0,
                replied_count=0,
            ),
            Campaign(
                name="Spring Contractor Push",
                subject="Available {{skills}} Contractor - {{location}}",
                body="Hi {{recruiter_name}},\n\nWould you be interested in a top {{skills}} contractor for your upcoming projects?",
                status="Completed",
                scheduled_for="2025-04-01",
                sent_count=180,
                opened_count=72,
                replied_count=18,
            ),
        ]
        session.add_all(campaigns)
        session.commit()
        print(f"   Created {len(campaigns)} campaigns")

        # Insert Contacts
        print("Inserting contacts...")
        contacts = [
            Contact(
                name="Alice Thompson",
                email="alice@techcorp.com",
                company="TechCorp Solutions",
                list_name="Q2 Outreach",
                status="Queued",
            ),
            Contact(
                name="Bob Martinez",
                email="bob@innovate.com",
                company="Innovate Systems",
                list_name="Q2 Outreach",
                status="Sent",
            ),
            Contact(
                name="Carol Wilson",
                email="carol@cloudpro.io",
                company="CloudPro Inc",
                list_name="Spring Contractors",
                status="Opened",
            ),
            Contact(
                name="David Chen",
                email="david@softdev.com",
                company="SoftDev Corp",
                list_name="Spring Contractors",
                status="Replied",
            ),
            Contact(
                name="Emma Davis",
                email="emma@techtalent.io",
                company="TechTalent Recruiting",
                list_name="Q2 Outreach",
                status="Queued",
            ),
            Contact(
                name="Frank Anderson",
                email="frank@hiringsolutions.com",
                company="Hiring Solutions LLC",
                list_name="May Pulse",
                status="Bounced",
            ),
        ]
        session.add_all(contacts)
        session.commit()
        print(f"   Created {len(contacts)} contacts")

        # Insert Job Applications
        print("Inserting job applications...")
        job_apps = [
            JobApplication(
                role="Senior Python Developer",
                company="TechCorp Solutions",
                status="Applied",
                stage="Applied",
                updated_label="2 days ago",
                action_label="Follow up scheduled",
            ),
            JobApplication(
                role="Full Stack Engineer",
                company="Innovate Systems",
                status="Interview",
                stage="Technical Round",
                updated_label="1 day ago",
                action_label="Prepare for coding challenge",
            ),
            JobApplication(
                role="Data Scientist",
                company="CloudPro Inc",
                status="Interview",
                stage="Final Round",
                updated_label="Today",
                action_label="Schedule final interview",
            ),
            JobApplication(
                role="DevOps Engineer",
                company="SoftDev Corp",
                status="Offer",
                stage="Offer",
                updated_label="Today",
                action_label="Review offer details",
            ),
            JobApplication(
                role="Machine Learning Engineer",
                company="AI Innovations",
                status="Applied",
                stage="Screening",
                updated_label="3 days ago",
                action_label="Awaiting recruiter feedback",
            ),
            JobApplication(
                role="Backend Engineer",
                company="FinTech Solutions",
                status="Rejected",
                stage="Rejected",
                updated_label="1 week ago",
                action_label="Look for similar roles",
            ),
            JobApplication(
                role="Frontend Engineer",
                company="StartupXYZ",
                status="Applied",
                stage="Applied",
                updated_label="5 days ago",
                action_label="Send portfolio link",
            ),
            JobApplication(
                role="Cloud Architect",
                company="Enterprise Corp",
                status="Interview",
                stage="Hiring Manager Round",
                updated_label="2 days ago",
                action_label="Research company more",
            ),
        ]
        session.add_all(job_apps)
        session.commit()
        print(f"   Created {len(job_apps)} job applications")

        print("\nDatabase successfully populated with sample data!")
        print(f"  - {len(users)} Users")
        print(f"  - {len(portals)} Portals")
        print(f"  - {len(campaigns)} Campaigns")
        print(f"  - {len(contacts)} Contacts")
        print(f"  - {len(job_apps)} Job Applications")

    except Exception as e:
        print(f"Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
