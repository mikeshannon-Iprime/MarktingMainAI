from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
URL_PATTERN = r"^https?://.+$"
MONTH_PATTERN = r"^\d{4}-\d{2}$"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class DatabaseStatus(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    database: DatabaseStatus
    modules: List[str]


class OverviewModule(BaseModel):
    slug: str
    label: str
    description: str
    metric: str


class OverviewActivity(BaseModel):
    title: str
    detail: str


class OverviewResponse(BaseModel):
    headline: str
    modules: List[OverviewModule]
    activity: List[OverviewActivity]


class CampaignMetrics(BaseModel):
    emailsSent: int
    openRate: int
    replyRate: int
    bounceRate: int


class CampaignComposer(BaseModel):
    campaignName: str
    fromName: str
    fromEmail: str
    replyTo: str
    subject: str
    body: str
    mergeTags: List[str]
    aiPrompts: List[str]


class Contact(BaseModel):
    name: str
    email: str
    company: str
    status: str
    list: str


class ContactList(BaseModel):
    name: str
    contacts: int
    openRate: int
    replyRate: int


class CampaignItem(BaseModel):
    name: str
    sent: int
    opened: int
    replied: int
    status: str
    scheduledFor: str


class CampaignSettings(BaseModel):
    smtpHost: str
    smtpPort: int
    smtpUsername: str = ""
    smtpPassword: str = ""
    senderLimit: int
    emailDelaySeconds: int = 3
    smartWarmup: bool
    unsubscribeFooter: bool
    spamGuard: bool
    gmailSync: bool
    outlookSync: bool
    openTracking: bool
    aiSubjectAssist: bool
    honorUnsubscribes: bool = True
    bounceManagement: bool = True
    sendgridSync: bool = False
    aiProvider: str = "ollama"
    aiDefaultTone: str = "professional"
    aiPersonalization: bool = True


class CampaignWorkspaceResponse(BaseModel):
    metrics: CampaignMetrics
    composer: CampaignComposer
    contacts: List[Contact]
    lists: List[ContactList]
    campaigns: List[CampaignItem]
    templates: List[Dict[str, str]]
    settings: CampaignSettings


class CampaignTemplatePreviewRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=20000)
    fromName: str = Field(default="", max_length=120)
    fromEmail: str = Field(default="", max_length=255)
    replyTo: str = Field(default="", max_length=255)


class CampaignPreviewRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=20000)
    recipients: List[str] = Field(default_factory=list)

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, value: List[str]) -> List[str]:
        for email in value:
            if not email or "@" not in email:
                raise ValueError("All recipients must be valid email values.")
        return value


class CampaignPreviewResponse(BaseModel):
    subject: str
    body: str
    recipientCount: int
    previewHtml: str


class CampaignTestSendRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=1, max_length=20000)
    fromName: str = Field(default="", max_length=120)
    fromEmail: str = Field(default="", max_length=255)
    replyTo: str = Field(default="", max_length=255)


class ActionResponse(BaseModel):
    success: bool
    message: str


class CampaignLaunchRequest(BaseModel):
    campaignName: str = Field(min_length=3, max_length=255)
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=20000)
    recipients: List[str] = Field(min_length=1)
    scheduledFor: str = Field(min_length=5, max_length=64)
    sendNow: bool = False
    fromName: str = Field(default="", max_length=120)
    fromEmail: str = Field(default="", max_length=255)
    replyTo: str = Field(default="", max_length=255)
    openTracking: bool = True
    autoFollowup: bool = False
    sendingSpeed: str = Field(default="50", max_length=16)
    emailDelaySeconds: int = Field(default=3, ge=0, le=300)
    listName: str = Field(default="", max_length=120)

    @field_validator("recipients")
    @classmethod
    def validate_launch_recipients(cls, value: List[str]) -> List[str]:
        invalid = [email for email in value if "@" not in email]
        if invalid:
            raise ValueError("All recipients must be valid email values.")
        return value


class CampaignLaunchResponse(BaseModel):
    success: bool
    message: str
    mode: str = "demo"
    campaign: Optional[Dict[str, Any]] = None
    sentCount: int = 0
    failedCount: int = 0


class CampaignDraftRequest(BaseModel):
    campaignName: str = Field(min_length=3, max_length=255)
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=20000)
    fromName: str = Field(default="", max_length=120)
    fromEmail: str = Field(default="", max_length=255)
    replyTo: str = Field(default="", max_length=255)


class CampaignDraftResponse(BaseModel):
    success: bool
    message: str
    campaign: Optional[Dict[str, Any]] = None


class CampaignContactImportItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    company: str = Field(default="", max_length=255)
    list: str = Field(default="Imported", max_length=120)
    status: str = Field(default="Queued", max_length=32)


class CampaignContactImportRequest(BaseModel):
    contacts: List[CampaignContactImportItem] = Field(min_length=1)
    listName: str = Field(default="Imported", max_length=120)


class CampaignContactImportResponse(BaseModel):
    imported: int
    skipped: int
    contacts: List[Contact]


class ContactListCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class JobStats(BaseModel):
    appliedToday: int
    newMatches: int
    interviews: int
    avgMatchScore: int


class JobProfile(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    phone: str = Field(min_length=6, max_length=40)
    location: str = Field(min_length=2, max_length=120)
    linkedin: str = Field(pattern=URL_PATTERN, max_length=255)
    experience: str = Field(min_length=2, max_length=60)
    employmentType: str = Field(min_length=2, max_length=80)
    rate: str = Field(min_length=1, max_length=60)
    visa: str = Field(min_length=1, max_length=40)
    workMode: str = Field(min_length=2, max_length=60)
    jobTitles: List[str] = Field(default_factory=list)
    resumeFileName: Optional[str] = None
    resumeSummary: Optional[str] = None
    resumeSkills: List[str] = Field(default_factory=list)


class JobAutomationSettings(BaseModel):
    autoApply: bool = Field(description="When true, discovery/auto-apply may run on schedule or toggle.")
    matchThreshold: int = Field(
        description=(
            "Minimum CV↔JD match for auto-apply. Effective floor is 65%; "
            "values above 65 raise the apply band only."
        ),
        ge=30,
        le=100,
    )
    maxApplications: int = Field(description="Daily cap for auto-apply + tailor + reject decisions.", ge=1, le=100)
    alerts: bool = Field(description="Send completion alerts when auto-apply finishes.")
    tailorCv: bool = Field(
        description="When true, jobs scoring 40–64% get a tailored CV instead of being skipped.",
    )
    scheduleEnabled: bool = Field(description="Enable scheduled discovery / auto-apply runs.")
    scheduleLabel: str = Field(description="Human-readable schedule label shown in the UI.")
    scheduleTimezone: str = Field(default="America/New_York", description="IANA timezone for scheduled runs.")
    scheduleTime: str = Field(default="09:00", description="Local clock time for scheduled runs (HH:MM).")


class SearchConfig(BaseModel):
    titles: List[str] = Field(description="Target job titles used for portal search.")
    requiredSkills: List[str] = Field(description="Must-have skills for ranking and filtering.")
    optionalSkills: List[str] = Field(description="Nice-to-have skills that boost ranking.")
    location: str = Field(description="Primary search location.")
    radius: str = Field(description="Search radius label, e.g. '50 miles' or 'Nationwide'.")
    filters: List[str] = Field(description="Advanced free-form filter tokens.")
    excludeKeywords: List[str] = Field(default_factory=list, description="Keywords that exclude a posting.")
    employmentType: str = Field(default="Both", description="Employment type filter (Contract, Full Time, Both, …).")
    minMatchScore: int = Field(default=70, description="Minimum match % retained after search ranking.")
    postedWithin: str = Field(
        default="7",
        description=(
            "Posted-age window in days as a string. "
            "'1' = last 24 hours, '2' = last 48 hours, '3'/'7'/'14'/'30' = calendar days. "
            "Auto-apply always scrapes windows ['1','2'] regardless of this saved value."
        ),
        examples=["1", "2", "7"],
    )
    experienceLevel: str = Field(default="Any", description="Experience filter label.")
    rateMin: str = Field(default="", description="Minimum rate/salary filter (numeric string).")
    rateMax: str = Field(default="", description="Maximum rate/salary filter (numeric string).")
    repeatEvery: str = Field(default="Once daily", description="Search schedule cadence label (Search schedule).")


class PortalItem(BaseModel):
    name: str = Field(description="Portal display name (Dice, Monster, CareerBuilder, …).")
    url: str = Field(description="Portal root URL.")
    status: str = Field(description="Connection status, typically Active or Paused.")


class CarrierItem(BaseModel):
    name: str
    url: str
    status: str = "Monitoring"


class JobResult(BaseModel):
    id: int = Field(description="Persisted job result id used by apply/analyze/tailor.")
    role: str
    company: str
    location: str
    type: str = Field(description="Employment type chip from the posting.")
    posted: str = Field(
        description="Posted age label. Numeric days (e.g. '1') or hour labels (e.g. '5h ago').",
    )
    rate: Optional[str] = None
    match: int = Field(description="CV↔JD match score 0–100.")
    hot: bool = False
    skills: List[str] = Field(default_factory=list)
    portalName: Optional[str] = None
    portalUrl: Optional[str] = None
    sourceUrl: Optional[str] = Field(default=None, description="Live posting URL when available.")
    description: Optional[str] = Field(default=None, description="Job description text used for matching/tailoring.")
    matchInsight: Optional[str] = None
    matchSource: Optional[str] = None


class AnalysisResult(BaseModel):
    selectedJobId: Optional[int] = None
    score: int
    summary: str
    hits: List[str]
    misses: List[str]
    suggestions: List[str]
    experienceMatch: Optional[str] = None
    titleMatch: Optional[str] = None
    jobDescription: Optional[str] = None
    skillGaps: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    tailoredScore: Optional[int] = None
    matchSource: Optional[str] = Field(default=None, description="Scoring source: embeddings, heuristic+ml, etc.")
    platform: Optional[str] = Field(default=None, description="Detected board, e.g. LinkedIn or Indeed.")
    sourceUrl: Optional[str] = Field(default=None, description="Live posting URL when available.")
    missingKeywords: List[str] = Field(
        default_factory=list,
        description="Alias of misses for UI highlighting of missing keywords.",
    )


class TailoredResumeResponse(BaseModel):
    success: bool
    message: str
    jobId: int
    content: str
    tailoredScore: Optional[int] = None
    analysis: Optional[AnalysisResult] = None
    adjustments: List[str] = Field(
        default_factory=list,
        description="Surgical role-aligned adjustments; base employment history is preserved.",
    )
    jdPointers: List[str] = Field(
        default_factory=list,
        description="Experience bullets derived from the job description requirements.",
    )
    basePreserved: bool = Field(
        default=True,
        description="True when tailor kept the existing resume body and only added adjustments.",
    )


class SavedTailoredResumeResponse(BaseModel):
    success: bool
    message: str
    jobId: int


class StoredTailoredResumeResponse(BaseModel):
    jobId: int
    content: str
    found: bool


class AutofillField(BaseModel):
    key: str
    label: str
    value: str
    sensitive: bool = False
    requiresReview: bool = False
    status: str = Field(description="approved | needs_review")
    approved: bool = False


class AutofillPreviewRequest(BaseModel):
    jobId: Optional[int] = Field(default=None, gt=0)
    approvedKeys: List[str] = Field(
        default_factory=list,
        description="Sensitive field keys the user explicitly approved for autofill.",
    )


class AutofillPreviewResponse(BaseModel):
    success: bool
    message: str
    jobId: Optional[int] = None
    platform: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    fields: List[AutofillField] = Field(default_factory=list)
    autoFillCount: int = 0
    reviewCount: int = 0

class LinkedInJob(BaseModel):
    role: str
    company: str
    location: str
    type: Optional[str] = None
    posted: Optional[str] = None
    match: Optional[int] = None
    easyApply: bool
    applicants: int
    insight: str
    linkedinUrl: Optional[str] = None
    experienceLevel: Optional[str] = None
    datePosted: Optional[str] = None


class ApplicationRecord(BaseModel):
    id: Optional[int] = None
    jobResultId: Optional[int] = None
    role: str
    company: str
    status: str
    stage: str
    updated: str
    action: str
    portal: str = "Direct"
    date: str = ""
    match: Optional[int] = None
    postingUrl: str = ""
    attemptStatus: Optional[str] = None
    attemptDetail: Optional[str] = None
    confirmationUrl: Optional[str] = None


class ApplicationStats(BaseModel):
    applied: int
    interviews: int
    actionNeeded: int
    conversion: int
    responseRate: int = 0
    avgMatchScore: int = 0
    avgResponseTime: str = "—"
    bestPlatform: str = "—"
    underReview: int = 0
    totalTracked: int = 0


class ApplicationsPayload(BaseModel):
    all: List[ApplicationRecord]
    interviews: List[ApplicationRecord]
    actionNeeded: List[ApplicationRecord]
    stats: ApplicationStats


class UpdateApplicationRequest(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Tracker status: Applying, Applied, Action Needed, Interview, Offer, Tailoring, Rejected, Failed.",
    )
    stage: Optional[str] = Field(default=None, max_length=255)
    action: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, description="Optional note appended to attempt detail.")


