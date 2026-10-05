# Functional Test Cases — Legacy HTML Prototypes

**Project:** MarketingMind AI / JobSync Pro  
**Document version:** 1.4  
**Date:** 2026-07-19  
**Scope:** Manual functional tests for standalone HTML prototypes in `backupfolder/`, plus **automated** production test suites.

**Related docs:** [`usermanual.md`](../usermanual.md) · [`usermanual.mfd`](../usermanual.mfd) · [`docs/TESTING_GUIDE.md`](../docs/TESTING_GUIDE.md)

## Automated test implementation (production-ready)

| Layer | Location | Run command |
|-------|----------|-------------|
| Backend API (pytest) | `backend/tests/test_functional_*.py` | `cd backend && .venv\Scripts\python.exe -m pytest` |
| Backend unit | `backend/tests/test_reporting_helpers.py` | same |
| Frontend validators | `frontend/src/utils/validators.functional.test.js` | `cd frontend && npm test` |
| Frontend reporting | `frontend/src/utils/reportingHelpers.functional.test.js` | same |

Install test dependencies once:

```bash
cd backend && .venv\Scripts\pip.exe install -r requirements-dev.txt
cd frontend && npm install
```

Automated tests map to manual TC IDs (e.g. `SP-FLT-04` → `validators.functional.test.js`, `JA-*` → `test_functional_job_automation.py`).

**Current suite (v1.4):** 62 backend + 21 frontend = **83 automated tests**, all passing.

| Backend module | Tests | Manual TC coverage |
|----------------|-------|-------------------|
| `test_functional_auth.py` | Auth login/me | AU-* |
| `test_functional_job_automation.py` | Profile, search config, search run (user), Quick apply (user), portals, auto-apply, multi-CV library | JA-*, JA-SCH-10, JA-RES-13, JA-CV-* |
| `test_functional_campaigns.py` | Workspace, preview, drafts, contacts | CM-* |
| `test_functional_day_report.py` | Dashboard KPIs | DR-* |
| `test_functional_submissions.py` | Submission dashboard | SP-* |
| `test_functional_linkedin.py` | Discover, enrich, outreach | LI-* |
| `test_functional_notifications.py` | Email/SMS setup, preferences, history | NT-* |
| `test_reporting_helpers.py` | MoM/YoY helpers | SP-FLT-* |

| # | File | Type |
|---|------|------|
| 1 | `job_automation_platform.html` | Full job automation UI prototype |
| 2 | `campaigns_tab_mass_email.html` | Mass email / campaign studio prototype |
| 3 | `day_to_day_report_dashboard.html` | Recruiter day-to-day KPI dashboard |
| 4 | `linkedin_recruiter_discovery_panel.html` | LinkedIn recruiter discovery & outreach |
| 5 | `submission_progress_dashboard_mom_yoy_calendar.html` | **Reference spec** — implemented in app as `SubmissionProgressPage.jsx` (HTML file not in repo; tests below map to `/submissions` + `frontend/public/legacy/submissions.html` redirect) |

