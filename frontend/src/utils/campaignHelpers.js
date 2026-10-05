import { isEmail } from './validators'

export const AI_PROMPT_LABELS = [
  'Hotlist blast',
  'Candidate intro',
  'Follow-up',
  'Urgent placement',
  'Bench sales',
  'Re-introduction',
  'Rate negotiation',
  'Availability update',
]

export const AI_PROMPTS = {
  'Hotlist blast':
    'Write a hotlist email for a Senior Java Developer available on C2C. 8 years experience. Skills: Spring Boot, Microservices, AWS, Docker, Kubernetes. Location: Dallas TX. Available immediately. Rate: $85-90/hr. H1B visa. Keep it concise and professional.',
  'Candidate intro':
    'Write a formal candidate introduction email for a Full Stack Developer (React + Java) with 6 years of experience applying for a contract role at a prime vendor. Highlight technical skills and immediate availability.',
  'Follow-up':
    'Write a professional follow-up email for a hotlist I sent 3 days ago about a Java Developer. Be polite, brief, and create urgency without being pushy.',
  'Urgent placement':
    'Write an urgent placement email for a DevOps Engineer available immediately. Skills: AWS, Terraform, Kubernetes, CI/CD. Location: Remote. Rate: $80/hr. Emphasize immediate availability and multiple interview requests.',
  'Bench sales':
    'Write a bench sales email marketing 3 consultants — Java Developer, React Developer, and a Data Engineer — all available immediately in Texas. Keep it scannable with bullets.',
  'Re-introduction':
    'Write a re-introduction email to a recruiter I contacted 6 months ago. I have a new Python/ML Engineer available. Acknowledge the time gap and highlight fresh availability.',
  'Rate negotiation':
    'Write a rate negotiation email where I am countering a $75/hr offer for my Java consultant and proposing $85/hr based on 10 years of experience and niche skills in Kafka and Spring Cloud.',
  'Availability update':
    'Write a brief availability update email letting vendors know my Java consultant who was on a project just became available in 2 weeks and is actively seeking C2C contract roles.',
}