class ApplicationFollowUpRequest(BaseModel):
    note: Optional[str] = Field(default=None, description="Optional follow-up note.")


class UserResumeItem(BaseModel):
    id: int = Field(description="CV library record id.")
    fileName: str = Field(description="Original uploaded file name.")
    summary: str = Field(default="", description="Parsed resume summary for this CV only.")
    skills: List[str] = Field(default_factory=list, description="Skills isolated to this CV snapshot.")
    jobTitles: List[str] = Field(default_factory=list, description="Job titles isolated to this CV snapshot.")
    mlScore: Optional[int] = Field(default=None, description="Stored ML role-fit score from last parse.")
    matchedSkills: List[str] = Field(default_factory=list)
    missingSkills: List[str] = Field(default_factory=list)
    isActive: bool = Field(default=False, description="True when this CV is the active working profile.")
    uploadedAt: Optional[str] = None
    profileName: Optional[str] = None
    experience: Optional[str] = None
    profileSnapshot: Optional[dict] = Field(
        default=None,
        description=(
            "Isolated profile + search snapshot for this CV. "
            "Activating the resume restores this snapshot into the working profile/search "
            "without mixing data from other CVs."
        ),
    )


class JobAutomationWorkspaceResponse(BaseModel):
    stats: JobStats
    profile: JobProfile
    automation: JobAutomationSettings
    search: SearchConfig
    resumes: List[UserResumeItem] = Field(default_factory=list, description="Multi-resume CV library for the current user.")
    portals: List[PortalItem]
    carriers: List[CarrierItem]
    results: List[JobResult]
    savedJobs: List[int] = Field(default_factory=list)
    analysis: AnalysisResult
    linkedin: List[LinkedInJob]
    applications: ApplicationsPayload


