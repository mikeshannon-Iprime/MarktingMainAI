-- =============================================================================
-- MarketingMind AI — PostgreSQL Database Schema
-- =============================================================================
-- Source:     app/db/models.py (SQLAlchemy 2.x)
-- Tables:     32
-- PostgreSQL: 14+
-- Generator:  scripts/generate_schema_sql.py
--
-- Apply schema only (no seed data):
--   psql -U postgres -d postgres -f database/schema.sql
--
-- Apply schema + seed demo data:
--   python scripts/init_postgres_schema.py
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- Drop existing tables (reverse dependency order)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS linkedin_sequence_steps CASCADE;
DROP TABLE IF EXISTS tailored_resumes CASCADE;
DROP TABLE IF EXISTS saved_jobs CASCADE;
DROP TABLE IF EXISTS linkedin_sequences CASCADE;
DROP TABLE IF EXISTS job_applications CASCADE;
DROP TABLE IF EXISTS job_analyses CASCADE;
DROP TABLE IF EXISTS user_settings CASCADE;
DROP TABLE IF EXISTS user_resumes CASCADE;
DROP TABLE IF EXISTS search_configs CASCADE;
DROP TABLE IF EXISTS portals CASCADE;
DROP TABLE IF EXISTS notification_deliveries CASCADE;
DROP TABLE IF EXISTS linkedin_settings CASCADE;
DROP TABLE IF EXISTS linkedin_recruiters CASCADE;
DROP TABLE IF EXISTS linkedin_outreach_queue CASCADE;
DROP TABLE IF EXISTS linkedin_message_templates CASCADE;
DROP TABLE IF EXISTS linkedin_jobs CASCADE;
DROP TABLE IF EXISTS linkedin_followups CASCADE;
DROP TABLE IF EXISTS linkedin_api_keys CASCADE;
DROP TABLE IF EXISTS job_results CASCADE;
DROP TABLE IF EXISTS job_profiles CASCADE;
DROP TABLE IF EXISTS job_automation_settings CASCADE;
DROP TABLE IF EXISTS contact_lists CASCADE;
DROP TABLE IF EXISTS carriers CASCADE;
DROP TABLE IF EXISTS campaign_templates CASCADE;
DROP TABLE IF EXISTS campaign_settings CASCADE;
DROP TABLE IF EXISTS campaign_items CASCADE;
DROP TABLE IF EXISTS campaign_contacts CASCADE;
DROP TABLE IF EXISTS auth_sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS submission_months CASCADE;
DROP TABLE IF EXISTS linkedin_api_sources CASCADE;
DROP TABLE IF EXISTS day_report_rows CASCADE;

-- -----------------------------------------------------------------------------
-- Auth & users
-- -----------------------------------------------------------------------------

-- Table: users — Application accounts (recruiter, admin, super_admin)
CREATE TABLE users (
	id SERIAL NOT NULL,
	external_id VARCHAR(64),
	name VARCHAR(120) NOT NULL,
	email VARCHAR(255) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	role VARCHAR(32) NOT NULL,
	phone VARCHAR(40),
	company VARCHAR(120),
	title VARCHAR(120),
	department VARCHAR(120),
	location VARCHAR(120),
	timezone VARCHAR(64),
	bio TEXT,
	is_active BOOLEAN NOT NULL,
	last_login TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);