export const AI_EMAIL_HTML = {
  hotlist: `<p>Hi {{recruiter_name}},</p><p>Hope this finds you well! I'm reaching out with an exciting consultant who just became available:</p><p><strong>Senior Java Developer — Actively Available</strong></p><ul><li><strong>Experience:</strong> 8+ years</li><li><strong>Core Skills:</strong> Spring Boot · Microservices · AWS · Docker · Kubernetes</li><li><strong>Location:</strong> Dallas, TX (Open to Remote/Hybrid)</li><li><strong>Availability:</strong> Immediate</li><li><strong>Rate:</strong> $85–90/hr on C2C</li><li><strong>Visa:</strong> H1B (No cap-gap)</li></ul><p>This consultant has led microservices migrations and has hands-on production experience with AWS EKS and CI/CD pipelines. Resume attached for your review.</p><p>Let me know if there's a fit — happy to set up a quick call!</p><p>Best,<br>{{recruiter_name}} | {{company_name}}</p>`,
  intro: `<p>Dear {{recruiter_name}},</p><p>I hope you're having a great week. I am writing to formally introduce <strong>{{candidate_name}}</strong>, a Full Stack Developer with 6 years of hands-on experience in <strong>React.js</strong> and <strong>Java Spring Boot</strong>.</p><p>{{candidate_name}} has delivered end-to-end web applications across fintech and healthcare domains and is immediately available for contract engagements. The attached resume provides full project details.</p><p>I believe this profile aligns well with your current requirements. I would welcome the opportunity to discuss further at your convenience.</p><p>Warm regards,<br>{{recruiter_name}}</p>`,
  followup: `<p>Hi {{recruiter_name}},</p><p>I wanted to follow up on the Java Developer profile I shared earlier this week. This consultant remains available and has received interest from a few other vendors, so I wanted to circle back before the window closes.</p><p>Would you have any matching C2C requirements? Even a quick call would help us align.</p><p>Thanks for your time,<br>{{recruiter_name}} | {{company_name}}</p>`,
  urgent: `<p>Hi {{recruiter_name}},</p><p><strong>Urgent — DevOps Engineer Available Immediately</strong></p><p>I have a highly skilled DevOps consultant available <strong>right now</strong> and this profile is moving fast:</p><ul><li>AWS · Terraform · Kubernetes · Jenkins CI/CD</li><li>Location: Remote (Any timezone)</li><li>Rate: $80/hr C2C</li><li>Availability: <strong>Immediate start</strong></li></ul><p>Multiple interviews are already scheduled — please respond today if you have an open requirement.</p><p>{{recruiter_name}} | {{company_name}}</p>`,
  bench: `<p>Hi {{recruiter_name}},</p><p>We currently have the following consultants on the bench and actively available:</p><table style="border-collapse:collapse;width:100%;font-size:12px"><tr style="background:#f3f4f6"><th style="border:1px solid #e5e7eb;padding:6px;text-align:left">Role</th><th style="border:1px solid #e5e7eb;padding:6px;text-align:left">Skills</th><th style="border:1px solid #e5e7eb;padding:6px;text-align:left">Location</th><th style="border:1px solid #e5e7eb;padding:6px;text-align:left">Rate</th></tr><tr><td style="border:1px solid #e5e7eb;padding:6px">Java Developer</td><td style="border:1px solid #e5e7eb;padding:6px">Spring Boot, AWS, Microservices</td><td style="border:1px solid #e5e7eb;padding:6px">Dallas, TX</td><td style="border:1px solid #e5e7eb;padding:6px">$85/hr C2C</td></tr><tr><td style="border:1px solid #e5e7eb;padding:6px">React Developer</td><td style="border:1px solid #e5e7eb;padding:6px">React, TypeScript, Node.js</td><td style="border:1px solid #e5e7eb;padding:6px">Austin, TX</td><td style="border:1px solid #e5e7eb;padding:6px">$80/hr C2C</td></tr><tr><td style="border:1px solid #e5e7eb;padding:6px">Data Engineer</td><td style="border:1px solid #e5e7eb;padding:6px">Python, Spark, Snowflake, dbt</td><td style="border:1px solid #e5e7eb;padding:6px">Remote</td><td style="border:1px solid #e5e7eb;padding:6px">$90/hr C2C</td></tr></table><p style="margin-top:10px">Resumes available on request. Please let me know if any of these profiles match your open requirements.</p><p>Best,<br>{{recruiter_name}} | {{company_name}}</p>`,
  reintro: `<p>Hi {{recruiter_name}},</p><p>It's been a while since we last connected — I hope things are going well for you and your team!</p><p>I'm reaching out today because I have a strong <strong>Python / ML Engineer</strong> who just became available and thought of you right away.</p><ul><li>Skills: Python · TensorFlow · PyTorch · AWS SageMaker · MLOps</li><li>Experience: 7 years</li><li>Location: Remote</li><li>Rate: $95/hr C2C</li></ul><p>I'd love to reconnect and see if there's a fit. Would you be open to a quick 10-minute call this week?</p><p>Best,<br>{{recruiter_name}}</p>`,
  rate: `<p>Hi {{recruiter_name}},</p><p>Thank you for extending the offer of $75/hr for our Java consultant. We genuinely appreciate the opportunity and are excited about the potential partnership.</p><p>However, given the consultant's <strong>10 years of niche expertise</strong> — particularly in Kafka and Spring Cloud, which are critical to your project — we believe a rate of <strong>$85/hr on C2C</strong> more accurately reflects the market value.</p><p>We're confident this consultant will deliver strong ROI from day one. Would you be able to meet us at $85/hr? Happy to discuss further.</p><p>Warm regards,<br>{{recruiter_name}} | {{company_name}}</p>`,
  availability: `<p>Hi {{recruiter_name}},</p><p>Quick update — our <strong>Senior Java Developer</strong> is wrapping up their current engagement and will be <strong>fully available in 2 weeks</strong>.</p><p>They are actively seeking C2C contract roles and are open to remote or hybrid positions nationwide.</p><ul><li>Skills: Java 17 · Spring Boot · AWS · Microservices</li><li>Experience: 8+ years</li><li>Rate: $85/hr C2C</li><li>Available: May 20, 2025</li></ul><p>Please keep us in mind if any matching requirements come up. Resume available upon request.</p><p>{{recruiter_name}} | {{company_name}}</p>`,
}

const PROMPT_KEY_MAP = {
  'Hotlist blast': 'hotlist',
  'Candidate intro': 'intro',
  'Follow-up': 'followup',
  'Urgent placement': 'urgent',
  'Bench sales': 'bench',
  'Re-introduction': 'reintro',
  'Rate negotiation': 'rate',
  'Availability update': 'availability',
}