class SearchRunRequest(BaseModel):
    titles: List[str] = Field(min_length=1, description="Job titles to search across configured portals.")
    requiredSkills: List[str] = Field(default_factory=list)
    optionalSkills: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    radius: Optional[str] = None
    filters: List[str] = Field(default_factory=list)
    excludeKeywords: List[str] = Field(default_factory=list)
    employmentType: str = Field(default="Both", description="Employment type filter applied to results.")
    minMatchScore: int = Field(default=70, ge=30, le=100)
    postedWithin: str = Field(
        default="7",
        description="Posted-age window in days ('1'=24h, '2'=48h, '7'=7 days, …).",
        examples=["1", "2", "7"],
    )
    experienceLevel: str = "Any"
    rateMin: str = ""
    rateMax: str = ""
    repeatEvery: str = Field(default="Once daily", description="Search schedule cadence (Search schedule).")

    @field_validator("titles")
    @classmethod
    def validate_titles(cls, value: List[str]) -> List[str]:
        clean = [item.strip() for item in value if item and item.strip()]
        if not clean:
            raise ValueError("At least one non-empty title is required.")
        return clean


class SearchConfigSaveRequest(BaseModel):
    titles: List[str] = Field(default_factory=list)
    requiredSkills: List[str] = Field(default_factory=list)
    optionalSkills: List[str] = Field(default_factory=list)
    location: str = ""
    radius: str = "50 miles"
    filters: List[str] = Field(default_factory=list)
    excludeKeywords: List[str] = Field(default_factory=list)
    employmentType: str = "Both Contract & Full Time"
    minMatchScore: int = Field(default=70, ge=30, le=100)
    postedWithin: str = Field(
        default="7",
        description="Posted-age window in days ('1'=24h, '2'=48h, '7'=7 days, …).",
        examples=["1", "2", "7"],
    )
    experienceLevel: str = "Any"
    rateMin: str = ""
    rateMax: str = ""
    repeatEvery: str = Field(default="Once daily", description="Search schedule cadence (Search schedule).")


class AnalyzeJobRequest(BaseModel):
    jobId: Optional[int] = Field(default=None, description="Existing job result id to analyze.")
    jobDescription: Optional[str] = Field(
        default=None,
        min_length=20,
        description="Raw job description text when analyzing without a saved job id.",
    )


class LinkedInJobSearchRequest(BaseModel):
    query: str = ""
    experienceLevel: str = "all"
    employmentType: str = "all"
    company: str = ""
    under10Applicants: bool = False
    datePosted: str = "all"
    easyApplyOnly: bool = False


class DeletePortalRequest(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)


class DeleteCarrierRequest(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)


class TailorResumeRequest(BaseModel):
    jobId: int = Field(gt=0)
    jobDescription: Optional[str] = None


class JobDescriptionRefreshResponse(BaseModel):
    success: bool
    jobId: int
    role: Optional[str] = None
    company: Optional[str] = None
    sourceUrl: Optional[str] = None
    description: str = ""
    descriptionQuality: str = Field(
        default="missing",
        description="full | summary | missing — quality of the returned JD text.",
    )
    fetchedFromPortal: bool = False
    message: str = ""


class SaveTailoredResumeRequest(BaseModel):
    jobId: int = Field(gt=0)
    content: str = Field(min_length=20)


