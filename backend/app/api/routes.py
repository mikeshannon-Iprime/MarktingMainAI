from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.auth import (
    ROLE_ADMIN,
    ROLE_SUPER_ADMIN,
    ROLE_USER,
    AuthError,
    get_auth_options,
    get_current_user,
    login_user,
    logout_user,
    register_user,
    require_roles,
)
from app.core.logging import get_logger

from app.schemas.api_models import (
    ActionResponse,
    AddCarrierRequest,
    AddPortalRequest,
    AnalyzeJobRequest,
    AutoApplyRequest,
    AutoApplyResponse,
    DeleteCarrierRequest,
    DeletePortalRequest,
    ImportCarriersRequest,
    ImportPortalsRequest,
    LinkedInJobSearchRequest,
    SaveTailoredResumeRequest,
    TailorResumeRequest,
    AnalysisResult,
    ApplyJobsRequest,
    ApplyJobsResponse,
    ApplicationFollowUpRequest,
    ApplicationMutationResponse,
    UpdateApplicationRequest,
    AutofillPreviewRequest,
    AutofillPreviewResponse,
    JobApplicationListResponse,
    JobApplicationStatusResponse,
    SaveJobRequest,
    SaveJobResponse,
    CampaignLaunchRequest,
    CampaignLaunchResponse,
    CampaignDraftRequest,
    CampaignDraftResponse,
    CampaignContactImportRequest,
    CampaignContactImportResponse,
    CampaignPreviewRequest,
    CampaignPreviewResponse,
    CampaignTemplatePreviewRequest,
    CampaignSettings,
    CampaignTestSendRequest,
    CampaignWorkspaceResponse,
    CarrierItem,
    ChangePasswordRequest,
    ContactList,
    ContactListCreateRequest,
    DayReportDashboardResponse,
    DayReportFilterRequest,
    EndpointCatalogResponse,
    HealthResponse,
    JobAutomationWorkspaceResponse,
    JobAutomationSettings,
    JobDescriptionRefreshResponse,
    JobProfile,
    LinkedInApiKeysRequest,
    LinkedInBookmarkRequest,
    LinkedInDiscoverRequest,
    LinkedInDiscoverResponse,
    LinkedInEnrichRequest,
    LinkedInEnrichResponse,
    LinkedInGenerateMessageRequest,
    LinkedInGenerateMessageResponse,
    LinkedInOutreachRequest,
    LinkedInMessageTemplate,
    LinkedInTemplateCreateRequest,
    LinkedInSettingsUpdateRequest,
    LinkedInWorkspaceResponse,
    LoginRequest,
    NotificationPreferences,
    NotificationHistoryResponse,
    NotificationSetupResponse,
    NotificationTestEmailRequest,
    NotificationTestSmsRequest,
    OverviewResponse,
    PortalItem,
    RegisterRequest,
    ResumeParseResponse,
    SearchConfigSaveRequest,
    SearchRunRequest,
    SearchRunResponse,
    SavedTailoredResumeResponse,
    StoredTailoredResumeResponse,
    SubmissionDashboardResponse,
    SubmissionFilterRequest,
    TailoredResumeResponse,
    AuthOptionsResponse,
    AuthResponse,
    TestDataAppendRequest,
    TestDataAppendResponse,
    TestDataDumpResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserResumeActionResponse,
    UserResumeListResponse,
    UserSettingsResponse,
)
from app.services.resume_ai import parse_resume_with_ai
from app.db.database import database_status
from app.services.seed_data import (
    add_carrier,
    add_portal,
    analyze_job,
    apply_jobs,
    get_job_application,
    list_recent_job_applications,
    update_job_application,
    schedule_application_followup,
    apply_linkedin_job,
    create_contact_list,
    create_linkedin_message_template,
    delete_carrier,
    delete_portal,
    enrich_linkedin_profiles,
    filter_day_report,
    filter_submissions,
    generate_linkedin_message,
    get_campaign_workspace,
    get_day_report_dashboard,
    get_endpoint_catalog,
    get_job_automation_workspace,
    get_linkedin_workspace,
    get_overview_payload,
    get_submission_dashboard,
    get_tailored_resume,
    get_test_data_payload,
    import_carriers,
    import_portals,
    refresh_job_description,
    launch_campaign,
    import_campaign_contacts,
    append_test_data_payload,
    preview_campaign,
    preview_template,
    preview_application_autofill,
    reset_test_data_payload,
    run_auto_apply,
    run_job_search,
    run_linkedin_discovery,
    save_automation_settings,
    save_campaign_draft,
    save_campaign_settings,
    save_job,
    save_job_profile,
    save_search_config,
    apply_parsed_resume,
    activate_user_resume,
    delete_user_resume,
    list_user_resumes,
    save_linkedin_api_keys,
    save_linkedin_settings,
    set_linkedin_recruiter_bookmark,
    save_tailored_resume,
    search_linkedin_jobs,
    send_linkedin_outreach,
    send_test_campaign,
    test_campaign_smtp,
    tailor_resume_for_job,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/auth/options", response_model=AuthOptionsResponse,
    tags=["Auth"],
)
def get_auth_bootstrap_options() -> dict:
    return get_auth_options()