export const SENDING_SPEED_OPTIONS = [
  { value: '50', label: 'Normal (50/hr)' },
  { value: '100', label: 'Medium (100/hr)' },
  { value: '200', label: 'Fast (200/hr)' },
  { value: 'instant', label: 'Instant (all at once)' },
]

export const SMTP_PORT_OPTIONS = [
  { value: 587, label: '587 (TLS)' },
  { value: 465, label: '465 (SSL)' },
  { value: 25, label: '25' },
]

export const CONTACT_AVATAR_COLORS = [
  { bg: '#dbeafe', text: '#1e40af' },
  { bg: '#d1fae5', text: '#065f46' },
  { bg: '#ede9fe', text: '#5b21b6' },
  { bg: '#fef3c7', text: '#92400e' },
  { bg: '#fee2e2', text: '#991b1b' },
]

export function avatarColorForIndex(index) {
  return CONTACT_AVATAR_COLORS[index % CONTACT_AVATAR_COLORS.length]
}

export function applyAiToneAndLength(html, tone, length) {
  let body = html
  if (tone === 'urgent') {
    body = body.replace('<p>Hi', '<p><strong>URGENT:</strong> Hi')
  } else if (tone === 'friendly') {
    body = body.replace('Best,', 'Thanks so much,')
  } else if (tone === 'formal') {
    body = body.replace('Hi {{recruiter_name}}', 'Dear {{recruiter_name}}')
  } else if (tone === 'concise') {
    body = body.replace(/<ul>[\s\S]*?<\/ul>/, '')
  }

  if (length === 'short') {
    const paragraphs = body.match(/<p>[\s\S]*?<\/p>/g) ?? []
    body = paragraphs.slice(0, 3).join('')
  } else if (length === 'long') {
    body += '<p>Happy to share resume, RTR, references, and interview availability on request.</p>'
  }

  return body
}

export function buildCampaignAnalytics(campaign) {
  const sent = campaign.sent ?? 0
  const opened = campaign.opened ?? 0
  const replied = campaign.replied ?? 0
  const openRate = sent > 0 ? Math.round((opened / sent) * 100) : 0
  const replyRate = sent > 0 ? Math.round((replied / sent) * 100) : 0
  const clickRate = sent > 0 ? Math.max(0, Math.round(openRate * 0.42)) : 0
  const bounceRate = sent > 0 ? Math.max(1, Math.round(sent * 0.02)) : 0

  return {
    sent,
    opened,
    replied,
    openRate,
    replyRate,
    clickRate,
    bounceRate,
    deliveryRate: sent > 0 ? Math.max(0, 100 - bounceRate) : 0,
    topList: campaign.list ?? 'Priority Accounts',
    lastActivity: campaign.scheduledFor ?? '—',
  }
}

export function updateLiveMetrics(metrics, sentCount) {
  const emailsSent = (metrics.emailsSent ?? 0) + sentCount
  return {
    ...metrics,
    emailsSent,
    openRate: metrics.openRate ?? 38,
    replyRate: metrics.replyRate ?? 12,
    bounceRate: metrics.bounceRate ?? 2,
  }
}

export const AI_GENERATION_STEPS = [
  'Analyzing your prompt...',
  'Drafting subject line...',
  'Writing email body...',
  'Applying personalization...',
  'Finalizing...',
]

export const LIST_COLORS = ['#2563eb', '#059669', '#d97706', '#7c3aed', '#dc2626']

export function pickAiEmailKey(promptText, presetLabel) {
  if (presetLabel && PROMPT_KEY_MAP[presetLabel]) {
    return PROMPT_KEY_MAP[presetLabel]
  }

  const normalized = (promptText ?? '').toLowerCase()
  for (const [label, key] of Object.entries(PROMPT_KEY_MAP)) {
    const snippet = AI_PROMPTS[label]?.substring(0, 24).toLowerCase() ?? ''
    if (snippet && normalized.includes(snippet)) {
      return key
    }
  }

  if (normalized.includes('follow-up') || normalized.includes('follow up')) {
    return 'followup'
  }
  if (normalized.includes('urgent') || normalized.includes('devops')) {
    return 'urgent'
  }
  if (normalized.includes('bench')) {
    return 'bench'
  }
  if (normalized.includes('rate') || normalized.includes('$75')) {
    return 'rate'
  }
  if (normalized.includes('available in 2 weeks') || normalized.includes('availability')) {
    return 'availability'
  }
  if (normalized.includes('re-intro') || normalized.includes('6 months')) {
    return 'reintro'
  }
  if (normalized.includes('introduc')) {
    return 'intro'
  }

  return 'hotlist'
}