class AutoApplyRequest(BaseModel):
    matchThreshold: Optional[int] = Field(
        default=None,
        ge=30,
        le=100,
        description=(
            "Optional apply-floor override. Effective minimum is always 65%. "
            "Values above 65 raise the auto-apply band; mid-band (40–64%) still tailor; "
            "below 40% still reject."
        ),
        examples=[65, 70, 80],
    )


class MatchingPipelineMeta(BaseModel):
    steps: List[str] = Field(default_factory=list, description="Ordered matching pipeline steps executed.")
    llmUsed: bool = Field(default=False, description="True when LLM enrichment was used.")
    embeddingsUsed: bool = Field(default=False, description="True when embedding similarity was used.")
    embeddingModel: Optional[str] = Field(default=None, description="Embedding model id when used.")
    llmProvider: Optional[str] = Field(default=None, description="LLM provider when used.")
    matchSource: str = Field(default="none", description="Primary scoring source label.")
    message: str = Field(default="", description="Human-readable pipeline summary.")


class MatchPolicyMeta(BaseModel):
    applyMin: int = Field(description="Minimum match % required for auto-apply (default 65).")
    tailorMin: int = Field(description="Minimum match % for CV tailor band (default 40).")
    rejectBelow: int = Field(description="Scores strictly below this value are rejected (default 40).")


class AutoApplyResponse(BaseModel):
    success: bool
    message: str = Field(description="Summary including scrape windows and apply/tailor/reject counts.")
    results: List[JobResult] = Field(default_factory=list, description="Ranked jobs considered during this run.")
    applied: int = Field(default=0, description="Jobs routed to apply (≥ applyMin).")
    tailored: int = Field(default=0, description="Jobs routed to CV tailor (40–applyMin-1%).")
    rejected: int = Field(default=0, description="Jobs rejected (< tailorMin).")
    jobIds: List[int] = Field(default_factory=list, description="Job result ids that entered apply.")
    tailoredApplications: List[dict] = Field(
        default_factory=list,
        description="Application tracker rows created for tailored (mid-band) jobs.",
    )
    tailoredJobIds: List[int] = Field(
        default_factory=list,
        description="Job result ids that received a saved tailored CV during mid-band routing.",
    )
    rejectedApplications: List[dict] = Field(
        default_factory=list,
        description="Application tracker rows created for rejected jobs.",
    )
    scrapedCount: int = Field(default=0, description="New postings scraped this run.")
    portalsScraped: int = Field(default=0, description="Configured portals included in the scrape.")
    postedWindows: List[str] = Field(
        default_factory=list,
        description="Posted windows scraped for this run. Auto-apply uses ['1','2'] (24h + 48h).",
        examples=[["1", "2"]],
    )
    matchPolicy: Optional[MatchPolicyMeta] = Field(
        default=None,
        description="Effective match routing policy used for this run.",
    )
    matchingPipeline: Optional[MatchingPipelineMeta] = None


class SearchRunResponse(BaseModel):
    success: bool = True
    message: str = Field(default="", description="Human-readable search summary.")
    results: List[JobResult] = Field(default_factory=list, description="Ranked/filtered job results.")
    scrapedCount: int = Field(default=0, description="New postings scraped during this search.")
    portalsScraped: int = Field(default=0, description="Configured portals included in the scrape.")
    matchingPipeline: Optional[MatchingPipelineMeta] = None


class ApplyJobsRequest(BaseModel):
    jobIds: List[int] = Field(
        min_length=1,
        description="Job result ids to apply. Only posts within the last 48 hours are eligible.",
        examples=[[1, 2]],
    )
    supervised: bool = Field(
        default=True,
        description=(
            "true = background portal apply worker (fill/submit automation). "
            "false = track applications without returning browser open URLs for the UI. "
            "Current product policy keeps both Quick Apply and Apply selected in no-browser mode."
        ),
    )
    useTailoredResume: bool = Field(
        default=True,
        description=(
            "When true (default), portal apply prefers a saved tailored CV for each job when available. "
            "Used by Results 'Apply with Tailored CV' after Analyzer / mid-band routing updates the resume."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"jobIds": [101], "supervised": True},
                {"jobIds": [101, 102], "supervised": False},
            ]
        }
    }


class ApplyJobsResponse(BaseModel):
    success: bool
    message: str
    applied: int = Field(default=0, description="Number of application rows created / started.")
    applications: List[dict] = Field(default_factory=list, description="Created application tracker rows.")
    openUrls: List[str] = Field(
        default_factory=list,
        description=(
            "Portal URLs that the client may open. Current UI policy does not open these; "
            "supervised background workers handle portal interaction instead."
        ),
    )
    supervised: bool = Field(
        default=False,
        description="Echo of whether supervised portal apply workers were started.",
    )
    tailoredJobIds: List[int] = Field(
        default_factory=list,
        description="Job ids where a saved tailored CV was used for this apply.",
    )