@router.post("/api/auth/login", response_model=AuthResponse,
    tags=["Auth"],
)
def login(payload: LoginRequest) -> dict:
    try:
        return login_user(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/api/auth/register", response_model=AuthResponse,
    tags=["Auth"],
)
def register(payload: RegisterRequest) -> dict:
    try:
        return register_user(payload.name, payload.email, payload.password, payload.role)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/auth/logout", response_model=ActionResponse, dependencies=[Depends(get_current_user)],
    tags=["Auth"],
)
def logout(current_user: dict = Depends(get_current_user)) -> dict:
    logout_user(current_user["token"])
    return {"success": True, "message": "Logged out successfully."}


@router.get("/api/auth/me", response_model=AuthResponse, dependencies=[Depends(get_current_user)],
    tags=["Auth"],
)
def auth_me(current_user: dict = Depends(get_current_user)) -> dict:
    return {
        "token": current_user["token"],
        "user": {
            "id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
            "role": current_user["role"],
        },
    }


# ── User Profile Management ────────────────────────────────────────────


@router.get("/api/user/profile", response_model=UserProfileResponse, dependencies=[Depends(get_current_user)],
    tags=["User"],
)
def get_user_profile(current_user: dict = Depends(get_current_user)) -> dict:
    from app.services.seed_data import get_user_profile as get_profile_data
    profile = get_profile_data(current_user["id"])
    return {"user": profile}