**How to run HTML tests:** Open each `.html` file in Chrome/Edge (file:// or static server). Use DevTools console only if a step requires it.

**Test case columns:**
- **Input** — user actions, field values, files
- **Expected output** — visible UI state, counters, toasts, DOM changes

---

## 1. Job Automation Platform (`job_automation_platform.html`)

### 1.1 Navigation & layout

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-NAV-01 | Default panel | Page loaded | None | Open file | **Profile** tab active; `#panel-profile` visible; topbar shows "JobSync Pro", LIVE badge, "Candidate Profile" |
| JA-NAV-02 | Switch to Job Search | Page loaded | Click **Job Search** nav tab | `switchPanel('search')` | `#panel-search` active; Profile panel hidden; nav tab gets `.active` |
| JA-NAV-03 | Switch to Portals | Page loaded | Click **Portals** | — | `#panel-portals` visible; 4 default portals listed (Dice, Indeed, CareerBuilder, Monster) |
| JA-NAV-04 | Switch to Results | Page loaded | Click **Results** | — | `#panel-results` visible; `#resultsCount` shows **18** |
| JA-NAV-05 | Switch to CV Analyzer | Page loaded | Click **CV Analyzer** | — | `#panel-analyzer` visible; placeholder or analysis area shown |
| JA-NAV-06 | Switch to LinkedIn | Page loaded | Click **LinkedIn** | — | `#panel-linkedin` visible; `#liCount` = **9** |
| JA-NAV-07 | Switch to Tracker | Page loaded | Click **Tracker** | — | `#panel-tracker` visible; `#trackerCount` = **4** |

### 1.2 Profile panel

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-PRF-01 | Save profile — valid | On Profile tab | `pName` = `John Smith` | Click **Save Profile** | Toast: `Profile saved for John Smith!` (class `success`) |
| JA-PRF-02 | Save profile — empty name | On Profile tab | `pName` = empty | Click **Save Profile** | Toast: `Profile saved!` |
| JA-PRF-03 | Personal fields | On Profile tab | Email `john@email.com`, Phone `+1 (555) 123-4567`, Location `Dallas, TX`, LinkedIn URL | Enter values | Fields retain values; no auto-save until Save |
| JA-PRF-04 | Work preferences | On Profile tab | Experience `5-8 Years`, Type `Both Contract & Full Time`, Rate `$85/hr`, Visa `H1B`, Mode `Hybrid` | Select options | Dropdowns show selected values |
| JA-PRF-05 | Stats row initial | Page load | None | Observe stats | Applied Today = **0**; New Matches = **18**; Interviews = **3**; Avg Match = **87%** |
| JA-PRF-06 | Auto-apply toggle | On Profile tab | Click `#toggleAuto` | `toggleIt('toggleAuto')` | Toggle loses `.on` class (off); click again restores `.on` |
| JA-PRF-07 | Match threshold slider | On Profile tab | Drag `#matchThreshold` to `85` | `oninput` | `#matchVal` text = **85%** |
| JA-PRF-08 | Max applications | On Profile tab | `maxApps` = `50` | Enter number | Field value = 50 |
| JA-PRF-09 | Configure Search CTA | On Profile tab | Click **Configure Search →** | — | Switches to Search panel |

### 1.3 Resume upload

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-RES-01 | Upload PDF | Profile tab | File: `resume.pdf`, 250 KB | Click upload zone → select file | `#resumeList` shows filename + size KB; toast `Resume uploaded successfully!` |
| JA-RES-02 | Cancel file picker | Profile tab | Open picker, cancel | — | No change to `#resumeList` |
| JA-RES-03 | Parse with AI | Resume uploaded | Click **Parse with AI** | — | Toast: `AI parsing resume...` (neutral) |

### 1.4 Job Search configuration

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-SCH-01 | Add title tag | Search tab | Type `DevOps Engineer`, press Enter | `addTag` on `#titleInput` | New tag in `#titleTags`; `#searchCount` increments |
| JA-SCH-02 | Remove title tag | Tag exists | Click × on tag | `removeTag` | Tag removed; `#searchCount` decrements |
| JA-SCH-03 | AI suggest titles | Search tab | Click **AI Suggest Titles** | `addPresetTitles()` | Adds 3 tags: Java Architect, Senior Java Engineer, J2EE Developer; toast success; count +3 |
| JA-SCH-04 | Add AND skill | Search tab | `Kubernetes`, Enter in `#andInput` | — | Tag with class `and` in `#andTags` |
| JA-SCH-05 | Add OR skill | Search tab | `Terraform`, Enter in `#orInput` | — | Tag with class `or` in `#orTags` |
| JA-SCH-06 | Location filters | Search tab | Location `Remote`, Posted Within `Last 7 Days` | Set fields | Values stored in inputs |
| JA-SCH-07 | Run Search Now | Search tab | Click **Run Search Now** | `runSearch()` | Toast `🔍 Searching 4 portals...`; `#resultsCount` animates 7→18; after ~2.5s switches to Results; toast `Found 18 matching jobs!` |
| JA-SCH-08 | Exclude-keywords Search button (React) | React app, Search tab | Type `Security, Clearance` in Exclude keywords, click inline **Search** | `runSearchAction()` | Keywords committed to search config; portal search runs; navigates to Results with matches filtered by exclusions |
| JA-SCH-09 | Exclude-keywords Enter key (React) | React app, Search tab | Type keyword, press **Enter** in Exclude keywords field | — | Same as JA-SCH-08 (search runs) |
| JA-SCH-10 | User role can run search (React) | Logged in as **user** | Configure a title + location, **Run search now** | `POST /api/job-automation/search/run` | HTTP 200; results returned (no 403); scoped to the user's own job results |

### 1.5 Portals & carriers

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-POR-01 | Add portal — valid | Portals tab | Name `ZipRecruiter`, URL `https://ziprecruiter.com` | Click **Add** | New row in `#portalList`; fields cleared; toast `${name} added to portals!` |
| JA-POR-02 | Add portal — missing fields | Portals tab | Name empty OR URL empty | Click **Add** | Toast: `Enter portal name and URL` |
| JA-POR-03 | Remove portal | Portal row exists | Click trash on custom row | `remove()` on row | Row removed from DOM |
| JA-POR-04 | Excel upload | Portals tab | File `portals.xlsx` | Upload via zone | `#portalFileList` shows filename; toast `Excel uploaded — parsing URLs...` |
| JA-CAR-01 | Add carrier | Portals tab | Name `Acme Corp`, URL `https://acme.com/careers` | **Add** | Row in `#carrierList`; toast `Acme Corp career page added!` |
| JA-CAR-02 | Add carrier — invalid | Portals tab | Empty name/URL | **Add** | Toast: `Enter company name and URL` |

### 1.6 Results panel

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-RES-01 | Render job list | Results tab | None | Open Results | 7 job cards from `JOBS` array; sorted by match % desc |
| JA-RES-02 | Search filter | Results tab | Search box `CloudBase` | `filterJobs('CloudBase')` | Only Spring Boot Engineer @ CloudBase Inc shown |
| JA-RES-03 | Type filter | Results tab | Filter `C2C` | `filterByType('C2C')` | Only C2C jobs shown |
| JA-RES-04 | Select job checkbox | Results tab | Check job id 0 | `toggleSelect(0)` | Card `#jcard-0` has `.selected`; `#selCount` = 1 |
| JA-RES-05 | Quick Apply | Results tab | Click Quick Apply on job 0 | `applyJob(0)` | `#stat-applied` increments by 1; toast `Applied to Senior Java Developer at TechCorp Solutions!` |
| JA-RES-06 | Apply selected — none | Results tab | No selection | **Apply Selected** | Toast: `Select jobs first!` |
| JA-RES-07 | Apply selected — 2 jobs | 2 jobs checked | **Apply Selected** | `applySelected()` | `#stat-applied` +2; toast `Applied to 2 jobs!`; selection cleared |
| JA-RES-08 | Save job | Results tab | Save on any job | `saveJob(id)` | Toast: `Job saved to favorites!` |
| JA-RES-09 | Analyze job | Results tab | Analyze on job 1 | `analyzeJob(1)` | Switches to Analyzer; JD populated; analysis runs |

### 1.6a Results panel — React app enhancements (v1.3)

Applies to `frontend/src/pages/JobAutomationPage.jsx` (React app at `/job-automation`), not the HTML prototype.

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-RES-10 | Results empty state | Fresh session, no search run | Open **Results** tab | — | "No search results yet" card with **Go to Job Search** button; clicking it switches to Search tab |
| JA-RES-11 | Filtered-out state | Results exist | Set filters that exclude all (e.g. min match 95%, unmatched query) | — | "No roles match the current filters" card showing total count + **Clear Results filters** button that restores results |
| JA-RES-12 | Results badge = total | Search returned N results | Apply a filter that hides some | — | Results nav tab badge shows total **N** (not filtered subset) |
| JA-RES-13 | Quick apply opens portal | Logged in (any role); results present | Click **Quick apply** on one card | `applyAction([id], { openPortal: true })` | New browser tab opens the portal's real search/application URL; toast confirms portal opened + tracker updated; app "Applied today" increments |
| JA-RES-14 | Quick apply URL sanitization | Result with polluted role/location data | Click **Quick apply** | — | Opened URL uses cleaned title (trimmed at first `\|`, length-capped) and a valid location (falls back to `United States` for junk) — never a malformed `where=` query |
| JA-RES-15 | Results Exclude-keywords Search | Results tab | Enter `Clearance` in Exclude keywords, click inline **Search** | — | Switches to Search tab and re-runs portal search with the exclusion applied |
| JA-RES-16 | AI keyword textarea | Resume parsed and/or search configured | Run search, open Results | — | Textarea is populated with unique AI-matched, required/optional, resume, and result skills separated by `, `; filtering matches any listed keyword |
| JA-RES-17 | Posted dropdown removed | Results tab | Inspect filter panel | — | No **Posted within** dropdown is present; posted date remains configured on Job Search |
| JA-RES-18 | Live Dice scrape | Dice active, location `Dallas, TX`, posted within 3 days, AI keyword `Java` | Run search | — | Backend requests `https://www.dice.com/jobs?filters.postedDate=THREE&countryCode=US&location=Dallas%2C+TX&q=Java`; Results contain live Dice job-detail URLs; fallback is used if Dice is unavailable |
| JA-RES-19 | Portal-specific scrape parameters | Multiple portals active; keyword `Java`, location `Dallas, TX`, posted within 3 days | Run search | — | Dice, CareerBuilder, LinkedIn, Indeed, and ZipRecruiter URLs use their native date parameter; Monster uses keyword/location/page and backend date filtering; custom portals receive generic query parameters |

### 1.6b Multi-CV library & session persistence (v1.4)

Applies to the React app (`/job-automation` My Profile tab) and backend `user_resumes` storage.

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-CV-01 | Upload multiple CVs | Logged in (any role) | Upload `cv-java.txt`, Parse with AI; then upload `cv-python.txt`, Parse with AI | `POST /api/job-automation/resume/parse` ×2 | Both CVs appear in the **CV library** panel; the most recent upload is marked **Active**; each entry shows skill count and AI role-fit % |
| JA-CV-02 | CV library in workspace | ≥1 CV uploaded | Reload the page | `GET /api/job-automation/workspace` | `resumes` array returned; CV library panel repopulates after refresh |
| JA-CV-03 | Switch active CV | ≥2 CVs uploaded | Click **Set active** on an inactive CV | `POST /api/job-automation/resumes/{id}/activate` | That CV becomes active; profile resume file name, resume skills, and search required skills update from the selected CV |
| JA-CV-04 | Delete CV with fallback | Active CV exists | Click the trash icon on the active CV | `DELETE /api/job-automation/resumes/{id}` | CV removed; the newest remaining CV becomes active and the profile updates; deleting the last CV clears the profile resume file name |
| JA-CV-05 | Re-upload same file | CV `cv-java.txt` exists | Parse `cv-java.txt` again | — | No duplicate row; the stored parse (summary, skills, ML score) is refreshed and the CV becomes active |
| JA-CV-06 | User-scoped CV library | Two users each upload CVs | Log in as the other user, open CV library | `GET /api/job-automation/resumes` | Each user only sees their own CVs (404 when activating/deleting another user's resume id) |
| JA-CV-07 | Session persists across reloads | Logged in | Reload the browser / reopen the tab | Token restored from localStorage | User remains logged in without re-entering credentials |
| JA-CV-08 | Sliding session renewal | Logged in, active use | Keep using the app past the initial session lifetime | Backend renews `auth_sessions.expires_at` when < half the lifetime remains | Active users are not logged out; 401 only after prolonged inactivity |

### 1.7 CV Analyzer

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-ANL-01 | Run analysis — no JD | Analyzer tab | Empty `#jdText` | **Run Analysis** | Toast: `Paste a job description first!` |
| JA-ANL-02 | Run analysis — with JD | Analyzer tab | JD text containing Java, Spring Boot, AWS | Paste + **Run Analysis** | `#analysisResult` visible; score % shown; matched/missed keyword chips; `#tailorCard` visible; toast with score |
| JA-ANL-03 | Select job from dropdown | Analyzer tab | Select job index `0` | `selectJobForAnalysis('0')` | `#jdText` filled with `JOB_JDS[0]` |
| JA-ANL-04 | Apply tailoring | After analysis | **Apply All Suggestions** | `applyTailoring()` | Toast: `All suggestions applied to CV!` |
| JA-ANL-05 | Download tailored CV | After analysis | **Download Tailored CV** | `downloadTailored()` | Toast: `Tailored CV downloaded!` |

### 1.8 LinkedIn jobs panel

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-LI-01 | Render LinkedIn cards | LinkedIn tab | None | Open tab | 9 `LI_JOBS` cards with match %, applicants, Easy Apply badges |
| JA-LI-02 | Easy Apply | LinkedIn tab | Apply on Wipro role | `applyLiJob(...)` | `#stat-applied` +1; toast with LinkedIn apply message |

### 1.9 Application tracker

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| JA-TRK-01 | All applications | Tracker tab | Sub-tab **All** | — | 6 apps from `TRACKER_APPS` with status pills |
| JA-TRK-02 | Interviews sub-tab | Tracker tab | Click **Interviews** | `switchSubTab` | Only Interview status rows |
| JA-TRK-03 | Stats sub-tab | Tracker tab | Click **Statistics** | — | Response rate 6.4%, Avg match 87%, etc. |

---

## 2. Campaigns Mass Email (`campaigns_tab_mass_email.html`)

### 2.1 Navigation & stats

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| CM-NAV-01 | Campaigns active | Page loaded | None | Open file | **Campaigns** nav active; `#panel-campaigns` visible |
| CM-NAV-02 | Placeholder panels | Page loaded | Click Profile / Job Search / etc. | — | Placeholder card with icon + message |
| CM-STAT-01 | Initial KPIs | Page loaded | None | Read stats | Sent **1,284**; Open **38%**; Reply **12%**; Bounce **2%** |

### 2.2 Compose — email editor

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| CM-CMP-01 | Campaign name | Compose tab | `campName` = `Python Bench — June 2026` | Type | Field updated |
| CM-CMP-02 | Rich text bold | Compose tab | Select text, click Bold | `fmt('bold')` | Selected text bold in `#emailBody` |
| CM-CMP-03 | Insert merge tag | Compose tab | Click `{{candidate_name}}` chip | `insertMerge` | Tag inserted at cursor in body |
| CM-CMP-04 | Clear body — confirm | Body has content | **Clear**, confirm OK | `clearBody()` | `#emailBody` empty |
| CM-CMP-05 | Clear body — cancel | Body has content | **Clear**, cancel | — | Body unchanged |
| CM-CMP-06 | Copy body | Body has text | **Copy** | `copyBody()` | Toast: `Email body copied!` |
| CM-CMP-07 | Insert link | Compose tab | URL `https://example.com` | `insertLink()` | Link created in editor |
| CM-CMP-08 | Insert table | Compose tab | **Insert table** | `insertTable()` | 2×2 HTML table in body |
| CM-CMP-09 | Preview email | Subject + body set | **Preview** | `previewEmail()` | `#previewArea` visible; subject/body mirrored |
| CM-CMP-10 | Save draft | Compose tab | **Save Draft** | `saveDraft()` | Toast: `Campaign saved as draft!` |

### 2.3 AI compose

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| CM-AI-01 | Quick prompt — hotlist | Compose tab | Click **Hotlist blast** chip | `setPrompt('hotlist')` | `#aiPromptInput` filled with hotlist prompt text |
| CM-AI-02 | Generate — empty prompt | Compose tab | Clear prompt, **Generate** | `generateAI()` | Toast: `Please enter a prompt or select a quick prompt` |
| CM-AI-03 | Generate — hotlist | Prompt set | **Generate Email** | `generateAI()` | `#aiGenerating` spinner steps; body replaced with `AI_EMAILS.hotlist` HTML; toast purple success |
| CM-AI-04 | Improve email | Body non-empty | **Improve** | `improveAI()` | Spinner ~2.2s; toast `Email improved by AI!` |
| CM-AI-05 | Translate | Body non-empty | Language `Spanish` | `translateAI()` | Toasts: translating → translated |
| CM-AI-06 | AI subject | Compose tab | Click sparkles on subject | `aiSubject()` | After ~1.4s subject = `🔥 Senior Java Developer | C2C | Immediate | Dallas TX | H1B | $85-90/hr` |

### 2.4 Contacts & recipients

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| CM-CON-01 | Load all contacts | Compose tab | List = **All contacts** | `loadContactList('all')` | 8 contacts in preview; toast `Loaded 8 contacts` |
| CM-CON-02 | Load vendors | Compose tab | List = vendors | — | Filtered contacts; toast with count |
| CM-CON-03 | Search contacts | Compose tab | Search `Michael` | `filterContacts('Michael')` | Michael Torres row only |
| CM-CON-04 | Toggle contact | Contact visible | Click row | `toggleContact(email)` | Row highlighted; `#recipCount` updates |
| CM-CON-05 | Select all | Contacts loaded | **Select all** | `selectAllContacts()` | `#recipCount` = 8; toast success |
| CM-CON-06 | Clear selection | Contacts selected | **Clear** | `clearContacts()` | `#recipCount` = 0 |
| CM-CON-07 | Import Excel | Compose tab | File `contacts.xlsx` | `importExcel` | After ~1.2s: 2 new contacts; 2 emails auto-selected; toast imported |
| CM-CON-08 | Paste emails | Compose tab | `a@test.com, b@test.com` | **Parse emails** | 2 contacts added; `#recipCount` +2; textarea cleared |

### 2.5 Templates & campaigns history

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| CM-TPL-01 | View templates | Templates sub-tab | Open sub-tab | `renderTemplates()` | 4 templates listed (Hotlist Blast, etc.) |
| CM-TPL-02 | Use template | Templates tab | **Use** on Hotlist Blast | `useTemplate(0)` | Subject + body loaded; switches to Compose; toast loaded |
| CM-TPL-03 | Preview template | Templates tab | Click template card | `previewTemplate(i)` | Preview card visible with subject + body |
| CM-CAM-01 | Campaign history | Campaigns sub-tab | Open sub-tab | — | 5 items from `CAMPAIGN_HISTORY` with status badges |
| CM-CAM-02 | Progress bar | Sent campaign | View Java Hotlist April | — | Progress fill width = opened % (41%) |

### 2.6 Send & schedule

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| CM-SND-01 | Launch — no recipients | Compose tab | `#recipCount` = 0 | **Launch** / scheduler send | Toast: `Select at least 1 recipient` |
| CM-SND-02 | Send test | Compose tab | Email `test@company.com` | `sendTest()` | Toast: `Test email sent to test@company.com!` |
| CM-SND-03 | Open scheduler | Compose tab | **Schedule / Send** | `openScheduler()` | `#schedulerCard` visible; `#sendDate` = tomorrow |
| CM-SND-04 | Immediate launch | 3 recipients selected; immediate toggle ON | **Send now** in scheduler | `launchCampaign()` | `#st-sent` animates upward; toast `Campaign "{name}" sent to 3 recipients!`; history row added |
| CM-SND-05 | Scheduled launch | 2 recipients; immediate OFF; date `2026-07-15`, time `09:00` | Launch | — | Toast: `Campaign scheduled for 2026-07-15 at 09:00!`; history status **Scheduled** |

### 2.7 Attachments

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| CM-ATT-01 | Add attachment | Compose tab | Files `cv.pdf`, `hotlist.docx` | `handleAttach` | Both listed in `#attList` with KB sizes |
| CM-ATT-02 | Remove attachment | File listed | Click × on file row | — | Row removed |

---

## 3. Day-to-Day Report Dashboard (`day_to_day_report_dashboard.html`)

**Embedded data:** `payload.data_rows` (recruiters: Chandrika, Komal, Nan, Parasuram, Sam).  
**Default range:** `2027-01-21` to `2027-02-20` (from `payload.start_default` / `end_default`).

### 3.1 Initialization

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| DR-INIT-01 | Page load | Open HTML | None | `setup()` runs | `#startDate` / `#endDate` set to defaults; recruiter dropdown has All + 5 recruiters; `#rangeTxt` updated; charts render |
| DR-INIT-02 | Recruiter options | Page loaded | Inspect `#recruiterSel` | — | Options: `__all__`, Chandrika, Komal, Nan, Parasuram, Sam |
| DR-INIT-03 | Date bounds | Page loaded | Inspect date inputs | — | min = `2026-01-13`, max = `2027-02-20` |

### 3.2 Filter — Apply

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| DR-FLT-01 | Default apply | Page loaded | Defaults | Auto `applyFilters()` | KPIs sum all rows in default range; 4 Plotly charts + table render |
| DR-FLT-02 | Single recruiter — Sam | Page loaded | Start `2026-02-16`, End `2026-02-16`, Recruiter **Sam** | **Apply** | `#kpi1v` = **15** (LinkedIn); `#kpi2v` = **12** (calls); `#kpi3v` = **2** (sourced); `#kpi4v` = **1** (marketing); `#rangeTxt` includes dates |
| DR-FLT-03 | Recruiter Komal — Feb 2026 | Page loaded | Start `2026-02-01`, End `2026-02-28`, Recruiter **Komal** | **Apply** | KPIs = sum of Komal rows in February 2026 only; trend chart x-axis limited to those dates |
| DR-FLT-04 | All recruiters — narrow range | Page loaded | Start `2026-03-13`, End `2026-03-13` | Recruiter **All**, **Apply** | Only rows dated 2026-03-13 (Sam + Komal entries) included |
| DR-FLT-05 | No matching rows | Page loaded | Start `2026-01-01`, End `2026-01-10` | **Apply** | All KPIs = **0** or **-**; charts empty/zero; table has 0 rows |
| DR-FLT-06 | Invalid range (start > end) | Page loaded | Start `2026-05-01`, End `2026-04-01` | **Apply** | Filtered set empty → KPIs 0; no JS error |

### 3.3 Filter — Reset

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| DR-RST-01 | Reset after filter | Filters changed | Click **Reset** | — | Dates → defaults; recruiter → **All**; KPIs/charts match default range again |

### 3.4 KPI calculations (formula)

For any filtered set `F`:

| KPI | Element | Calculation | Null handling |
|-----|---------|-------------|---------------|
| LinkedIn | `#kpi1v` | Σ `Number(row.li)\|\|0` | `fmtInt` → `-` if NaN |
| Calls | `#kpi2v` | Σ `Number(row.calls)\|\|0` | same |
| Sourced | `#kpi3v` | Σ `Number(row.sourced)\|\|0` | same |
| Marketing | `#kpi4v` | Σ `Number(row.mkt)\|\|0` | same |

### 3.5 Charts & table

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| DR-CHT-01 | Trend chart | After apply | — | Inspect `#trendChart` | 4 traces: Sourced, Calls, LinkedIn (dotted), Marketing (dashed) |
| DR-CHT-02 | Recruiter chart | After apply | — | `#recruiterChart` | Horizontal bar chart; sorted by sourced desc |
| DR-CHT-03 | Mix chart | After apply | — | `#mixChart` | Stacked bars by day |
| DR-CHT-04 | Tech chart | After apply | — | `#techChart` | Top 10 technologies by row count |
| DR-TBL-01 | Recent table | After apply | — | `#tableDiv` | Max **25** rows, newest dates first; Notes column `Yes` if notes non-empty |
| DR-TBL-02 | Weekend row | Filter includes Nan weekend | — | — | LinkedIn/Calls/Sourced show `-` in table |

---

## 4. LinkedIn Recruiter Discovery (`linkedin_recruiter_discovery_panel.html`)

### 4.1 Layout & stats

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| LI-INIT-01 | Default view | Page loaded | None | — | Discover sub-tab active; stats: Found **247**, Contacted **89**, Replied **23**, Follow-ups **14** |
| LI-INIT-02 | Selected badge | Page loaded | None | — | `#selectedBadge` = `0 selected` |

### 4.2 Discover — company & tech filters

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| LI-DIS-01 | Toggle company off | TEKsystems active | Click TEKsystems chip | `toggleChip` | Chip inactive; removed from `activeCompanies` |
| LI-DIS-02 | Toggle company on | Robert Half inactive | Click chip | — | Chip active with check icon |
| LI-DIS-03 | Add custom company | Discover tab | `newCompany` = `Deloitte` | **Add** | New chip in `#companyChips`; toast added |
| LI-DIS-04 | Toggle tech keyword | Discover tab | Click `AWS` chip | `toggleTech` | AWS in/out of `activeTechs`; `#searchPreview` updates |
| LI-DIS-05 | Add custom tech | Discover tab | `newTech` = `Kafka` | **Add** | New active tech chip; preview includes `"Kafka"` |
| LI-DIS-06 | Search preview text | Java + Spring Boot active | — | Read `#searchPreview` | `"Recruiter" AND ("Java" OR "Spring Boot")` |

### 4.3 Discover — run search

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| LI-DIS-07 | Run — no companies | All companies deselected | **Discover Recruiters** | `runDiscovery()` | Toast: `Select at least one target company` |
| LI-DIS-08 | Run — no tech | `activeTechs` empty | **Discover** | — | Toast: `Select at least one technology keyword` |
| LI-DIS-09 | Run — success | ≥1 company, ≥1 tech | **Discover Recruiters** | — | Spinner messages; then 8 recruiter cards; `#st-disc` = **8**; toast `Found 8 matching recruiters!` |
| LI-DIS-10 | Filter recruiters | Results shown | Search `Jessica` | `filterRecruiters` | Only Jessica Turner card |
| LI-DIS-11 | Sort by match | Results shown | Sort **Highest match** | `sortRecruiters('match')` | Cards ordered match desc (96 first) |
| LI-DIS-12 | Select recruiter | Results shown | Click card checkbox | — | `selectedRecs` has id; badge updates |
| LI-DIS-13 | Select all | Results shown | **Select all** | `selectAllRecs()` | 8 selected; toast success |
| LI-DIS-14 | Clear results | Results shown | **Clear** | `clearResults()` | Empty list; selection cleared |

### 4.4 Quick actions

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| LI-QA-01 | Quick connect | Results shown | Connect on id 1 | `quickConnect(1)` | Toast: `Connection request sent to Jessica Turner!` |
| LI-QA-02 | Quick message | Results shown | Message on id 3 | `quickMsg(3)` | Switches to AI Outreach; body pre-filled with Anita Sharma text |
| LI-QA-03 | Bulk outreach | 3 selected | **Bulk outreach** | `bulkOutreach()` | Opens compose sub-tab; outreach list populated |

### 4.5 Paste profiles

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| LI-PST-01 | Enrich URLs | Paste tab | 3 LinkedIn URLs (one per line) | **Enrich profiles** | Toast enriching; after 2s `#enrichedList` has 3 cards; toast success |
| LI-PST-02 | Enrich — empty | Paste tab | Empty textarea | **Enrich** | Toast: `Paste some LinkedIn URLs first` |
| LI-PST-03 | Add URL to queue | Paste tab | URL in `#newUrl` | **Add** | Row in `#urlQueue` status Pending |
| LI-PST-04 | Run queue | URLs queued | **Run queue** | `runQueue()` | Toast API lookup → `Queue complete — 12 recruiters found!` |

### 4.6 AI Outreach

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| LI-OUT-01 | Message type — connect | Compose sub-tab | Click **Connection request** | `setMsgType('connect')` | Subject + body from `MSG_BODIES.connect` |
| LI-OUT-02 | Generate message | Prompt text entered | **Generate** | `generateMsg()` | Spinner steps; default AI body in `#msgBody`; char count updates |
| LI-OUT-03 | Generate — empty | Empty prompt | **Generate** | — | Toast: `Enter a prompt or select a message type first` |
| LI-OUT-04 | Send — no selection | Compose tab | 0 selected | **Send to selected** | Toast: `No recruiters selected` |
| LI-OUT-05 | Send — no body | Selected, empty body | **Send** | — | Toast: `Write a message first` |
| LI-OUT-06 | Send — success | 2 selected, body filled | **Send to selected** | `sendToSelected()` | `#st-cont` increases by 2; toast sent |
| LI-OUT-07 | Use template | Templates sidebar | Click template 0 | `useMsgTemplate(0)` | Body = template text; toast loaded |
| LI-OUT-08 | Schedule outreach | Compose tab | **Schedule** | `scheduleOutreach()` | Toast: `Outreach sequence scheduled!` |

### 4.7 Sequence tracker

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| LI-TRK-01 | Render sequences | Tracker sub-tab | Open tab | `renderTracker()` | 4 sequences from `SEQ_DATA` with step dots |
| LI-TRK-02 | Follow-ups list | Tracker sub-tab | — | `#followupList` | Anita Sharma (Today), David Rodriguez (Today), Lisa Chen (Tomorrow) |
| LI-TRK-03 | Send follow-up | Tracker tab | Send on follow-up row | — | Toast: `Follow-up sent to {name}!` |

### 4.8 API sources & settings

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| LI-API-01 | API tab | APIs sub-tab | View connection cards | — | Apollo, Hunter, etc. show Connected/Disconnected badges |
| LI-SET-01 | Save LinkedIn settings | Settings sub-tab | Change daily limit to 25 | **Save** | Toast: `LinkedIn settings saved!` |
| LI-SET-02 | Compliance toggles | Settings sub-tab | Toggle do-not-contact | Click toggle | `#t7` on/off state changes |

---

## 5. Submission Progress MoM / YoY / Calendar

**Reference:** `frontend/src/pages/SubmissionProgressPage.jsx`  
**API:** `GET /api/submissions/dashboard`, `POST /api/submissions/filter`  
**Sample seed data** (`test_data.default.json`):

| month | submissions |
|-------|-------------|
| 2025-11 | 24 |
| 2025-12 | 28 |
| 2026-01 | 31 |
| 2026-02 | 34 |
| 2026-03 | 39 |
| 2026-04 | 42 |
| 2026-05 | 47 |

**MoM formula:** `round((current - prior_month) / prior_month * 100, 1)` — null if no prior month.  
**YoY formula:** same vs same month prior year — null if prior year missing or zero.

### 5.1 Dashboard load

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| SP-INIT-01 | Initial load | User logged in; app on `/submissions` | Navigate to Submissions | `GET /api/submissions/dashboard` | Hero shows range; start/end month inputs filled; summary total = **245** (sum of 7 months); average = **35** (245÷7) |
| SP-INIT-02 | Calendar heatmap | Workspace loaded | None | View calendar | Cells for 2025-11…2026-05 show submission counts; empty months show `·` |
| SP-INIT-03 | Charts populated | Workspace loaded | None | — | Line chart (volume), MoM bar chart, YoY line chart render with 7 data points |
| SP-INIT-04 | Monthly table | Workspace loaded | None | — | 7 rows with Month, Submissions, MoM %, YoY % |

### 5.2 Month range filter

| TC ID | Feature | Preconditions | Input (API body) | Steps | Expected output |
|-------|---------|---------------|------------------|-------|-----------------|
| SP-FLT-01 | Full range | App on submissions | `{ "startMonth": "2025-11", "endMonth": "2026-05" }` | **Apply** | `months.length` = 7; `summary.total` = 245; `summary.average` = 35 |
| SP-FLT-02 | Single month | App on submissions | `{ "startMonth": "2026-03", "endMonth": "2026-03" }` | **Apply** | 1 month row; submissions = 39; MoM for 2026-03 = **13.2%** ((39-34)/34×100); YoY = null (no 2025-03) |
| SP-FLT-03 | Q1 2026 | App on submissions | start `2026-01`, end `2026-03` | **Apply** | 3 months; total = 104; average = 35 |
| SP-FLT-04 | Invalid — end before start | App on submissions | start `2026-05`, end `2026-01` | **Apply** (UI) | Validation banner: `End month cannot be before start month.`; no API call |
| SP-FLT-05 | Empty start month | App on submissions | start `""`, end `2026-05` | **Apply** | Banner: `Start month is required.` |
| SP-FLT-06 | Reset | After filter | Click **Reset** | `resetFilters()` | Inputs → workspace default range; data restored to full dashboard |

### 5.3 Calendar click filter

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| SP-CAL-01 | Click month cell | Calendar visible | Click cell `2026-04` (42 submissions) | `selectCalendarMonth` | startMonth = endMonth = `2026-04`; range text `2026-04`; table shows 1 row; total = 42 |
| SP-CAL-02 | Click empty cell | Month with no data | Click empty cell | — | No action (`hasData` false); filter unchanged |
| SP-CAL-03 | Active cell style | After SP-CAL-01 | — | — | Clicked cell has `.active` class |

### 5.4 MoM / YoY display rules

| TC ID | Feature | Preconditions | Input data | Expected output |
|-------|---------|---------------|------------|-----------------|
| SP-MOM-01 | First month MoM | Filter from 2025-11 only | month 2025-11 | MoM column = **N/A** (no prior month in series) |
| SP-MOM-02 | Positive MoM | 2026-02 row | prior 2026-01 = 31, current 34 | MoM = **9.7%**; bar color teal (`#30c0c7`) |
| SP-MOM-03 | Negative MoM | Hypothetical drop month | current < prior | Bar color orange (`#ff9457`) |
| SP-YOY-01 | No prior year | Any 2025-11 row | no 2024-11 in data | YoY = **N/A** in table and gap in line chart |
| SP-YOY-02 | YoY tooltip | Month with yoy value | hover chart | Tooltip shows `value%` not raw decimal |

### 5.5 API error fallback

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| SP-ERR-01 | Backend offline | Stop backend | Apply filter | POST fails | Banner: filter failed message; local workspace months filtered client-side; charts still update |

### 5.6 Legacy redirect

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| SP-LEG-01 | Legacy HTML redirect | Open `frontend/public/legacy/submissions.html` | — | Browser load | Meta refresh to `/submissions`; React app loads Submission Progress page |

---

## 6. Cross-module smoke checklist

| TC ID | Modules | Input | Expected output |
|-------|---------|-------|-----------------|
| X-SMK-01 | All HTML files | Open each in browser | No console errors on load (except optional CDN if offline) |
| X-SMK-02 | All HTML files | Resize to 580px width | Grids collapse to single column (responsive CSS) |
| X-SMK-03 | All HTML files | Trigger any success toast | Toast appears bottom-right, auto-hides ~3s |
| X-SMK-04 | Job + Campaigns + LinkedIn | Tabler icons CDN loaded | Icons render (not blank squares) |

---

## 7. Test data quick reference

### Job Automation — sample job (id 0)

```json
{
  "title": "Senior Java Developer",
  "company": "TechCorp Solutions",
  "match": 92,
  "type": "C2C",
  "rate": "$85-95/hr"
}
```

### Campaigns — sample contact

```json
{
  "name": "Michael Torres",
  "email": "m.torres@tcs.com",
  "company": "TCS",
  "tag": "primes"
}
```

### LinkedIn — sample recruiter (id 1)

```json
{
  "name": "Jessica Turner",
  "company": "TEKsystems",
  "match": 96,
  "source": "Apollo"
}
```

### Day report — sample row (Sam, 2026-02-16)

```json
{
  "Date_dt": "2026-02-16",
  "Recruiter Name": "Sam",
  "Linkedin Connections_num": 15,
  "Daily calls Count_num": 12,
  "Sourced Data Count_num": 2,
  "Marketing/Submissions Count_num": 1
}
```

### Submissions — MoM example (2026-02)

| Field | Value |
|-------|-------|
| submissions | 34 |
| prior month (2026-01) | 31 |
| mom % | 9.7 |
| yoy | null |

---

## 8. Traceability matrix

| Business capability | Primary file | TC ID prefix |
|--------------------|--------------|--------------|
| Candidate profile & auto-apply | job_automation_platform.html | JA-* |
| Job search & results | job_automation_platform.html | JA-SCH-*, JA-RES-* |
| Portal/carrier management | job_automation_platform.html | JA-POR-*, JA-CAR-* |
| CV match analysis | job_automation_platform.html | JA-ANL-* |
| Mass email campaigns | campaigns_tab_mass_email.html | CM-* |
| Recruiter daily KPIs | day_to_day_report_dashboard.html | DR-* |
| LinkedIn recruiter outreach | linkedin_recruiter_discovery_panel.html | LI-* |
| Submission MoM/YoY/calendar | SubmissionProgressPage.jsx | SP-* |
| Email & SMS notifications | UserProfilePage.jsx + Campaign Studio | NT-*, CM-SND-02 |

---

## 9. Notifications — Email & SMS (`UserProfilePage.jsx`)

Maps to `POST /api/notifications/*` and Campaign SMTP (`CM-SND-02`).

| TC ID | Feature | Preconditions | Input | Steps | Expected output |
|-------|---------|---------------|-------|-------|-----------------|
| NT-SET-01 | Channel status | Logged in | Open Profile → Notifications | Page load | Banner shows email/SMS configured or demo mode |
| NT-SET-02 | Save SMS prefs | Notifications tab | Enable SMS, phone `+15555550128` | **Save Preferences** | Toast success; settings persist on reload |
| NT-TST-01 | Test email | Notifications tab | Click **Send test email** | — | Toast: test email sent (live or demo) |
| NT-TST-02 | Test SMS | SMS enabled + phone set | Click **Send test SMS** | — | Toast: test SMS sent (live or demo) |
| NT-HIS-01 | Delivery history | After NT-TST-01 | — | Scroll history table | Row with channel `email`, status `sent` |
| NT-JOB-01 | Auto-apply alert | Job automation alerts ON | Run **auto apply** | — | Email/SMS delivery when job alerts enabled (see history) |
| NT-CMP-01 | Campaign alert | Campaign alerts ON | Launch campaign (admin) | — | Email notification logged for campaign event |

---

*End of document*