class JobApplicationStatusResponse(BaseModel):
    id: int
    jobResultId: Optional[int] = None
    role: str
    company: str
    status: str = Field(description="Tracker status (Applying, Applied, Tailoring, Rejected, Failed, …).")
    stage: str
    updated: str
    action: str
    portal: Optional[str] = None
    date: Optional[str] = None
    match: Optional[int] = Field(default=None, description="CV↔JD match at decision time when available.")
    postingUrl: Optional[str] = None
    attemptStatus: str = Field(
        default="manual",
        description=(
            "Machine status: queued, filling, awaiting_submit, needs_attention, applied, "
            "manual, demo, tailored, rejected, failed."
        ),
    )
    attemptDetail: str = Field(default="", description="Human-readable progress / decision detail.")
    confirmationUrl: Optional[str] = None


class JobApplicationListResponse(BaseModel):
    applications: List[JobApplicationStatusResponse] = Field(default_factory=list)
    tracker: Optional[ApplicationsPayload] = Field(
        default=None,
        description="Optional partitioned tracker payload with stats for full Tracker refresh.",
    )


class ApplicationMutationResponse(BaseModel):
    success: bool
    message: str
    application: JobApplicationStatusResponse


class SaveJobRequest(BaseModel):
    jobId: int = Field(gt=0)


class SaveJobResponse(BaseModel):
    success: bool
    message: str
    saved: bool


class ResumeParsedProfile(BaseModel):
    fullName: Optional[str] = Field(default=None, description="Candidate full name extracted from resume text.")
    email: Optional[str] = Field(default=None, description="Primary email address detected in the resume.")
    phone: Optional[str] = Field(default=None, description="Primary phone number detected in the resume.")
    location: Optional[str] = Field(default=None, description="Detected candidate location (city/state/country when present).")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL detected in the resume.")
    skills: List[str] = Field(default_factory=list, description="Normalized skills identified from resume content.")
    jobTitles: List[str] = Field(default_factory=list, description="Job titles inferred from resume content.")
    yearsExperience: Optional[float] = Field(default=None, description="Estimated years of experience inferred from resume text.")
    summary: str = Field(default="", description="Short text summary extracted from the resume body.")


class ResumeMlAssessment(BaseModel):
    modelType: str = Field(description="Scoring strategy used, for example sklearn_tfidf_cosine or keyword_overlap.")
    targetRole: str = Field(description="Role used as the target for match analysis.")
    matchScore: int = Field(description="Role-fit score from 0 to 100.")
    matchedSkills: List[str] = Field(default_factory=list, description="Required skills that were found in the resume.")
    missingSkills: List[str] = Field(default_factory=list, description="Required skills not found in the resume.")


class ResumeLlmAssessment(BaseModel):
    usedLangChain: bool = Field(description="True when LangChain pipeline was used for LLM analysis.")
    provider: str = Field(description="LLM provider used for analysis (or fallback).")
    model: str = Field(description="Model identifier used for LLM analysis.")
    status: str = Field(description="Execution status, such as ok or fallback.")
    insights: str = Field(description="Natural-language insights generated from resume analysis.")


class ResumeAgentTrace(BaseModel):
    used: bool = Field(description="True when a multi-step AI agent flow was used.")
    mode: str = Field(description="Agent mode, for example langchain-openai or fallback.")
    steps: List[str] = Field(default_factory=list, description="Trace of major processing steps executed during parsing.")


class UserResumeListResponse(BaseModel):
    resumes: List[UserResumeItem] = Field(default_factory=list)


class UserResumeActionResponse(BaseModel):
    success: bool
    message: str
    resumes: List[UserResumeItem] = Field(default_factory=list)
    profile: Optional[JobProfile] = None
    search: Optional[SearchConfig] = None


class ResumeParseResponse(BaseModel):
    filename: str = Field(description="Original uploaded file name.")
    contentType: str = Field(description="MIME type detected from uploaded file.")
    sizeBytes: int = Field(description="Uploaded file size in bytes.")
    extractedTextPreview: str = Field(description="Short preview of extracted resume text for quick inspection.")
    parsedProfile: ResumeParsedProfile = Field(description="Structured profile extracted from the resume.")
    mlAssessment: ResumeMlAssessment = Field(description="ML-based role-fit and skill match assessment.")
    llmAssessment: ResumeLlmAssessment = Field(description="LLM assessment output, or fallback details when disabled.")
    agentTrace: ResumeAgentTrace = Field(description="Execution trace for the parsing pipeline.")
    profile: Optional[JobProfile] = Field(default=None, description="Updated job profile after persisting parse results.")
    search: Optional[SearchConfig] = Field(default=None, description="Updated search config after persisting parse results.")
    resumes: List[UserResumeItem] = Field(default_factory=list, description="All CVs stored for this user after the upload.")
    message: Optional[str] = Field(default=None, description="Human-readable status message.")


class AddPortalRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    url: str = Field(pattern=URL_PATTERN, max_length=512)


class AddCarrierRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    url: str = Field(pattern=URL_PATTERN, max_length=512)


class ImportPortalsRequest(BaseModel):
    portals: List[AddPortalRequest] = Field(min_length=1)


class ImportCarriersRequest(BaseModel):
    carriers: List[AddCarrierRequest] = Field(min_length=1)


class DayReportRow(BaseModel):
    date: str
    recruiter: str
    technology: str
    linkedin: Optional[int] = None
    calls: Optional[int] = None
    sourced: Optional[int] = None
    marketing: Optional[int] = None
    notes: str


class DayReportDashboardResponse(BaseModel):
    range: Dict[str, str]
    bounds: Optional[Dict[str, str]] = None
    defaultRange: Optional[Dict[str, str]] = None
    recruiters: List[str]
    totals: Dict[str, int]
    rows: List[DayReportRow]


class DayReportFilterRequest(BaseModel):
    start: Optional[str] = Field(default=None, pattern=DATE_PATTERN)
    end: Optional[str] = Field(default=None, pattern=DATE_PATTERN)
    recruiter: Optional[str] = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "DayReportFilterRequest":
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be less than or equal to end")
        return self


class SubmissionMonth(BaseModel):
    month: str
    submissions: int
    mom: Optional[float] = None
    yoy: Optional[float] = None


class SubmissionDashboardResponse(BaseModel):
    range: Dict[str, str]
    summary: Optional[Dict[str, int]] = None
    months: List[SubmissionMonth]


class SubmissionFilterRequest(BaseModel):
    startMonth: Optional[str] = Field(default=None, pattern=MONTH_PATTERN)
    endMonth: Optional[str] = Field(default=None, pattern=MONTH_PATTERN)

    @model_validator(mode="after")
    def validate_month_range(self) -> "SubmissionFilterRequest":
        if self.startMonth and self.endMonth and self.startMonth > self.endMonth:
            raise ValueError("startMonth must be less than or equal to endMonth")
        return self


class EndpointCatalogItem(BaseModel):
    method: str
    path: str
    summary: str
    requestExample: Optional[dict] = None
    responseExample: dict


class EndpointCatalogResponse(BaseModel):
    items: List[EndpointCatalogItem]


class TestDataDumpResponse(BaseModel):
    dataset: Dict[str, Any]
    counts: Dict[str, int]
    appendableDatasets: List[str]