-- Table: user_settings — Per-user notification and UI preferences
CREATE TABLE user_settings (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	email_notifications BOOLEAN NOT NULL,
	campaign_alerts BOOLEAN NOT NULL,
	job_alerts BOOLEAN NOT NULL,
	daily_report BOOLEAN NOT NULL,
	weekly_digest BOOLEAN NOT NULL,
	sms_notifications BOOLEAN NOT NULL,
	sms_phone VARCHAR(40),
	language VARCHAR(16) NOT NULL,
	date_format VARCHAR(32) NOT NULL,
	theme VARCHAR(16) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: auth_sessions — Bearer token sessions
CREATE TABLE auth_sessions (
	id SERIAL NOT NULL,
	token VARCHAR(128) NOT NULL,
	user_id INTEGER NOT NULL,
	email VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- Campaigns
-- -----------------------------------------------------------------------------

-- Table: campaign_settings — SMTP and campaign delivery options per user
CREATE TABLE campaign_settings (
	id SERIAL NOT NULL,
	user_id INTEGER,
	smtp_host VARCHAR(255) NOT NULL,
	smtp_port INTEGER NOT NULL,
	sender_limit INTEGER NOT NULL,
	smart_warmup BOOLEAN NOT NULL,
	unsubscribe_footer BOOLEAN NOT NULL,
	spam_guard BOOLEAN NOT NULL,
	gmail_sync BOOLEAN NOT NULL,
	outlook_sync BOOLEAN NOT NULL,
	open_tracking BOOLEAN NOT NULL,
	ai_subject_assist BOOLEAN NOT NULL,
	smtp_username VARCHAR(255),
	smtp_password VARCHAR(255),
	email_delay_seconds INTEGER NOT NULL,
	options_json JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: contact_lists — Named email recipient lists
CREATE TABLE contact_lists (
	id SERIAL NOT NULL,
	user_id INTEGER,
	name VARCHAR(120) NOT NULL,
	contacts_count INTEGER NOT NULL,
	open_rate INTEGER NOT NULL,
	reply_rate INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: campaign_contacts — Individual campaign recipients
CREATE TABLE campaign_contacts (
	id SERIAL NOT NULL,
	user_id INTEGER,
	name VARCHAR(120) NOT NULL,
	email VARCHAR(255) NOT NULL,
	company VARCHAR(255) NOT NULL,
	status VARCHAR(32) NOT NULL,
	list_name VARCHAR(120) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: campaign_templates — Reusable email templates
CREATE TABLE campaign_templates (
	id SERIAL NOT NULL,
	user_id INTEGER,
	name VARCHAR(120) NOT NULL,
	category VARCHAR(64) NOT NULL,
	description VARCHAR(255),
	subject VARCHAR(255) NOT NULL,
	body TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: campaign_items — Campaign runs (draft, scheduled, sent)
CREATE TABLE campaign_items (
	id SERIAL NOT NULL,
	user_id INTEGER,
	name VARCHAR(255) NOT NULL,
	from_name VARCHAR(120),
	from_email VARCHAR(255),
	reply_to VARCHAR(255),
	subject VARCHAR(255) NOT NULL,
	body TEXT NOT NULL,
	status VARCHAR(32) NOT NULL,
	scheduled_for VARCHAR(64),
	sent_count INTEGER NOT NULL,
	opened_count INTEGER NOT NULL,
	replied_count INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- Job automation
-- -----------------------------------------------------------------------------

-- Table: job_profiles — Candidate profile, resume metadata, skills (JSONB)
CREATE TABLE job_profiles (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	name VARCHAR(120) NOT NULL,
	email VARCHAR(255) NOT NULL,
	phone VARCHAR(40) NOT NULL,
	location VARCHAR(120) NOT NULL,
	linkedin VARCHAR(255) NOT NULL,
	experience VARCHAR(60) NOT NULL,
	employment_type VARCHAR(80) NOT NULL,
	rate VARCHAR(60) NOT NULL,
	visa VARCHAR(40) NOT NULL,
	work_mode VARCHAR(60) NOT NULL,
	job_titles JSONB NOT NULL,
	resume_file_name VARCHAR(255),
	resume_summary TEXT,
	resume_skills JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: user_resumes — Per-user CV library with isolated profile snapshots
CREATE TABLE user_resumes (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	file_name VARCHAR(255) NOT NULL,
	content_type VARCHAR(120),
	file_bytes BYTEA,
	summary TEXT,
	skills JSONB NOT NULL DEFAULT '[]'::jsonb,
	job_titles JSONB NOT NULL DEFAULT '[]'::jsonb,
	ml_score INTEGER,
	matched_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
	missing_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
	is_active BOOLEAN NOT NULL DEFAULT false,
	profile_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_user_resumes_user_file UNIQUE (user_id, file_name),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: job_automation_settings — Auto-apply threshold, schedule, toggles
CREATE TABLE job_automation_settings (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	auto_apply BOOLEAN NOT NULL,
	match_threshold INTEGER NOT NULL,
	max_applications INTEGER NOT NULL,
	alerts BOOLEAN NOT NULL,
	tailor_cv BOOLEAN NOT NULL,
	schedule_enabled BOOLEAN NOT NULL,
	schedule_label VARCHAR(255) NOT NULL,
	schedule_timezone VARCHAR(64) NOT NULL,
	schedule_time VARCHAR(8) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: search_configs — Job search titles, skills, filters (JSONB arrays)
CREATE TABLE search_configs (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	titles JSONB NOT NULL,
	required_skills JSONB NOT NULL,
	optional_skills JSONB NOT NULL,
	location VARCHAR(120) NOT NULL,
	radius VARCHAR(32) NOT NULL,
	filters JSONB NOT NULL,
	exclude_keywords JSONB NOT NULL,
	employment_type VARCHAR(80) NOT NULL,
	min_match_score INTEGER NOT NULL,
	posted_within VARCHAR(8) NOT NULL,
	experience_level VARCHAR(64) NOT NULL,
	rate_min VARCHAR(32) NOT NULL,
	rate_max VARCHAR(32) NOT NULL,
	repeat_every VARCHAR(32) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: portals — Job board URLs per user (Dice, Monster, etc.)
CREATE TABLE portals (
	id SERIAL NOT NULL,
	user_id INTEGER,
	name VARCHAR(120) NOT NULL,
	url VARCHAR(512) NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_portals_user_url UNIQUE (user_id,
	url),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: carriers — Company career page monitors
CREATE TABLE carriers (
	id SERIAL NOT NULL,
	user_id INTEGER,
	name VARCHAR(120) NOT NULL,
	url VARCHAR(512) NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_carriers_user_url UNIQUE (user_id,
	url),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: job_results — Scraped/matched job listings (manual integer PK)
CREATE TABLE job_results (
	id INTEGER NOT NULL,
	user_id INTEGER,
	role VARCHAR(512) NOT NULL,
	company VARCHAR(512) NOT NULL,
	location VARCHAR(255) NOT NULL,
	type VARCHAR(120) NOT NULL,
	posted VARCHAR(32) NOT NULL,
	rate VARCHAR(120),
	match INTEGER NOT NULL,
	hot BOOLEAN NOT NULL,
	skills JSONB NOT NULL,
	portal_name VARCHAR(120),
	portal_url VARCHAR(1024),
	source_url VARCHAR(1024),
	description TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: saved_jobs — User favorites junction (user_id, job_result_id)
CREATE TABLE saved_jobs (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	job_result_id INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_saved_jobs_user_job UNIQUE (user_id,
	job_result_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(job_result_id) REFERENCES job_results (id) ON DELETE CASCADE
);

-- Table: job_applications — Application tracker pipeline rows
CREATE TABLE job_applications (
	id SERIAL NOT NULL,
	user_id INTEGER,
	job_result_id INTEGER,
	role VARCHAR(255) NOT NULL,
	company VARCHAR(255) NOT NULL,
	status VARCHAR(64) NOT NULL,
	stage VARCHAR(255) NOT NULL,
	updated_label VARCHAR(64) NOT NULL,
	action_label VARCHAR(255) NOT NULL,
	portal VARCHAR(120),
	application_date DATE,
	match INTEGER,
	posting_url VARCHAR(512),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(job_result_id) REFERENCES job_results (id) ON DELETE SET NULL
);

-- Table: tailored_resumes — Per-job tailored CV content
CREATE TABLE tailored_resumes (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	job_result_id INTEGER NOT NULL,
	content TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_tailored_resumes_user_job UNIQUE (user_id,
	job_result_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(job_result_id) REFERENCES job_results (id) ON DELETE CASCADE
);

-- Table: linkedin_jobs — LinkedIn job search cache
CREATE TABLE linkedin_jobs (
	id SERIAL NOT NULL,
	user_id INTEGER,
	role VARCHAR(255) NOT NULL,
	company VARCHAR(255) NOT NULL,
	location VARCHAR(120) NOT NULL,
	type VARCHAR(64),
	posted VARCHAR(32),
	match INTEGER,
	easy_apply BOOLEAN NOT NULL,
	applicants INTEGER NOT NULL,
	insight TEXT,
	linkedin_url VARCHAR(512),
	experience_level VARCHAR(32),
	date_posted VARCHAR(32),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: job_analyses — CV vs job fit analysis results
CREATE TABLE job_analyses (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	job_result_id INTEGER,
	score INTEGER NOT NULL,
	tailored_score INTEGER,
	summary TEXT NOT NULL,
	hits JSONB NOT NULL,
	misses JSONB NOT NULL,
	suggestions JSONB NOT NULL,
	skill_gaps JSONB NOT NULL,
	recommendations JSONB NOT NULL,
	experience_match TEXT,
	title_match TEXT,
	job_description TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(job_result_id) REFERENCES job_results (id) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- LinkedIn recruiter
-- -----------------------------------------------------------------------------

-- Table: linkedin_recruiters — Discovered recruiter profiles
CREATE TABLE linkedin_recruiters (
	id SERIAL NOT NULL,
	user_id INTEGER,
	external_id INTEGER,
	name VARCHAR(120) NOT NULL,
	title VARCHAR(255) NOT NULL,
	company VARCHAR(255) NOT NULL,
	location VARCHAR(120) NOT NULL,
	techs JSONB NOT NULL,
	connection_degree VARCHAR(16) NOT NULL,
	avatar VARCHAR(8),
	match_score INTEGER NOT NULL,
	source VARCHAR(64) NOT NULL,
	email VARCHAR(255),
	note TEXT,
	status VARCHAR(32) NOT NULL,
	bookmarked BOOLEAN NOT NULL,
	contacted_at TIMESTAMP WITH TIME ZONE,
	replied_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: linkedin_sequences — Multi-step outreach sequences
CREATE TABLE linkedin_sequences (
	id SERIAL NOT NULL,
	user_id INTEGER,
	external_id INTEGER,
	name VARCHAR(120) NOT NULL,
	recruiter_id INTEGER,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(recruiter_id) REFERENCES linkedin_recruiters (id) ON DELETE SET NULL
);

-- Table: linkedin_sequence_steps — Steps within an outreach sequence
CREATE TABLE linkedin_sequence_steps (
	id SERIAL NOT NULL,
	sequence_id INTEGER NOT NULL,
	step_order INTEGER NOT NULL,
	label VARCHAR(120) NOT NULL,
	status VARCHAR(32) NOT NULL,
	step_date VARCHAR(32),
	PRIMARY KEY (id),
	FOREIGN KEY(sequence_id) REFERENCES linkedin_sequences (id) ON DELETE CASCADE
);

-- Table: linkedin_followups — Due follow-up reminders
CREATE TABLE linkedin_followups (
	id SERIAL NOT NULL,
	user_id INTEGER,
	name VARCHAR(120) NOT NULL,
	company VARCHAR(255) NOT NULL,
	due VARCHAR(64) NOT NULL,
	followup_type VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: linkedin_message_templates — Outreach message templates
CREATE TABLE linkedin_message_templates (
	id SERIAL NOT NULL,
	user_id INTEGER,
	name VARCHAR(120) NOT NULL,
	body TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: linkedin_outreach_queue — Scheduled LinkedIn outreach delivery queue
CREATE TABLE linkedin_outreach_queue (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	recruiter_ids JSONB NOT NULL,
	subject VARCHAR(300) NOT NULL,
	body TEXT NOT NULL,
	channel VARCHAR(64) NOT NULL,
	scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: linkedin_settings — LinkedIn automation limits and flags
CREATE TABLE linkedin_settings (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	auto_run_daily BOOLEAN NOT NULL,
	auto_enrich BOOLEAN NOT NULL,
	skip_contacted BOOLEAN NOT NULL,
	auto_followup BOOLEAN NOT NULL,
	ai_personalize BOOLEAN NOT NULL,
	max_per_day INTEGER NOT NULL,
	delay_seconds INTEGER NOT NULL,
	account_email VARCHAR(255) NOT NULL,
	daily_connections INTEGER NOT NULL,
	daily_inmails INTEGER NOT NULL,
	is_premium BOOLEAN NOT NULL,
	respect_dnc BOOLEAN NOT NULL,
	honor_unsubscribes BOOLEAN NOT NULL,
	use_permitted_sources BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: linkedin_api_sources — Third-party enrichment providers catalog
CREATE TABLE linkedin_api_sources (
	id SERIAL NOT NULL,
	external_id VARCHAR(32),
	name VARCHAR(120) NOT NULL,
	short_code VARCHAR(16) NOT NULL,
	description TEXT NOT NULL,
	status VARCHAR(32) NOT NULL,
	color VARCHAR(16) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);

-- Table: linkedin_api_keys — API keys per user and provider
CREATE TABLE linkedin_api_keys (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	provider VARCHAR(32) NOT NULL,
	api_key VARCHAR(512) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_linkedin_api_keys_user_provider UNIQUE (user_id,
	provider),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- Reporting
-- -----------------------------------------------------------------------------

-- Table: day_report_rows — Daily recruiter KPI activity rows
CREATE TABLE day_report_rows (
	id SERIAL NOT NULL,
	report_date DATE NOT NULL,
	recruiter VARCHAR(120) NOT NULL,
	technology VARCHAR(255) NOT NULL,
	linkedin INTEGER,
	calls INTEGER,
	sourced INTEGER,
	marketing INTEGER,
	notes TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);

-- Table: submission_months — Monthly submission totals for MoM/YoY charts
CREATE TABLE submission_months (
	id SERIAL NOT NULL,
	month VARCHAR(7) NOT NULL,
	submissions INTEGER NOT NULL,
	placement_rate FLOAT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);

-- Table: notification_deliveries — Audit log for email and SMS notification deliveries
CREATE TABLE notification_deliveries (
	id SERIAL NOT NULL,
	user_id INTEGER,
	channel VARCHAR(16) NOT NULL,
	event_type VARCHAR(64) NOT NULL,
	recipient VARCHAR(255) NOT NULL,
	subject VARCHAR(255),
	body TEXT,
	status VARCHAR(32) NOT NULL,
	provider_message_id VARCHAR(128),
	error_message TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE UNIQUE INDEX ix_users_external_id ON users (external_id);
CREATE UNIQUE INDEX ix_auth_sessions_token ON auth_sessions (token);
CREATE INDEX ix_campaign_contacts_email ON campaign_contacts (email);
CREATE INDEX ix_linkedin_recruiters_external_id ON linkedin_recruiters (external_id);
CREATE INDEX ix_linkedin_outreach_queue_scheduled_for ON linkedin_outreach_queue (scheduled_for);
CREATE INDEX ix_linkedin_outreach_queue_status ON linkedin_outreach_queue (status);
CREATE INDEX ix_linkedin_outreach_queue_user_id ON linkedin_outreach_queue (user_id);
CREATE INDEX ix_day_report_rows_report_date ON day_report_rows (report_date);
CREATE UNIQUE INDEX ix_submission_months_month ON submission_months (month);
CREATE INDEX ix_notification_deliveries_user_id ON notification_deliveries (user_id);
CREATE INDEX ix_user_resumes_user_id ON user_resumes (user_id);

-- -----------------------------------------------------------------------------
-- Table comments
-- -----------------------------------------------------------------------------
COMMENT ON TABLE users IS 'Application accounts (recruiter, admin, super_admin)';
COMMENT ON TABLE user_settings IS 'Per-user notification and UI preferences';
COMMENT ON TABLE auth_sessions IS 'Bearer token sessions';
COMMENT ON TABLE campaign_settings IS 'SMTP and campaign delivery options per user';
COMMENT ON TABLE contact_lists IS 'Named email recipient lists';
COMMENT ON TABLE campaign_contacts IS 'Individual campaign recipients';
COMMENT ON TABLE campaign_templates IS 'Reusable email templates';
COMMENT ON TABLE campaign_items IS 'Campaign runs (draft, scheduled, sent)';
COMMENT ON TABLE job_profiles IS 'Candidate profile, resume metadata, skills (JSONB)';
COMMENT ON TABLE job_automation_settings IS 'Auto-apply threshold, schedule, toggles';
COMMENT ON TABLE search_configs IS 'Job search titles, skills, filters (JSONB arrays)';
COMMENT ON TABLE portals IS 'Job board URLs per user (Dice, Monster, etc.)';
COMMENT ON TABLE carriers IS 'Company career page monitors';
COMMENT ON TABLE job_results IS 'Scraped/matched job listings (manual integer PK)';
COMMENT ON TABLE saved_jobs IS 'User favorites junction (user_id, job_result_id)';
COMMENT ON TABLE job_applications IS 'Application tracker pipeline rows';
COMMENT ON TABLE tailored_resumes IS 'Per-job tailored CV content';
COMMENT ON TABLE linkedin_jobs IS 'LinkedIn job search cache';
COMMENT ON TABLE job_analyses IS 'CV vs job fit analysis results';
COMMENT ON TABLE linkedin_recruiters IS 'Discovered recruiter profiles';
COMMENT ON TABLE linkedin_sequences IS 'Multi-step outreach sequences';
COMMENT ON TABLE linkedin_sequence_steps IS 'Steps within an outreach sequence';
COMMENT ON TABLE linkedin_followups IS 'Due follow-up reminders';
COMMENT ON TABLE linkedin_message_templates IS 'Outreach message templates';
COMMENT ON TABLE linkedin_outreach_queue IS 'Scheduled LinkedIn outreach delivery queue';
COMMENT ON TABLE linkedin_settings IS 'LinkedIn automation limits and flags';
COMMENT ON TABLE linkedin_api_sources IS 'Third-party enrichment providers catalog';
COMMENT ON TABLE linkedin_api_keys IS 'API keys per user and provider';
COMMENT ON TABLE day_report_rows IS 'Daily recruiter KPI activity rows';
COMMENT ON TABLE submission_months IS 'Monthly submission totals for MoM/YoY charts';
COMMENT ON TABLE notification_deliveries IS 'Audit log for email and SMS notification deliveries';

COMMIT;