export function generateAiSubjectLine() {
  return '🔥 Senior Java Developer | C2C | Immediate | Dallas TX | H1B | $85-90/hr'
}

const MERGE_TAG_PATTERN = /\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g

const DEFAULT_MERGE_CONTEXT = {
  recruiter_name: 'Sarah Mitchell',
  candidate_name: 'John Smith',
  skills: 'Java, Spring Boot, AWS, Microservices',
  location: 'Dallas, TX',
  rate: '$85/hr C2C',
  availability: 'Immediate',
  visa_status: 'H1B',
  company_name: 'TEKsystems',
  experience: '8',
  job_title: 'Senior Java Developer',
}

export const TEMPLATE_CATEGORY_STYLES = {
  Hotlist: { bg: '#fef3c7', text: '#92400e' },
  Bench: { bg: '#dbeafe', text: '#1e40af' },
  'Follow-up': { bg: '#ede9fe', text: '#5b21b6' },
  Urgent: { bg: '#fee2e2', text: '#991b1b' },
  General: { bg: '#f3f4f6', text: '#374151' },
}

export function templateCategoryStyle(category) {
  return TEMPLATE_CATEGORY_STYLES[category] ?? TEMPLATE_CATEGORY_STYLES.General
}

export function applyMergeTags(text, context = {}) {
  if (!text) {
    return ''
  }
  const merged = { ...DEFAULT_MERGE_CONTEXT, ...context }
  return text.replace(MERGE_TAG_PATTERN, (match, key) => merged[key] ?? match)
}

export function buildLocalTemplatePreview(template, composer = {}) {
  const context = {
    recruiter_name: composer.fromName || DEFAULT_MERGE_CONTEXT.recruiter_name,
    company_name: 'TEKsystems',
  }
  const subject = applyMergeTags(template.subject, context)
  const body = applyMergeTags(template.body, context)
  return {
    subject,
    body,
    recipientCount: 1,
    previewHtml: `<div class="template-preview-subject"><strong>Subject:</strong> ${subject}</div><hr class="template-preview-divider" /><div class="template-preview-content">${body}</div>`,
  }
}

export function mergeCampaignSettings(settings) {
  return {
    smtpHost: 'smtp.office365.com',
    smtpPort: 587,
    smtpUsername: '',
    smtpPassword: '',
    senderLimit: 600,
    emailDelaySeconds: 3,
    smartWarmup: true,
    unsubscribeFooter: true,
    honorUnsubscribes: true,
    bounceManagement: true,
    spamGuard: true,
    gmailSync: true,
    outlookSync: false,
    sendgridSync: false,
    openTracking: true,
    aiSubjectAssist: true,
    aiProvider: 'ollama',
    aiDefaultTone: 'professional',
    aiPersonalization: true,
    ...settings,
  }
}

function resolveContactColumns(headerRow) {
  const cells = headerRow.map((cell) => String(cell ?? '').trim().toLowerCase())
  const emailCol = cells.findIndex((cell) => cell.includes('email'))
  const nameCol = cells.findIndex((cell) => cell === 'name' || cell.includes('contact'))
  const companyCol = cells.findIndex((cell) => cell.includes('company') || cell.includes('organization'))
  const titleCol = cells.findIndex((cell) => cell.includes('title') || cell.includes('role'))
  const tagsCol = cells.findIndex((cell) => cell.includes('tag') || cell.includes('list'))

  return {
    emailCol: emailCol >= 0 ? emailCol : 0,
    nameCol: nameCol >= 0 ? nameCol : 1,
    companyCol: companyCol >= 0 ? companyCol : 2,
    titleCol: titleCol >= 0 ? titleCol : 3,
    tagsCol: tagsCol >= 0 ? tagsCol : 4,
  }
}