class TestDataAppendRequest(BaseModel):
    dataset: str = Field(min_length=2, max_length=120)
    entries: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("entries")
    @classmethod
    def validate_entries(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not value:
            raise ValueError("entries must not be empty")
        return value


class TestDataAppendResponse(ActionResponse):
    dataset: str
    totalRecords: int


class AuthUser(BaseModel):
    id: str
    name: str
    email: str
    role: str


class AuthResponse(BaseModel):
    token: str
    user: AuthUser


class LoginRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    role: str = "user"


class AuthDemoUser(BaseModel):
    name: str
    email: str
    role: str


class AuthOptionsResponse(BaseModel):
    roles: List[str]
    demoUsers: List[AuthDemoUser]


# ── LinkedIn Recruiter Discovery ────────────────────────────────────────────


class LinkedInStats(BaseModel):
    recruitersFound: int
    contacted: int
    replied: int
    followupsDue: int


class RecruiterProfile(BaseModel):
    id: int
    name: str
    title: str
    company: str
    location: str
    techs: List[str]
    conn: str
    avatar: str
    match: int
    source: str
    email: str
    note: str
    status: str
    bookmarked: bool = False


class OutreachSequenceStep(BaseModel):
    label: str
    status: str
    date: str


class OutreachSequence(BaseModel):
    id: int
    name: str
    steps: List[OutreachSequenceStep]


class LinkedInFollowup(BaseModel):
    name: str
    company: str
    due: str
    type: str


class LinkedInMessageTemplate(BaseModel):
    id: Optional[int] = None
    name: str
    body: str


class LinkedInApiSource(BaseModel):
    id: str
    name: str
    shortCode: str
    description: str
    status: str
    color: str


class LinkedInApiUsageItem(BaseModel):
    label: str
    used: int
    limit: Optional[int] = None


class LinkedInSettings(BaseModel):
    autoRunDaily: bool
    autoEnrich: bool
    skipContacted: bool
    autoFollowup: bool
    aiPersonalize: bool
    maxPerDay: int
    delaySeconds: int
    accountEmail: str
    dailyConnections: int
    dailyInmails: int
    isPremium: bool
    respectDnc: bool
    honorUnsubscribes: bool
    usePermittedSources: bool


class LinkedInWorkspaceResponse(BaseModel):
    stats: LinkedInStats
    recruiters: List[RecruiterProfile]
    sequences: List[OutreachSequence]
    followups: List[LinkedInFollowup]
    templates: List[LinkedInMessageTemplate]
    apiSources: List[LinkedInApiSource]
    apiUsage: List[LinkedInApiUsageItem]
    settings: LinkedInSettings
    companies: List[str]
    technologies: List[str]
    apiConnected: bool
    pasteProfilesEnabled: bool
    outreachEnabled: bool


class LinkedInDiscoverRequest(BaseModel):
    companies: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    seniority: str = "Any"
    location: str = "United States"
    connections: str = "1st & 2nd degree"
    resultsPerCompany: int = Field(default=20, ge=5, le=100)


class LinkedInDiscoverResponse(BaseModel):
    recruiters: List[RecruiterProfile]
    totalFound: int
    message: str


class LinkedInEnrichRequest(BaseModel):
    urls: List[str] = Field(min_length=1)
    techContext: str = ""


class LinkedInEnrichResponse(BaseModel):
    profiles: List[RecruiterProfile]
    enriched: int
    message: str


class LinkedInOutreachRequest(BaseModel):
    recruiterIds: List[int] = Field(min_length=1)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=5000)
    channel: str = "LinkedIn Message"
    scheduleAt: Optional[str] = None

    @field_validator("scheduleAt")
    @classmethod
    def validate_schedule_at(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            scheduled = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("scheduleAt must be a valid ISO-8601 datetime") from exc
        if scheduled.tzinfo is None:
            raise ValueError("scheduleAt must include a timezone")
        if scheduled.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise ValueError("scheduleAt must be in the future")
        return value


class LinkedInBookmarkRequest(BaseModel):
    bookmarked: bool


class LinkedInTemplateCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    body: str = Field(min_length=1, max_length=5000)


class LinkedInGenerateMessageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    messageType: str = "connect"
    tone: str = "Professional"
    channel: str = "LinkedIn Message"


class LinkedInGenerateMessageResponse(BaseModel):
    subject: str
    body: str
    messageType: str


class LinkedInSettingsUpdateRequest(BaseModel):
    settings: LinkedInSettings


class LinkedInApiKeysRequest(BaseModel):
    apollo: Optional[str] = None
    hunter: Optional[str] = None
    rocketreach: Optional[str] = None
    lusha: Optional[str] = None


# ── User Profile Management ────────────────────────────────────────────


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    role: str
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    bio: Optional[str] = None
    createdAt: str
    lastLogin: Optional[str] = None


class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)


class UserProfileResponse(BaseModel):
    user: UserProfile


class ChangePasswordRequest(BaseModel):
    currentPassword: str = Field(min_length=1)
    newPassword: str = Field(min_length=6)
    confirmPassword: str = Field(min_length=6)


class NotificationPreferences(BaseModel):
    emailNotifications: bool = True
    campaignAlerts: bool = True
    jobAlerts: bool = True
    dailyReport: bool = False
    weeklyDigest: bool = True
    smsNotifications: bool = False
    smsPhone: str = ""


class NotificationSetupResponse(BaseModel):
    emailConfigured: bool
    smsConfigured: bool
    emailProvider: str
    smsProvider: str
    demoMode: bool
    notificationFromName: str
    notificationFromEmail: str
    twilioFromNumber: str = ""


class NotificationTestEmailRequest(BaseModel):
    email: str = Field(default="", max_length=255)


class NotificationTestSmsRequest(BaseModel):
    phone: str = Field(default="", max_length=40)


class NotificationDeliveryItem(BaseModel):
    id: str
    channel: str
    eventType: str
    recipient: str
    subject: Optional[str] = None
    status: str
    providerMessageId: Optional[str] = None
    errorMessage: Optional[str] = None
    createdAt: Optional[str] = None


class NotificationHistoryResponse(BaseModel):
    items: List[NotificationDeliveryItem]


class UserSettingsResponse(BaseModel):
    notifications: NotificationPreferences
    language: str
    dateFormat: str
    theme: str