@router.put("/api/user/profile", response_model=ActionResponse, dependencies=[Depends(get_current_user)],
    tags=["User"],
)
def update_user_profile(
    payload: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    from app.services.seed_data import update_user_profile as update_profile_data
    update_profile_data(current_user["id"], payload.model_dump(exclude_none=True))
    return {"success": True, "message": "Profile updated successfully."}


@router.put("/api/user/password", response_model=ActionResponse, dependencies=[Depends(get_current_user)],
    tags=["User"],
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    from app.services.seed_data import change_user_password
    try:
        change_user_password(current_user["id"], payload.currentPassword, payload.newPassword, payload.confirmPassword)
        return {"success": True, "message": "Password changed successfully."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/user/settings", response_model=UserSettingsResponse, dependencies=[Depends(get_current_user)],
    tags=["User"],
)
def get_user_settings(current_user: dict = Depends(get_current_user)) -> dict:
    from app.services.seed_data import get_user_settings as get_settings_data
    return get_settings_data(current_user["id"])


@router.put("/api/user/settings", response_model=ActionResponse, dependencies=[Depends(get_current_user)],
    tags=["User"],
)
def update_user_settings(
    payload: UserSettingsResponse,
    current_user: dict = Depends(get_current_user),
) -> dict:
    from app.services.seed_data import update_user_settings as update_settings_data
    update_settings_data(current_user["id"], payload.model_dump())
    return {"success": True, "message": "Settings updated successfully."}


@router.get(
    "/api/notifications/setup",
    response_model=NotificationSetupResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Notifications"],
)
def get_notifications_setup(current_user: dict = Depends(get_current_user)) -> dict:
    from app.services.notification_service import get_notification_setup

    return get_notification_setup(current_user["id"])


@router.get(
    "/api/notifications/history",
    response_model=NotificationHistoryResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Notifications"],
)
def get_notifications_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
) -> dict:
    from app.services.notification_service import get_notification_history

    return {"items": get_notification_history(current_user["id"], limit=limit)}


@router.post(
    "/api/notifications/test-email",
    response_model=ActionResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Notifications"],
)
def send_notifications_test_email(
    payload: NotificationTestEmailRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    from app.services.campaign_email import CampaignEmailError
    from app.services.notification_service import send_test_email

    try:
        result = send_test_email(current_user["id"], payload.email or None)
        return {"success": True, "message": result.get("message", "Test email sent.")}
    except (CampaignEmailError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/notifications/test-sms",
    response_model=ActionResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Notifications"],
)
def send_notifications_test_sms(
    payload: NotificationTestSmsRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    from app.services.notification_service import send_test_sms
    from app.services.sms_client import SmsDeliveryError

    try:
        result = send_test_sms(current_user["id"], payload.phone or None)
        return {"success": True, "message": result.get("message", "Test SMS sent.")}
    except (SmsDeliveryError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health", response_model=HealthResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Health"],
)
def health_check() -> dict:
    database = database_status()
    return {
        "status": "ok" if database["status"] == "available" else "degraded",
        "database": database,
        "modules": ["overview", "campaigns", "job-automation", "day-report", "submissions", "linkedin"],
    }


@router.get("/api/overview", response_model=OverviewResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Overview"],
)
def get_overview(current_user: dict = Depends(get_current_user)) -> dict:
    return get_overview_payload(current_user["id"])


@router.get("/api/campaigns/workspace", response_model=CampaignWorkspaceResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def get_campaigns_workspace(current_user: dict = Depends(get_current_user)) -> dict:
    return get_campaign_workspace(current_user["id"])


@router.post("/api/campaigns/preview", response_model=CampaignPreviewResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def preview_campaign_payload(payload: CampaignPreviewRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return preview_campaign(payload.subject, payload.body, payload.recipients, current_user["id"])


@router.post("/api/campaigns/templates/preview", response_model=CampaignPreviewResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def preview_template_payload(payload: CampaignTemplatePreviewRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return preview_template(
        payload.subject,
        payload.body,
        {
            "fromName": payload.fromName,
            "fromEmail": payload.fromEmail,
            "replyTo": payload.replyTo,
        },
        current_user["id"],
    )


@router.post("/api/campaigns/test-send", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def send_campaign_test(payload: CampaignTestSendRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return send_test_campaign(
        payload.email,
        payload.subject,
        payload.body,
        {
            "fromName": payload.fromName,
            "fromEmail": payload.fromEmail,
            "replyTo": payload.replyTo,
        },
        current_user["id"],
    )


@router.post("/api/campaigns/launch", response_model=CampaignLaunchResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def launch_campaign_payload(payload: CampaignLaunchRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return launch_campaign(payload.model_dump(), current_user["id"])


@router.post("/api/campaigns/drafts", response_model=CampaignDraftResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def save_campaign_draft_payload(payload: CampaignDraftRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return save_campaign_draft(payload.model_dump(), current_user["id"])


@router.post("/api/campaigns/contacts/import", response_model=CampaignContactImportResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def import_campaign_contacts_payload(payload: CampaignContactImportRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return import_campaign_contacts(payload.model_dump(), current_user["id"])


@router.post("/api/campaigns/test-smtp", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def test_campaign_smtp_payload(payload: CampaignSettings, current_user: dict = Depends(get_current_user)) -> dict:
    return test_campaign_smtp(payload.model_dump(), current_user["id"])


@router.get("/api/campaigns/track/{campaign_id}/{recipient_index}",
    tags=["Campaigns"],
)
def track_campaign_open(campaign_id: str, recipient_index: int) -> Response:
    return Response(
        content=b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
        media_type="image/gif",
    )


@router.put("/api/campaigns/settings", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def save_campaign_settings_payload(payload: CampaignSettings, current_user: dict = Depends(get_current_user)) -> dict:
    return save_campaign_settings(payload.model_dump(), current_user["id"])


@router.post("/api/campaigns/lists", response_model=ContactList, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Campaigns"],
)
def create_campaign_list(payload: ContactListCreateRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return create_contact_list(payload.name, current_user["id"])


@router.get(
    "/api/job-automation/workspace",
    response_model=JobAutomationWorkspaceResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Load Job Automation workspace",
    description=(
        "Returns the full recruiting workspace for the current user: active profile, "
        "multi-resume CV library, automation settings, search config, portals, ranked results, "
        "and application tracker payload."
    ),
)
def get_job_automation(current_user: dict = Depends(get_current_user)) -> dict:
    return get_job_automation_workspace(current_user["id"])


@router.put(
    "/api/job-automation/profile",
    response_model=ActionResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Save active CV profile",
    description="Persists the active/working job profile fields. Scoped to the currently active resume snapshot.",
)
def save_job_profile_payload(payload: JobProfile, current_user: dict = Depends(get_current_user)) -> dict:
    return save_job_profile(payload.model_dump(), current_user["id"])


@router.put(
    "/api/job-automation/automation",
    response_model=ActionResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Save automation settings",
    description=(
        "Persists auto-apply, matchThreshold (floor ≥65%), tailorCv, schedule, and daily caps. "
        "Auto-apply routing uses ≥65% apply / 40–64% tailor / <40% reject."
    ),
)
def save_automation_payload(payload: JobAutomationSettings, current_user: dict = Depends(get_current_user)) -> dict:
    return save_automation_settings(payload.model_dump(), current_user["id"])


@router.put(
    "/api/job-automation/search",
    response_model=ActionResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Save search configuration",
    description=(
        "Persists titles, skills, location, postedWithin ('1'=24h, '2'=48h), employment filters, "
        "and Search schedule (repeatEvery)."
    ),
)
def save_search_config_payload(payload: SearchConfigSaveRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return save_search_config(payload.model_dump(), current_user["id"])


@router.post(
    "/api/job-automation/search/run",
    response_model=SearchRunResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Run portal job search",
    description=(
        "Scrapes configured portals using the provided search payload (including postedWithin), "
        "ranks results against the active CV, and returns matched jobs. "
        "Use postedWithin='1' for 24h or '2' for 48h. "
        "Auto-apply separately forces both 24h and 48h windows."
    ),
)
def run_job_search_payload(
    payload: SearchRunRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return run_job_search(payload.model_dump(), current_user["id"])


@router.post("/api/job-automation/portals", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def add_portal_payload(payload: AddPortalRequest) -> dict:
    return add_portal(payload.name, payload.url)


@router.delete("/api/job-automation/portals", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def delete_portal_payload(payload: DeletePortalRequest) -> dict:
    try:
        return delete_portal(payload.name, payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/job-automation/portals/import", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def import_portals_payload(payload: ImportPortalsRequest) -> dict:
    return import_portals([item.model_dump() for item in payload.portals])


@router.post("/api/job-automation/carriers", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def add_carrier_payload(payload: AddCarrierRequest) -> dict:
    return add_carrier(payload.name, payload.url)


@router.delete("/api/job-automation/carriers", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def delete_carrier_payload(payload: DeleteCarrierRequest) -> dict:
    try:
        return delete_carrier(payload.name, payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/job-automation/carriers/import", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def import_carriers_payload(payload: ImportCarriersRequest) -> dict:
    return import_carriers([item.model_dump() for item in payload.carriers])


@router.post(
    "/api/job-automation/apply",
    response_model=ApplyJobsResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Apply to selected jobs (24h/48h eligible)",
    description=(
        "Creates application tracker rows and starts background portal apply workers for the given jobIds. "
        "Only jobs posted within the last 48 hours are eligible (covers 24h and 48h scrape windows). "
        "supervised=true launches portal fill workers; supervised=false tracks without UI browser opens. "
        "Current product UI uses no-browser mode for Quick Apply and Apply selected."
    ),
)
def apply_jobs_payload(
    payload: ApplyJobsRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return apply_jobs(
        payload.jobIds,
        current_user["id"],
        supervised=payload.supervised,
        use_tailored_resume=payload.useTailoredResume,
    )


@router.get(
    "/api/job-automation/applications/{application_id}",
    response_model=JobApplicationStatusResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Get application attempt status",
    description=(
        "Poll a single application attempt. attemptStatus values include queued, filling, "
        "awaiting_submit, needs_attention, applied, tailored, rejected, manual, demo, failed."
    ),
)
def get_application_status_payload(
    application_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        return get_job_application(application_id, current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/api/job-automation/applications",
    response_model=JobApplicationListResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="List recent applications",
    description="Returns recent application tracker rows for the current user (includes tailored and rejected decisions).",
)
def list_applications_payload(
    current_user: dict = Depends(get_current_user),
    limit: int = 100,
) -> dict:
    return list_recent_job_applications(current_user["id"], limit=limit)


@router.patch(
    "/api/job-automation/applications/{application_id}",
    response_model=ApplicationMutationResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Update application tracker status",
    description="Update status/stage/action for a tracked application (Interview, Rejected, Offer, etc.).",
)
def update_application_payload(
    application_id: int,
    payload: UpdateApplicationRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        return update_job_application(
            application_id,
            status=payload.status,
            stage=payload.stage,
            action=payload.action,
            notes=payload.notes,
            user_external_id=current_user["id"],
        )
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post(
    "/api/job-automation/applications/{application_id}/follow-up",
    response_model=ApplicationMutationResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Schedule application follow-up",
    description="Marks a follow-up reminder on the application and moves Applied/Failed rows into Action Needed.",
)
def follow_up_application_payload(
    application_id: int,
    payload: ApplicationFollowUpRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        return schedule_application_followup(
            application_id,
            note=payload.note,
            user_external_id=current_user["id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/api/job-automation/auto-apply",
    response_model=AutoApplyResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Scrape 24h/48h portals and route by CV match",
    description=(
        "Scrapes all configured portals for posted windows 1 day (24h) and 2 days (48h), "
        "scores each role against the active CV, then routes:\n"
        "- ≥65% → auto-apply in background\n"
        "- 40–64% → tailor CV to JD (when tailorCv is enabled)\n"
        "- <40% → reject application\n\n"
        "Optional matchThreshold may raise the apply floor above 65%, never lower it. "
        "Response includes applied/tailored/rejected counts, postedWindows, and matchPolicy."
    ),
)
def auto_apply_payload(
    payload: AutoApplyRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        result = run_auto_apply(payload.matchThreshold, current_user["id"])
        logger.info(
            "Auto apply for user %s: applied=%s scraped=%s",
            current_user["id"],
            result.get("applied", 0),
            result.get("scrapedCount", 0),
        )
        return result
    except Exception as exc:
        logger.exception("Auto apply failed for user %s", current_user["id"])
        raise HTTPException(status_code=500, detail="Auto apply failed. Check backend logs for details.") from exc


@router.post(
    "/api/job-automation/analyze",
    response_model=AnalysisResult,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Analyze CV fit for a job",
    description=(
        "Evaluates a job description (LinkedIn, Indeed, or pasted JD) against the active CV. "
        "Returns match percentage, matched/missing keywords, and role-aligned recommendations."
    ),
)
def analyze_job_payload(payload: AnalyzeJobRequest, current_user: dict = Depends(get_current_user)) -> dict:
    if not payload.jobId and not payload.jobDescription:
        raise HTTPException(status_code=400, detail="Provide jobId or jobDescription.")
    return analyze_job(
        job_id=payload.jobId,
        job_description=payload.jobDescription,
        user_external_id=current_user["id"],
    )


@router.post(
    "/api/job-automation/jobs/{job_id}/refresh-description",
    response_model=JobDescriptionRefreshResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Fetch full JD from portal website",
    description=(
        "Connects to the job's sourceUrl (Dice / LinkedIn / vendor detail page), "
        "extracts the exact job title and description, stores it on the job result, "
        "and returns the text for the CV Analyzer Job description field."
    ),
)
def refresh_job_description_payload(job_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    try:
        return refresh_job_description(job_id, current_user["id"], force=True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/api/job-automation/resume/tailor",
    response_model=TailoredResumeResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Tailor CV to a job description",
    description=(
        "Suggests specific role-aligned adjustments while preserving the base resume history. "
        "Does not rewrite employment dates or invent experience."
    ),
)
def tailor_resume_payload(payload: TailorResumeRequest, current_user: dict = Depends(get_current_user)) -> dict:
    try:
        return tailor_resume_for_job(payload.jobId, payload.jobDescription, current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/api/job-automation/autofill/preview",
    response_model=AutofillPreviewResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Preview application autofill fields",
    description=(
        "Builds a reviewable autofill map from the job profile. "
        "Repeated contact fields are ready to fill; work authorization and other sensitive answers stay held for review until approved."
    ),
)
def preview_autofill_payload(
    payload: AutofillPreviewRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        return preview_application_autofill(
            job_id=payload.jobId,
            approved_keys=payload.approvedKeys,
            user_external_id=current_user["id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/job-automation/resume/save-tailored", response_model=SavedTailoredResumeResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def save_tailored_resume_payload(payload: SaveTailoredResumeRequest, current_user: dict = Depends(get_current_user)) -> dict:
    try:
        return save_tailored_resume(payload.jobId, payload.content, current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/job-automation/resume/tailored/{job_id}", response_model=StoredTailoredResumeResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def get_tailored_resume_payload(job_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    return get_tailored_resume(job_id, current_user["id"])


@router.post("/api/job-automation/linkedin/search", dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def linkedin_job_search_payload(payload: LinkedInJobSearchRequest) -> dict:
    return search_linkedin_jobs(payload.model_dump())


@router.post("/api/job-automation/linkedin/apply", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def linkedin_apply_payload(payload: dict) -> dict:
    return apply_linkedin_job(payload.get("role", ""), payload.get("company", ""), bool(payload.get("easyApply")))


@router.post("/api/job-automation/save", response_model=SaveJobResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
)
def save_job_payload(payload: SaveJobRequest) -> dict:
    return save_job(payload.jobId)


@router.post(
    "/api/job-automation/resume/parse",
    response_model=ResumeParseResponse,
    tags=["Job Automation"],
    summary="Upload and parse resume with AI",
    description=(
        "Accepts TXT, PDF, or DOCX resume files and returns structured profile extraction, "
        "ML role-fit scoring, embedding-ready profile extraction, and optional LLM reasoning "
        "(Ollama when USE_LOCAL_LLM=true, else OpenAI). "
        "Persists the CV into the multi-resume library with an isolated profileSnapshot, "
        "activates it, and updates the working profile/search for that CV only. "
        "Falls back to deterministic parsing when no LLM provider is available."
    ),
    response_description="Parsed resume profile with ML/LLM assessments and updated multi-resume library.",
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {
                            "file": {"type": "string", "format": "binary", "description": "Resume file (.txt, .pdf, .docx)"},
                            "targetRole": {
                                "type": "string",
                                "default": "Software Engineer",
                                "description": "Target role used for match scoring.",
                            },
                            "requiredSkills": {
                                "type": "string",
                                "default": "Python, FastAPI, SQL",
                                "description": "Comma-separated required skills.",
                            },
                        },
                    },
                    "example": {
                        "targetRole": "Backend Engineer",
                        "requiredSkills": "Python,FastAPI,SQL,AWS,Docker",
                    },
                }
            },
        }
    },
)
async def parse_resume_payload(
    file: UploadFile = File(...),
    targetRole: str = Form("Software Engineer"),
    requiredSkills: str = Form("Python, FastAPI, SQL"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    required_skills = [skill.strip() for skill in requiredSkills.split(",") if skill.strip()]
    result = await parse_resume_with_ai(file=file, target_role=targetRole, required_skills=required_skills)
    file_bytes = result.pop("_fileBytes", None)
    content_type = result.pop("_contentType", None) or result.get("contentType")
    workspace = apply_parsed_resume(
        result.get("parsedProfile", {}),
        file.filename or "resume.txt",
        current_user["id"],
        assessment=result.get("mlAssessment"),
        file_bytes=file_bytes,
        content_type=content_type,
    )
    result["profile"] = workspace["profile"]
    result["search"] = workspace["search"]
    result["resumes"] = workspace.get("resumes", [])
    result["message"] = "Resume parsed, stored in your CV library, and profile/search configuration updated."
    return result


@router.get(
    "/api/job-automation/resumes",
    response_model=UserResumeListResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="List multi-resume CV library",
    description="Returns all stored CVs for the user, including isolated profileSnapshot metadata and the active flag.",
)
def list_resumes_payload(current_user: dict = Depends(get_current_user)) -> dict:
    return list_user_resumes(current_user["id"])


@router.post(
    "/api/job-automation/resumes/{resume_id}/activate",
    response_model=UserResumeActionResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Activate a CV and restore its snapshot",
    description=(
        "Marks the selected resume as Active and restores its isolated profileSnapshot into "
        "the working profile and search configuration without mixing other CVs."
    ),
)
def activate_resume_payload(resume_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    try:
        return activate_user_resume(resume_id, current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/api/job-automation/resumes/{resume_id}",
    response_model=UserResumeActionResponse,
    dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Job Automation"],
    summary="Delete a CV from the library",
    description="Removes a resume from the multi-CV library. If it was active, another CV may be activated or the profile cleared.",
)
def delete_resume_payload(resume_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    try:
        return delete_user_resume(resume_id, current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/day-report/dashboard", response_model=DayReportDashboardResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Day Report"],
)
def get_day_report() -> dict:
    return get_day_report_dashboard()


@router.post("/api/day-report/filter", response_model=DayReportDashboardResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Day Report"],
)
def filter_day_report_payload(payload: DayReportFilterRequest) -> dict:
    return filter_day_report(payload.start, payload.end, payload.recruiter)


@router.get("/api/submissions/dashboard", response_model=SubmissionDashboardResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Submissions"],
)
def get_submission_progress() -> dict:
    return get_submission_dashboard()


@router.post("/api/submissions/filter", response_model=SubmissionDashboardResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Submissions"],
)
def filter_submissions_payload(payload: SubmissionFilterRequest) -> dict:
    return filter_submissions(payload.startMonth, payload.endMonth)


@router.get("/api/meta/endpoints", response_model=EndpointCatalogResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Meta"],
)
def get_api_catalog() -> dict:
    return get_endpoint_catalog()


@router.get("/api/meta/test-data", response_model=TestDataDumpResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["Meta"],
)
def get_test_data_dump() -> dict:
    return get_test_data_payload()


@router.post("/api/meta/test-data/append", response_model=TestDataAppendResponse, dependencies=[Depends(require_roles(ROLE_SUPER_ADMIN))],
    tags=["Meta"],
)
def append_test_data_rows(payload: TestDataAppendRequest) -> dict:
    if not payload.entries:
        raise HTTPException(status_code=400, detail="entries must not be empty")
    try:
        return append_test_data_payload(payload.dataset, payload.entries)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/meta/test-data/reset", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_SUPER_ADMIN))],
    tags=["Meta"],
)
def reset_test_data_rows() -> dict:
    return reset_test_data_payload()


# ── LinkedIn Recruiter Discovery ────────────────────────────────────────────


@router.get("/api/linkedin/workspace", response_model=LinkedInWorkspaceResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def get_linkedin_workspace_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    return get_linkedin_workspace(current_user["id"])


@router.post("/api/linkedin/discover", response_model=LinkedInDiscoverResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def linkedin_discover(payload: LinkedInDiscoverRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return run_linkedin_discovery(
        payload.companies,
        payload.technologies,
        payload.seniority,
        payload.location,
        payload.connections,
        payload.resultsPerCompany,
        current_user["id"],
    )


@router.post("/api/linkedin/enrich", response_model=LinkedInEnrichResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def linkedin_enrich(payload: LinkedInEnrichRequest) -> dict:
    return enrich_linkedin_profiles(payload.urls, payload.techContext)


@router.put("/api/linkedin/recruiters/{recruiter_id}/bookmark", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def linkedin_bookmark_recruiter(recruiter_id: int, payload: LinkedInBookmarkRequest, current_user: dict = Depends(get_current_user)) -> dict:
    try:
        return set_linkedin_recruiter_bookmark(recruiter_id, payload.bookmarked, current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/linkedin/outreach", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def linkedin_outreach(payload: LinkedInOutreachRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return send_linkedin_outreach(
        payload.recruiterIds,
        payload.subject,
        payload.body,
        payload.channel,
        payload.scheduleAt,
        current_user["id"],
    )


@router.post("/api/linkedin/outreach/generate", response_model=LinkedInGenerateMessageResponse, dependencies=[Depends(require_roles(ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def linkedin_generate_message(payload: LinkedInGenerateMessageRequest) -> dict:
    return generate_linkedin_message(payload.prompt, payload.messageType, payload.tone, payload.channel)


@router.post("/api/linkedin/templates", response_model=LinkedInMessageTemplate, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def linkedin_create_template(payload: LinkedInTemplateCreateRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return create_linkedin_message_template(payload.name, payload.body, current_user["id"])


@router.put("/api/linkedin/settings", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def linkedin_save_settings(payload: LinkedInSettingsUpdateRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return save_linkedin_settings(payload.settings.model_dump(), current_user["id"])


@router.put("/api/linkedin/api-keys", response_model=ActionResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN))],
    tags=["LinkedIn"],
)
def linkedin_save_api_keys(payload: LinkedInApiKeysRequest, current_user: dict = Depends(get_current_user)) -> dict:
    return save_linkedin_api_keys(payload.model_dump(exclude_none=True), current_user["id"])