function parseContactMatrixRow(line, columns) {
  if (!Array.isArray(line) || !line.length) {
    return null
  }

  const cells = line.map((cell) => String(cell ?? '').trim())
  const email = cells[columns.emailCol] ?? cells.find((cell) => isEmail(cell)) ?? ''
  if (!isEmail(email)) {
    return null
  }

  let name = cells[columns.nameCol] ?? ''
  if (!name || name.includes('@')) {
    const local = email.split('@')[0].replace(/[._-]+/g, ' ')
    name = local
      .split(' ')
      .filter(Boolean)
      .map((part) => part[0].toUpperCase() + part.slice(1))
      .join(' ')
  }

  const company = cells[columns.companyCol] || email.split('@')[1] || 'Contact'
  const title = cells[columns.titleCol] || 'Contact'
  const list = cells[columns.tagsCol] || 'Imported'

  return {
    name,
    email,
    company,
    title,
    list,
    status: 'Queued',
  }
}

function parseContactMatrix(matrix) {
  if (!Array.isArray(matrix) || !matrix.length) {
    return []
  }

  let startIndex = 0
  let columns = resolveContactColumns([])

  for (let index = 0; index < Math.min(matrix.length, 8); index += 1) {
    const row = matrix[index]
    if (!Array.isArray(row)) {
      continue
    }
    const headerCells = row.map((cell) => String(cell ?? '').trim().toLowerCase())
    if (headerCells.some((cell) => cell.includes('email') || cell.includes('name') || cell.includes('company'))) {
      columns = resolveContactColumns(row)
      startIndex = index + 1
      break
    }
  }

  const rows = []
  const seen = new Set()

  for (let index = startIndex; index < matrix.length; index += 1) {
    const parsed = parseContactMatrixRow(matrix[index], columns)
    if (!parsed) {
      continue
    }
    const key = parsed.email.toLowerCase()
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    rows.push(parsed)
  }

  return rows
}

function parseContactText(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean)
  if (!lines.length) {
    return []
  }

  const rows = []
  const header = lines[0].toLowerCase()
  const startIndex = header.includes('email') ? 1 : 0

  for (const line of lines.slice(startIndex)) {
    const parts = line.includes('\t')
      ? line.split('\t').map((item) => item.trim())
      : line.split(',').map((item) => item.trim().replace(/^"|"$/g, ''))

    const email = parts.find((part) => isEmail(part)) ?? parts[0]
    if (!isEmail(email)) {
      continue
    }

    const name = parts.find((part) => part && !part.includes('@') && part !== email) ?? email.split('@')[0]
    const company = parts.find((part) => part && part !== name && part !== email && !isEmail(part)) ?? email.split('@')[1]

    rows.push({
      name: name.replace(/[._-]+/g, ' '),
      email,
      company,
      title: 'Contact',
      list: 'Imported',
      status: 'Queued',
    })
  }

  return rows
}

export async function parseContactSpreadsheetFile(file) {
  if (!file) {
    return []
  }

  const lowered = file.name.toLowerCase()
  if (lowered.endsWith('.xlsx') || lowered.endsWith('.xls')) {
    const XLSX = await import('xlsx')
    const buffer = await file.arrayBuffer()
    const workbook = XLSX.read(buffer, { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    const matrix = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })
    return parseContactMatrix(matrix)
  }

  const text = await file.text()
  return parseContactText(text)
}

export function parsePastedEmailList(raw) {
  const emails = String(raw ?? '')
    .split(/[\n,;]+/)
    .map((item) => item.trim())
    .filter((item) => isEmail(item))

  return emails.map((email) => {
    const local = email.split('@')[0].replace(/[._-]+/g, ' ')
    const name = local
      .split(' ')
      .filter(Boolean)
      .map((part) => part[0].toUpperCase() + part.slice(1))
      .join(' ')

    return {
      name: name || local,
      email,
      company: email.split('@')[1],
      title: 'Contact',
      list: 'Pasted',
      status: 'Queued',
    }
  })
}

export function downloadContactImportTemplate() {
  const header = 'Email,Name,Company,Title,Tags'
  const sample = 'recruiter@vendor.com,Jane Recruiter,VendorCo,Sr Recruiter,Priority Accounts'
  const blob = new Blob([`${header}\n${sample}\n`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'campaign-contacts-template.csv'
  anchor.click()
  URL.revokeObjectURL(url)
}

export function insertEditorTableHtml() {
  return '<table style="border-collapse:collapse;width:100%"><tr><td style="border:1px solid #d1d5db;padding:6px">Cell 1</td><td style="border:1px solid #d1d5db;padding:6px">Cell 2</td></tr><tr><td style="border:1px solid #d1d5db;padding:6px">Cell 3</td><td style="border:1px solid #d1d5db;padding:6px">Cell 4</td></tr></table>'
}
