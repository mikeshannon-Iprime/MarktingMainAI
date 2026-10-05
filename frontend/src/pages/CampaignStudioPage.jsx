import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  CalendarClock,
  Check,
  Copy,
  Download,
  Eraser,
  Eye,
  Mail,
  Plus,
  Send,
  Settings2,
  Shield,
  Sparkles,
  TrendingUp,
  Users,
  Wand2,
} from 'lucide-react'

import {
  createCampaignList,
  importCampaignContacts,
  launchCampaign,
  previewCampaign,
  previewCampaignTemplate,
  saveCampaignDraft,
  saveCampaignSettings,
  sendCampaignTest,
  testCampaignSmtp,
} from '../api/client'
import {
  AI_EMAIL_HTML,
  AI_GENERATION_STEPS,
  AI_PROMPTS,
  applyAiToneAndLength,
  avatarColorForIndex,
  buildLocalTemplatePreview,
  buildCampaignAnalytics,
  downloadContactImportTemplate,
  generateAiSubjectLine,
  insertEditorTableHtml,
  LIST_COLORS,
  mergeCampaignSettings,
  parseContactSpreadsheetFile,
  parsePastedEmailList,
  pickAiEmailKey,
  SENDING_SPEED_OPTIONS,
  SMTP_PORT_OPTIONS,
  templateCategoryStyle,
  updateLiveMetrics,
} from '../utils/campaignHelpers'
import { isEmail, isNonEmpty, pickFirstError, validateSmtpSettings } from '../utils/validators'
import './CampaignStudio.css'

const tabs = [
  { key: 'compose', label: 'Compose', icon: Mail },
  { key: 'contacts', label: 'Contacts', icon: Users, badgeKey: 'contacts' },
  { key: 'campaigns', label: 'Campaigns', icon: Send, badgeKey: 'campaigns' },
  { key: 'templates', label: 'Templates', icon: Copy, badgeKey: 'templates' },
  { key: 'settings', label: 'Settings', icon: Settings2 },
]

function CampaignToastStack({ toasts }) {
  if (!toasts.length) {
    return null
  }

  return (
    <div className="campaign-toast-stack">
      {toasts.map((toast) => (
        <div key={toast.id} className={`campaign-toast ${toast.tone}`}>{toast.message}</div>
      ))}
    </div>
  )
}

function ToggleRow({ label, hint, checked, onToggle }) {
  return (
    <button type="button" className="toggle-row toggle-button" onClick={onToggle}>
      <div>
        <strong>{label}</strong>
        <p>{hint}</p>
      </div>
      <span className={`toggle-indicator${checked ? ' active' : ''}`} />
    </button>
  )
}

function initials(name) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
}

function statusClass(status) {
  const key = status.toLowerCase()

  if (key === 'opened') {
    return 'opened'
  }

  if (key === 'bounced') {
    return 'bounced'
  }

  if (key === 'sent') {
    return 'sent'
  }

  return 'queued'
}

function AnimatedNumber({ value, duration = 700 }) {
  const numericValue = Number(value) || 0
  const previousValue = useRef(numericValue)
  const [displayValue, setDisplayValue] = useState(numericValue)

  useEffect(() => {
    const startValue = previousValue.current
    previousValue.current = numericValue

    if (startValue === numericValue || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      setDisplayValue(numericValue)
      return undefined
    }

    const startedAt = performance.now()
    let frameId
    const renderFrame = (now) => {
      const progress = Math.min(1, (now - startedAt) / duration)
      const eased = 1 - ((1 - progress) ** 3)
      setDisplayValue(Math.round(startValue + ((numericValue - startValue) * eased)))
      if (progress < 1) {
        frameId = window.requestAnimationFrame(renderFrame)
      }
    }

    frameId = window.requestAnimationFrame(renderFrame)
    return () => window.cancelAnimationFrame(frameId)
  }, [duration, numericValue])

  return displayValue.toLocaleString()
}

export function CampaignStudioPage({ workspace, currentUser, onRefresh }) {
  const [activeTab, setActiveTab] = useState('compose')
  const [composer, setComposer] = useState(null)
  const [contacts, setContacts] = useState([])
  const [lists, setLists] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [settings, setSettings] = useState(null)
  const [activeTemplate, setActiveTemplate] = useState(null)
  const [templates, setTemplates] = useState([])
  const [templatePreview, setTemplatePreview] = useState(null)
  const [templatePreviewBusy, setTemplatePreviewBusy] = useState(false)
  const [selectedContacts, setSelectedContacts] = useState(new Set())
  const [attachments, setAttachments] = useState([])
  const [message, setMessage] = useState({ tone: 'success', text: '' })
  const [previewResult, setPreviewResult] = useState(null)
  const [schedulerOpen, setSchedulerOpen] = useState(false)
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiTone, setAiTone] = useState('professional')
  const [aiLength, setAiLength] = useState('medium')
  const [aiBusy, setAiBusy] = useState(false)
  const [aiStatus, setAiStatus] = useState('')
  const [activePresetLabel, setActivePresetLabel] = useState('')
  const [contactFilter, setContactFilter] = useState('')
  const [contactListFilter, setContactListFilter] = useState('')
  const [dirSearch, setDirSearch] = useState('')
  const [pasteEmails, setPasteEmails] = useState('')
  const [importStatus, setImportStatus] = useState('')
  const [contactImportStatus, setContactImportStatus] = useState('')
  const [viewCampaign, setViewCampaign] = useState(null)
  const [analyticsCampaign, setAnalyticsCampaign] = useState(null)
  const [liveMetrics, setLiveMetrics] = useState(null)
  const [toasts, setToasts] = useState([])
  const [showComposePreview, setShowComposePreview] = useState(false)
  const [campaignFilter, setCampaignFilter] = useState('all')
  const [campaignSearch, setCampaignSearch] = useState('')
  const [scheduleModel, setScheduleModel] = useState({
    sendDate: new Date(Date.now() + 86400000).toISOString().slice(0, 10),
    sendTime: '09:00',
    sendNow: false,
    openTracking: true,
    autoFollowup: true,
    sendingSpeed: '100',
  })
  const [settingsBusy, setSettingsBusy] = useState(false)
  const [actionBusy, setActionBusy] = useState('')

  const editorRef = useRef(null)
  const isReadOnly = currentUser?.role === 'user'

  useEffect(() => {
    if (!workspace) {
      return
    }

    setComposer(workspace.composer)
    setContacts(workspace.contacts)
    setLists(workspace.lists)
    setCampaigns(workspace.campaigns)
    setTemplates(workspace.templates ?? [])
    setSettings(mergeCampaignSettings(workspace.settings))
    setLiveMetrics(workspace.metrics)
    const firstTemplate = workspace.templates?.[0] ?? null
    setActiveTemplate(firstTemplate)
    setSelectedContacts(new Set(workspace.contacts.slice(0, 2).map((contact) => contact.email)))
    const firstPrompt = workspace.composer.aiPrompts?.[0] ?? 'Hotlist blast'
    setAiPrompt(AI_PROMPTS[firstPrompt] ?? AI_PROMPTS['Hotlist blast'])
    setActivePresetLabel(firstPrompt)
  }, [workspace])

  useEffect(() => {
    if (editorRef.current && composer && editorRef.current.innerHTML !== composer.body) {
      editorRef.current.innerHTML = composer.body
    }
  }, [composer])

  useEffect(() => {
    if (!workspace?.templates?.length || !composer || composer.body?.length > 20) {
      return
    }
    const firstTemplate = workspace.templates[0]
    if (firstTemplate && editorRef.current && !editorRef.current.innerHTML.trim()) {
      editorRef.current.innerHTML = firstTemplate.body
      setComposer((current) => ({
        ...current,
        subject: firstTemplate.subject,
        body: firstTemplate.body,
      }))
    }
  }, [workspace, composer])

  const setField = (field, value) => {
    setComposer((current) => ({ ...current, [field]: value }))
  }

  const pushMessage = (text, tone = 'success') => {
    setMessage({ text, tone })
    const id = `${Date.now()}-${Math.random()}`
    setToasts((current) => [...current, { id, message: text, tone: tone === 'error' ? 'error' : tone === 'purple' ? 'purple' : 'success' }])
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id))
    }, 3000)
  }

  const ensureCanModify = (actionLabel) => {
    if (!isReadOnly) {
      return true
    }
    pushMessage(`You have view-only access. ${actionLabel} requires admin access.`, 'error')
    return false
  }

  const validateComposerContent = () => {
    if (!isNonEmpty(composer.campaignName, 3)) {
      pushMessage('Campaign name must be at least 3 characters.', 'error')
      return false
    }

    if (!isEmail(composer.replyTo) || !isEmail(composer.fromEmail)) {
      pushMessage('Reply-to and From email must be valid email addresses.', 'error')
      return false
    }

    if (!isNonEmpty(composer.fromName, 2)) {
      pushMessage('From name is required.', 'error')
      return false
    }

    if (!isNonEmpty(composer.subject, 3)) {
      pushMessage('Subject line must be at least 3 characters.', 'error')
      return false
    }

    if (!isNonEmpty(composer.body, 10)) {
      pushMessage('Email body must be at least 10 characters.', 'error')
      return false
    }

    return true
  }

  const validateComposerForSend = () => {
    if (!validateComposerContent()) {
      return false
    }

    if (!scheduleModel.sendNow) {
      if (!scheduleModel.sendDate || !scheduleModel.sendTime) {
        pushMessage('Select send date and time or enable send immediately.', 'error')
        return false
      }
    }

    return true
  }

  const execEditorCommand = (command, value = null) => {
    editorRef.current?.focus()
    document.execCommand(command, false, value)
    setField('body', editorRef.current?.innerHTML ?? composer.body)
  }

  const insertMergeTag = (tag) => {
    editorRef.current?.focus()
    document.execCommand('insertText', false, tag)
    setField('body', editorRef.current?.innerHTML ?? composer.body)
  }

  const insertMergeTagInSubject = (tag) => {
    setField('subject', `${composer.subject}${composer.subject ? ' ' : ''}${tag}`)
  }

  const filteredContacts = useMemo(() => {
    const text = contactFilter.trim().toLowerCase()

    return contacts.filter((contact) => {
      const matchesList = !contactListFilter || contactListFilter === 'all' || contact.list === contactListFilter
      const haystack = `${contact.name} ${contact.email} ${contact.company}`.toLowerCase()
      const matchesText = !text || haystack.includes(text)
      return matchesList && matchesText
    })
  }, [contacts, contactFilter, contactListFilter])

  const filteredCampaigns = useMemo(() => {
    const text = campaignSearch.trim().toLowerCase()

    return campaigns.filter((campaign) => {
      const matchesStatus = campaignFilter === 'all' || campaign.status.toLowerCase() === campaignFilter
      const matchesText = !text || campaign.name.toLowerCase().includes(text)
      return matchesStatus && matchesText
    })
  }, [campaignFilter, campaignSearch, campaigns])

  const filteredDirectoryContacts = useMemo(() => {
    const text = dirSearch.trim().toLowerCase()
    if (!text) {
      return contacts
    }
    return contacts.filter((contact) => (
      `${contact.name} ${contact.email} ${contact.company} ${contact.title ?? ''}`.toLowerCase().includes(text)
    ))
  }, [contacts, dirSearch])

  const aiPromptLabels = useMemo(() => {
    const fromWorkspace = composer?.aiPrompts ?? []
    const merged = [...fromWorkspace]
    ;['Rate negotiation', 'Availability update'].forEach((label) => {
      if (!merged.includes(label)) {
        merged.push(label)
      }
    })
    return merged
  }, [composer?.aiPrompts])

  const loadTemplatePreview = useCallback(async (template) => {
    if (!template) {
      setTemplatePreview(null)
      return
    }

    setTemplatePreviewBusy(true)
    try {
      const response = await previewCampaignTemplate({
        subject: template.subject,
        body: template.body,
        fromName: composer?.fromName ?? '',
        fromEmail: composer?.fromEmail ?? '',
        replyTo: composer?.replyTo ?? '',
      })
      setTemplatePreview(response)
    } catch {
      setTemplatePreview(buildLocalTemplatePreview(template, composer))
    } finally {
      setTemplatePreviewBusy(false)
    }
  }, [composer?.fromEmail, composer?.fromName, composer?.replyTo])

  useEffect(() => {
    if (activeTab === 'templates' && activeTemplate) {
      loadTemplatePreview(activeTemplate)
    }
  }, [activeTab, activeTemplate, loadTemplatePreview])

  if (!workspace || !composer || !settings) {
    return null
  }

  const toggleContact = (email) => {
    setSelectedContacts((current) => {
      const next = new Set(current)
      if (next.has(email)) {
        next.delete(email)
      } else {
        next.add(email)
      }
      return next
    })
  }

  const selectAllVisible = () => {
    setSelectedContacts((current) => {
      const next = new Set(current)
      filteredContacts.forEach((contact) => next.add(contact.email))
      return next
    })
  }

  const clearSelected = () => {
    setSelectedContacts(new Set())
  }

  const handleAttachmentChange = (event) => {
    if (!ensureCanModify('Attachment changes')) {
      event.target.value = ''
      return
    }

    const files = Array.from(event.target.files ?? [])

    if (!files.length) {
      return
    }

    const added = files.map((file) => ({
      id: `${file.name}-${file.size}-${Date.now()}`,
      name: file.name,
      kb: Math.max(1, Math.round(file.size / 1024)),
    }))

    setAttachments((current) => [...current, ...added])
    pushMessage(`${added.length} attachment(s) added.`)
    event.target.value = ''
  }

  const removeAttachment = (id) => {
    if (!ensureCanModify('Attachment removal')) {
      return
    }
    setAttachments((current) => current.filter((item) => item.id !== id))
  }

  const importContactsFromFile = async (file, statusSetter) => {
    const imported = await parseContactSpreadsheetFile(file)
    if (!imported.length) {
      pushMessage('No valid contacts found. Use columns: Email, Name, Company, Title, Tags.', 'error')
      return 0
    }

    try {
      const response = await importCampaignContacts({
        contacts: imported.map((item) => ({
          name: item.name,
          email: item.email,
          company: item.company,
          list: item.list || 'Imported',
          status: item.status || 'Queued',
        })),
        listName: imported[0]?.list || 'Imported',
      })

      setContacts((current) => {
        const seen = new Set(current.map((item) => item.email.toLowerCase()))
        const fresh = (response.contacts ?? imported).filter((item) => !seen.has(item.email.toLowerCase()))
        return [...fresh, ...current]
      })
      setSelectedContacts((current) => {
        const next = new Set(current)
        ;(response.contacts ?? imported).forEach((contact) => next.add(contact.email))
        return next
      })
      if (response.imported > 0) {
        setLists((current) => {
          const listName = imported[0]?.list || 'Imported'
          const existing = current.find((item) => item.name === listName)
          if (existing) {
            return current.map((item) =>
              item.name === listName ? { ...item, contacts: item.contacts + response.imported } : item,
            )
          }
          return [{ name: listName, contacts: response.imported, openRate: 0, replyRate: 0 }, ...current]
        })
      }
      const label = `${response.imported} imported${response.skipped ? `, ${response.skipped} skipped` : ''}`
      statusSetter(`Imported ${label} from ${file.name}`)
      pushMessage(`Imported ${label} from ${file.name}.`)
      onRefresh?.()
      return response.imported
    } catch {
      pushMessage('Contact import failed. Check file format and backend.', 'error')
      return 0
    }
  }

  const handleContactsImport = async (event) => {
    if (!ensureCanModify('Contact import')) {
      event.target.value = ''
      return
    }

    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    try {
      await importContactsFromFile(file, setImportStatus)
    } catch {
      pushMessage('Contact import failed. Check file format.', 'error')
    } finally {
      event.target.value = ''
    }
  }

  const handleContactsTabImport = async (event) => {
    if (!ensureCanModify('Contact import')) {
      event.target.value = ''
      return
    }

    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    try {
      await importContactsFromFile(file, setContactImportStatus)
    } catch {
      pushMessage('Contact import failed. Check file format.', 'error')
    } finally {
      event.target.value = ''
    }
  }

  const parsePastedEmails = async () => {
    if (!ensureCanModify('Pasted email import')) {
      return
    }

    const generated = parsePastedEmailList(pasteEmails)

    if (!generated.length) {
      pushMessage('No valid emails found in pasted text.', 'error')
      return
    }

    try {
      const response = await importCampaignContacts({
        contacts: generated.map((item) => ({
          name: item.name,
          email: item.email,
          company: item.company,
          list: item.list || 'Pasted',
          status: item.status || 'Queued',
        })),
        listName: 'Pasted',
      })

      setContacts((current) => {
        const seen = new Set(current.map((item) => item.email.toLowerCase()))
        const fresh = (response.contacts ?? generated).filter((item) => !seen.has(item.email.toLowerCase()))
        return [...fresh, ...current]
      })
      setSelectedContacts((current) => {
        const next = new Set(current)
        ;(response.contacts ?? generated).forEach((contact) => next.add(contact.email))
        return next
      })
      setPasteEmails('')
      pushMessage(`${response.imported} email(s) added from pasted input.`)
      onRefresh?.()
    } catch {
      pushMessage('Failed to save pasted contacts to backend.', 'error')
    }
  }

  const applyPresetPrompt = (presetLabel) => {
    setActivePresetLabel(presetLabel)
    setAiPrompt(AI_PROMPTS[presetLabel] ?? '')
    pushMessage(`${presetLabel} prompt loaded.`)
  }

  const generateAI = () => {
    if (!aiPrompt.trim()) {
      pushMessage('Enter a prompt or choose a quick prompt first.', 'error')
      return
    }

    setAiBusy(true)
    setAiStatus(AI_GENERATION_STEPS[0])
    const currentTone = aiTone
    const currentLength = aiLength

    let step = 0
    const interval = window.setInterval(() => {
      step += 1
      setAiStatus(AI_GENERATION_STEPS[step] ?? 'Finalizing...')
      if (step >= AI_GENERATION_STEPS.length) {
        window.clearInterval(interval)
        const key = pickAiEmailKey(aiPrompt, activePresetLabel)
        let generatedBody = AI_EMAIL_HTML[key] ?? AI_EMAIL_HTML.hotlist
        generatedBody = applyAiToneAndLength(generatedBody, currentTone, currentLength)
        setField('body', generatedBody)
        if (editorRef.current) {
          editorRef.current.innerHTML = generatedBody
        }
        if (!composer.subject.trim() || settings.aiSubjectAssist) {
          setField('subject', generateAiSubjectLine())
        }
        setAiBusy(false)
        setAiStatus('')
        pushMessage('AI email drafted successfully!', 'purple')
      }
    }, 600)
  }

  const improveDraft = () => {
    if (!composer.body.trim()) {
      pushMessage('No draft body available to improve.', 'error')
      return
    }

    setAiBusy(true)
    setAiStatus('Improving your email...')
    window.setTimeout(() => {
      const improved = `${composer.body}<p><em>PS: Happy to share references and schedule interviews this week.</em></p>`
      setField('body', improved)
      if (editorRef.current) {
        editorRef.current.innerHTML = improved
      }
      setAiBusy(false)
      setAiStatus('')
      pushMessage('Email improved by AI!', 'success')
    }, 1800)
  }

  const translateDraft = () => {
    const language = window.prompt('Translate to language', 'Spanish')
    if (!language) {
      return
    }
    setAiBusy(true)
    setAiStatus(`Translating to ${language}...`)
    window.setTimeout(() => {
      setAiBusy(false)
      setAiStatus('')
      pushMessage(`Email translated to ${language}!`, 'success')
    }, 1600)
  }

  const generateAiSubject = () => {
    setAiBusy(true)
    setAiStatus('Generating subject line...')
    window.setTimeout(() => {
      setField('subject', generateAiSubjectLine())
      setAiBusy(false)
      setAiStatus('')
      pushMessage('Subject line generated!', 'success')
    }, 1200)
  }

  const clearEditorBody = () => {
    if (!window.confirm('Clear email body?')) {
      return
    }
    setField('body', '')
    if (editorRef.current) {
      editorRef.current.innerHTML = ''
    }
  }

  const copyEditorBody = async () => {
    const text = editorRef.current?.innerText ?? ''
    if (!text.trim()) {
      pushMessage('Nothing to copy in email body.', 'error')
      return
    }
    try {
      await navigator.clipboard.writeText(text)
      pushMessage('Email body copied to clipboard.')
    } catch {
      pushMessage('Copy failed in this browser.', 'error')
    }
  }

  const insertEditorTable = () => {
    editorRef.current?.focus()
    document.execCommand('insertHTML', false, insertEditorTableHtml())
    setField('body', editorRef.current?.innerHTML ?? composer.body)
  }

  const insertStyledDivider = () => {
    editorRef.current?.focus()
    document.execCommand(
      'insertHTML',
      false,
      '<hr style="border:0;border-top:1px solid #d1d5db;margin:16px 0;" />',
    )
    setField('body', editorRef.current?.innerHTML ?? composer.body)
  }

  const duplicateCampaign = (campaign) => {
    setComposer((current) => ({
      ...current,
      campaignName: `${campaign.name} (Copy)`,
      subject: campaign.subject ?? current.subject,
      body: campaign.body ?? current.body,
    }))
    if (campaign.body && editorRef.current) {
      editorRef.current.innerHTML = campaign.body
    }
    setActiveTab('compose')
    setSchedulerOpen(true)
    pushMessage(`Duplicated "${campaign.name}" into composer.`)
  }

  const openCampaignForSend = (campaign) => {
    setComposer((current) => ({
      ...current,
      campaignName: campaign.name,
      subject: campaign.subject ?? current.subject,
      body: campaign.body ?? current.body,
    }))
    if (campaign.body && editorRef.current) {
      editorRef.current.innerHTML = campaign.body
    }
    setActiveTab('compose')
    setSchedulerOpen(true)
    pushMessage(`Ready to send "${campaign.name}". Select recipients and launch.`)
  }

  const previewEmail = async () => {
    if (!validateComposerContent()) {
      return
    }

    setActionBusy('preview')
    try {
      const response = await previewCampaign({
        subject: composer.subject,
        body: composer.body,
        recipients: Array.from(selectedContacts),
      })
      setPreviewResult(response)
      setShowComposePreview(true)
      pushMessage('Preview generated from backend endpoint.')
    } catch {
      const fallback = buildLocalTemplatePreview(
        { subject: composer.subject, body: composer.body },
        composer,
      )
      setPreviewResult({ ...fallback, recipientCount: selectedContacts.size })
      setShowComposePreview(true)
      pushMessage('Backend preview unavailable — showing a local preview.', 'info')
    } finally {
      setActionBusy('')
    }
  }

  const sendTestEmail = async () => {
    if (!ensureCanModify('Test send')) {
      return
    }

    if (!validateComposerContent()) {
      return
    }

    const email = window.prompt('Send test email to', composer.replyTo)

    if (!email) {
      return
    }

    if (!isEmail(email)) {
      pushMessage('Enter a valid test email address.', 'error')
      return
    }

    setActionBusy('test')
    try {
      const response = await sendCampaignTest({
        email,
        subject: composer.subject,
        body: composer.body,
        fromName: composer.fromName,
        fromEmail: composer.fromEmail,
        replyTo: composer.replyTo,
      })
      pushMessage(response.message)
    } catch {
      pushMessage('Test send failed. Verify backend availability.', 'error')
    } finally {
      setActionBusy('')
    }
  }

  const saveDraft = async () => {
    if (!ensureCanModify('Save draft')) {
      return
    }

    if (!validateComposerContent()) {
      return
    }

    setActionBusy('draft')
    try {
      const response = await saveCampaignDraft({
        campaignName: composer.campaignName,
        subject: composer.subject,
        body: composer.body,
        fromName: composer.fromName,
        fromEmail: composer.fromEmail,
        replyTo: composer.replyTo,
      })

      const draft = response.campaign ?? {
        name: composer.campaignName,
        sent: 0,
        opened: 0,
        replied: 0,
        status: 'Draft',
        scheduledFor: '—',
        subject: composer.subject,
        body: composer.body,
      }

      setCampaigns((current) => {
        const withoutExisting = current.filter((item) => !(item.name === draft.name && item.status === 'Draft'))
        return [draft, ...withoutExisting]
      })
      pushMessage(response.message ?? `Campaign "${composer.campaignName}" saved as draft.`)
      onRefresh?.()
    } catch {
      pushMessage('Draft save failed. Verify backend availability.', 'error')
    } finally {
      setActionBusy('')
    }
  }

  const launchCampaignAction = async () => {
    if (!ensureCanModify('Campaign launch')) {
      return
    }

    if (!validateComposerForSend()) {
      return
    }

    const recipients = Array.from(selectedContacts)

    if (!recipients.length) {
      pushMessage('Select at least one recipient before launch.', 'error')
      return
    }

    setActionBusy('launch')

    try {
      const scheduledFor = `${scheduleModel.sendDate} ${scheduleModel.sendTime}`
      const response = await launchCampaign({
        campaignName: composer.campaignName,
        subject: composer.subject,
        body: composer.body,
        recipients,
        scheduledFor,
        sendNow: scheduleModel.sendNow,
        fromName: composer.fromName,
        fromEmail: composer.fromEmail,
        replyTo: composer.replyTo,
        openTracking: scheduleModel.openTracking,
        autoFollowup: scheduleModel.autoFollowup,
        sendingSpeed: scheduleModel.sendingSpeed,
        emailDelaySeconds: settings.emailDelaySeconds ?? 3,
        listName: contactListFilter && contactListFilter !== 'all' ? contactListFilter : '',
      })

      const fresh = response.campaign ?? {
        name: composer.campaignName,
        sent: response.sentCount ?? recipients.length,
        opened: Math.max(0, Math.round((response.sentCount ?? recipients.length) * 0.38)),
        replied: Math.max(0, Math.round((response.sentCount ?? recipients.length) * 0.12)),
        status: scheduleModel.sendNow ? 'Sent' : 'Scheduled',
        scheduledFor,
        subject: composer.subject,
        body: composer.body,
      }

      setCampaigns((current) => [fresh, ...current])
      if (scheduleModel.sendNow) {
        setLiveMetrics((current) => updateLiveMetrics(current ?? workspace.metrics, fresh.sent))
      }
      setSchedulerOpen(false)
      pushMessage(response.message)
      onRefresh?.()
    } catch {
      pushMessage('Launch failed. Verify backend availability.', 'error')
    } finally {
      setActionBusy('')
    }
  }

  const createList = async () => {
    if (!ensureCanModify('List creation')) {
      return
    }

    const name = window.prompt('New list name', 'New Contact List')

    if (!name?.trim()) {
      return
    }

    if (!isNonEmpty(name, 2)) {
      pushMessage('List name must be at least 2 characters.', 'error')
      return
    }

    setActionBusy('newList')
    try {
      const response = await createCampaignList(name.trim())
      setLists((current) => [response, ...current])
      pushMessage(`List "${response.name}" created.`)
    } catch {
      pushMessage('Create list failed. Verify backend availability.', 'error')
    } finally {
      setActionBusy('')
    }
  }

  const selectTemplate = (template) => {
    setActiveTemplate(template)
  }

  const applyTemplate = (template, { skipConfirm = false } = {}) => {
    if (!ensureCanModify('Template apply')) {
      return
    }

    const plainBody = (composer?.body ?? '').replace(/<[^>]+>/g, '').trim()
    if (!skipConfirm && plainBody.length > 20) {
      const confirmed = window.confirm(`Replace current composer content with "${template.name}"?`)
      if (!confirmed) {
        return
      }
    }

    setActiveTemplate(template)
    setComposer((current) => ({
      ...current,
      campaignName: current.campaignName?.includes('May Talent Pulse')
        ? template.name
        : (current.campaignName || template.name),
      subject: template.subject,
      body: template.body,
    }))
    if (editorRef.current) {
      editorRef.current.innerHTML = template.body
    }
    setActiveTab('compose')
    pushMessage(`Template "${template.name}" loaded into composer.`)
  }

  const handleContactListChange = (value) => {
    setContactListFilter(value)
    if (!value) {
      return
    }

    const pool = value === 'all'
      ? contacts
      : contacts.filter((contact) => contact.list === value)

    setSelectedContacts((current) => {
      const next = new Set(current)
      pool.forEach((contact) => next.add(contact.email))
      return next
    })
    if (pool.length) {
      pushMessage(`Loaded ${pool.length} contact(s) from ${value === 'all' ? 'all lists' : value}.`)
    }
  }

  const quickEmailContact = (contact) => {
    setComposer((current) => ({
      ...current,
      campaignName: `Direct outreach — ${contact.name}`,
      subject: `Following up — {{candidate_name}} | ${contact.company}`,
    }))
    setSelectedContacts(new Set([contact.email]))
    setActiveTab('compose')
    pushMessage(`Prepared direct outreach to ${contact.name}.`)
  }

  const openSchedulerPanel = () => {
    setSchedulerOpen(true)
    if (!scheduleModel.sendDate) {
      setScheduleModel((current) => ({
        ...current,
        sendDate: new Date(Date.now() + 86400000).toISOString().slice(0, 10),
      }))
    }
  }

  const tabBadgeCount = (key) => {
    if (key === 'contacts') {
      return contacts.length
    }
    if (key === 'campaigns') {
      return campaigns.length
    }
    if (key === 'templates') {
      return templates.length
    }
    return 0
  }

  const metrics = liveMetrics ?? workspace.metrics

  const testSmtpConnection = async () => {
    if (!ensureCanModify('SMTP test')) {
      return
    }

    const validation = validateSmtpSettings(settings)
    if (!validation.isValid) {
      pushMessage(pickFirstError(validation.errors), 'error')
      return
    }

    setSettingsBusy(true)
    try {
      const response = await testCampaignSmtp(settings)
      pushMessage(response.message, response.success ? 'success' : 'error')
    } catch {
      pushMessage('SMTP test failed. Verify backend availability.', 'error')
    } finally {
      setSettingsBusy(false)
    }
  }

  const saveSettingsAction = async () => {
    if (!ensureCanModify('Settings updates')) {
      return
    }

    const validation = validateSmtpSettings(settings)
    if (!validation.isValid) {
      pushMessage(pickFirstError(validation.errors), 'error')
      return
    }

    setSettingsBusy(true)
    try {
      const response = await saveCampaignSettings(settings)
      pushMessage(response.message)
    } catch {
      pushMessage('Settings save failed. Verify backend availability.', 'error')
    } finally {
      setSettingsBusy(false)
    }
  }

  return (
    <div className="page-stack campaign-studio-page">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Campaign Studio <span className="live-pill">● LIVE</span></p>
          <h3>Mass email campaigns with compose, contacts, templates, AI drafting, and launch APIs.</h3>
          <p className="hero-copy">Mass email drafting, templates, contact lists, scheduling, and compliance for staffing campaigns.</p>
        </div>
        <div className="hero-grid four-up">
          <div className="metric-tile accent-amber">
            <Mail size={18} />
            <strong><AnimatedNumber value={metrics.emailsSent} /></strong>
            <span>Emails sent</span>
          </div>
          <div className="metric-tile accent-teal">
            <TrendingUp size={18} />
            <strong>{metrics.openRate}%</strong>
            <span>Open rate</span>
          </div>
          <div className="metric-tile accent-cobalt">
            <Send size={18} />
            <strong>{metrics.replyRate}%</strong>
            <span>Reply rate</span>
          </div>
          <div className="metric-tile accent-rose">
            <AlertCircle size={18} />
            <strong>{metrics.bounceRate ?? 2}%</strong>
            <span>Bounce rate</span>
          </div>
        </div>
      </section>

      <div className="tab-strip wrap-tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const badge = tab.badgeKey ? tabBadgeCount(tab.badgeKey) : 0
          return (
            <button
              key={tab.key}
              type="button"
              className={`tab-button${activeTab === tab.key ? ' active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              <Icon size={15} />
              {tab.label}
              {badge ? <span className="tab-badge">{badge}</span> : null}
            </button>
          )
        })}
      </div>

      {message.text ? <div className={`banner ${message.tone}`}>{message.text}</div> : null}

      {activeTab === 'compose' ? (
        <section className="dual-grid align-start">
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Email composer</p>
                <h4>Campaign details and rich body editor</h4>
              </div>
            </div>

            <div className="form-grid two-columns">
              <label>Campaign name<input value={composer.campaignName} onChange={(event) => setField('campaignName', event.target.value)} /></label>
              <label>Reply-to<input value={composer.replyTo} onChange={(event) => setField('replyTo', event.target.value)} /></label>
              <label>From name<input value={composer.fromName} onChange={(event) => setField('fromName', event.target.value)} /></label>
              <label>From email<input value={composer.fromEmail} onChange={(event) => setField('fromEmail', event.target.value)} /></label>
            </div>

            <label>
              Subject line
              <div className="inline-form-row">
                <input value={composer.subject} onChange={(event) => setField('subject', event.target.value)} />
                <button className="secondary-button" type="button" disabled={aiBusy} onClick={generateAiSubject}>
                  <Sparkles size={16} />
                </button>
              </div>
            </label>

            <div>
              <label>Merge tags — click to insert in body or subject</label>
              <div className="chip-wrap inset">
                {composer.mergeTags.map((tag) => (
                  <span key={tag} className="chip-button-row">
                    <button type="button" className="chip-button" onClick={() => insertMergeTag(tag)} title="Insert in body">{tag}</button>
                    <button type="button" className="chip-button soft" onClick={() => insertMergeTagInSubject(tag)} title="Insert in subject">+S</button>
                  </span>
                ))}
              </div>
            </div>

            <div className="page-stack dense">
              <label>Email body</label>
              <div className="editor-toolbar">
                <button className="tb-btn" type="button" onClick={() => execEditorCommand('bold')}>B</button>
                <button className="tb-btn" type="button" onClick={() => execEditorCommand('italic')}><em>I</em></button>
                <button className="tb-btn" type="button" onClick={() => execEditorCommand('underline')}><u>U</u></button>
                <span className="tb-divider" />
                <button className="tb-btn" type="button" onClick={() => execEditorCommand('insertUnorderedList')}>• List</button>
                <button className="tb-btn" type="button" onClick={() => execEditorCommand('insertOrderedList')}>1. List</button>
                <span className="tb-divider" />
                <button className="tb-btn" type="button" onClick={() => {
                  const url = window.prompt('Enter URL', 'https://')
                  if (url) {
                    execEditorCommand('createLink', url)
                  }
                }}>Link</button>
                <button className="tb-btn" type="button" onClick={insertEditorTable}>Table</button>
                <button className="tb-btn" type="button" onClick={insertStyledDivider}>Rule</button>
                <span className="tb-divider" />
                <select
                  className="tb-select"
                  defaultValue=""
                  onChange={(event) => {
                    if (event.target.value) {
                      execEditorCommand('fontSize', event.target.value)
                      event.target.value = ''
                    }
                  }}
                >
                  <option value="">Size</option>
                  <option value="1">Small</option>
                  <option value="3">Normal</option>
                  <option value="5">Large</option>
                </select>
                <select
                  className="tb-select"
                  defaultValue=""
                  onChange={(event) => {
                    if (event.target.value) {
                      execEditorCommand('foreColor', event.target.value)
                      event.target.value = ''
                    }
                  }}
                >
                  <option value="">Color</option>
                  <option value="#1d4ed8">Blue</option>
                  <option value="#059669">Green</option>
                  <option value="#dc2626">Red</option>
                  <option value="#d97706">Amber</option>
                  <option value="#111827">Black</option>
                </select>
                <span className="tb-divider" />
                <button className="tb-btn" type="button" onClick={clearEditorBody} title="Clear"><Eraser size={14} /></button>
                <button className="tb-btn" type="button" onClick={copyEditorBody} title="Copy"><Copy size={14} /></button>
              </div>
              <div
                ref={editorRef}
                className="rich-area"
                contentEditable
                suppressContentEditableWarning
                onInput={(event) => setField('body', event.currentTarget.innerHTML)}
              />
            </div>

            <div className="attachment-dropzone compact-dropzone">
              <strong>Attachments</strong>
              <span>Attach hotlist, resume, or supporting files for this campaign.</span>
              <label className="secondary-button file-trigger">
                Add files
                <input type="file" multiple onChange={handleAttachmentChange} />
              </label>
              <div className="card-list compact-list">
                {attachments.map((item) => (
                  <div key={item.id} className="file-item-react">
                    <span>{item.name}</span>
                    <span>{item.kb} KB</span>
                    <button className="secondary-button" type="button" onClick={() => removeAttachment(item.id)}>Remove</button>
                  </div>
                ))}
              </div>
            </div>

            <div className="button-row wrap-actions">
              <button className="secondary-button" type="button" disabled={actionBusy === 'preview'} onClick={previewEmail}>
                <Eye size={16} />
                Preview
              </button>
              <button className="secondary-button" type="button" disabled={actionBusy === 'test'} onClick={sendTestEmail}>
                <Send size={16} />
                Send test
              </button>
              <button className="primary-button btn-warning" type="button" onClick={saveDraft}>Save draft</button>
              <button className="primary-button" type="button" onClick={openSchedulerPanel}>
                <CalendarClock size={16} />
                Schedule / send
              </button>
            </div>
          </article>

          <div className="page-stack dense">
            <article className="glass-card ai-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">AI email drafter</p>
                  <h4>Powered by local AI — prompt-based drafting</h4>
                </div>
                <Sparkles size={18} />
              </div>
              <div className="chip-wrap inset">
                {aiPromptLabels.map((prompt) => (
                  <button key={prompt} type="button" className="chip-button soft" onClick={() => applyPresetPrompt(prompt)}>{prompt}</button>
                ))}
              </div>
              <label>Describe what you want to send<textarea rows={4} value={aiPrompt} onChange={(event) => setAiPrompt(event.target.value)} /></label>
              <div className="form-grid two-columns compact-gap">
                <label>
                  Tone
                  <select value={aiTone} onChange={(event) => setAiTone(event.target.value)}>
                    <option value="professional">Professional</option>
                    <option value="concise">Concise & direct</option>
                    <option value="friendly">Friendly & warm</option>
                    <option value="urgent">Urgent</option>
                    <option value="formal">Formal</option>
                  </select>
                </label>
                <label>
                  Length
                  <select value={aiLength} onChange={(event) => setAiLength(event.target.value)}>
                    <option value="short">Short (3–4 lines)</option>
                    <option value="medium">Medium</option>
                    <option value="long">Detailed</option>
                  </select>
                </label>
              </div>
              {aiBusy && aiStatus ? (
                <div className="ai-generating">
                  <span className="ai-spinner" />
                  <span>{aiStatus}</span>
                </div>
              ) : null}
              <div className="button-row wrap-actions">
                <button className="primary-button btn-purple" type="button" disabled={aiBusy} onClick={generateAI}>
                  <Sparkles size={16} />
                  {aiBusy ? 'Generating...' : 'Generate with AI'}
                </button>
                <button className="secondary-button" type="button" disabled={aiBusy} onClick={improveDraft}>
                  <Wand2 size={16} />
                  Improve existing
                </button>
                <button className="secondary-button" type="button" disabled={aiBusy} onClick={translateDraft}>Translate</button>
              </div>
            </article>

            <article className="glass-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Recipients</p>
                  <h4>{selectedContacts.size} selected contacts</h4>
                </div>
              </div>
              <div className="form-grid two-columns compact-gap">
                <label>
                  Select contact list
                  <select value={contactListFilter} onChange={(event) => handleContactListChange(event.target.value)}>
                    <option value="">-- Select a list --</option>
                    <option value="all">All Contacts ({contacts.length})</option>
                    {lists.map((list) => (
                      <option key={list.name} value={list.name}>{list.name} ({list.contacts})</option>
                    ))}
                  </select>
                </label>
                <label>
                  Search
                  <input value={contactFilter} onChange={(event) => setContactFilter(event.target.value)} placeholder="Name, company, email" />
                </label>
              </div>
              <div className="button-row wrap-actions">
                <button className="secondary-button" type="button" onClick={selectAllVisible}>Select all</button>
                <button className="secondary-button" type="button" onClick={clearSelected}>Clear</button>
              </div>
              <div className="selection-list scrollable-recipients">
                {filteredContacts.map((contact) => (
                  <label key={contact.email} className="selection-row">
                    <input type="checkbox" checked={selectedContacts.has(contact.email)} onChange={() => toggleContact(contact.email)} />
                    <div className="contact-avatar-react">{initials(contact.name)}</div>
                    <div>
                      <strong>{contact.name}</strong>
                      <p>{contact.company} · {contact.email}</p>
                    </div>
                    <span className={`tiny-pill ${statusClass(contact.status)}`}>{contact.status}</span>
                  </label>
                ))}
              </div>

              <div className="attachment-dropzone compact-dropzone">
                <strong>Import contacts from Excel</strong>
                <span>Col A: Email · Col B: Name · Col C: Company · Col D: Title · Col E: Tags</span>
                <label className="secondary-button file-trigger">
                  Import file
                  <input type="file" accept=".xls,.xlsx,.csv" onChange={handleContactsImport} />
                </label>
                {importStatus ? <p className="import-status">{importStatus}</p> : null}
              </div>

              <div className="paste-emails-box">
                <label>Or paste emails (comma-separated)
                  <textarea
                    rows={2}
                    value={pasteEmails}
                    placeholder="john@company.com, jane@firm.com"
                    onChange={(event) => setPasteEmails(event.target.value)}
                  />
                </label>
                <button className="secondary-button" type="button" onClick={parsePastedEmails}>Add from paste</button>
              </div>
            </article>

            {schedulerOpen ? (
              <article className="glass-card">
                <div className="section-heading small-gap">
                  <div>
                    <p className="eyebrow">Schedule & send</p>
                    <h4>Launch controls</h4>
                  </div>
                </div>
                <div className="form-grid two-columns compact-gap">
                  <label>Send date<input type="date" value={scheduleModel.sendDate} onChange={(event) => setScheduleModel((current) => ({ ...current, sendDate: event.target.value }))} /></label>
                  <label>Send time<input type="time" value={scheduleModel.sendTime} onChange={(event) => setScheduleModel((current) => ({ ...current, sendTime: event.target.value }))} /></label>
                </div>
                <label>
                  Sending speed
                  <select value={scheduleModel.sendingSpeed} onChange={(event) => setScheduleModel((current) => ({ ...current, sendingSpeed: event.target.value }))}>
                    {SENDING_SPEED_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <ToggleRow
                  label="Send immediately"
                  hint="Ignore scheduled date/time and send now."
                  checked={scheduleModel.sendNow}
                  onToggle={() => setScheduleModel((current) => ({ ...current, sendNow: !current.sendNow }))}
                />
                <ToggleRow
                  label="Track opens and clicks"
                  hint="Enable engagement tracking for analytics."
                  checked={scheduleModel.openTracking}
                  onToggle={() => setScheduleModel((current) => ({ ...current, openTracking: !current.openTracking }))}
                />
                <ToggleRow
                  label="Auto follow-up if no reply"
                  hint="Send reminder after 3 days."
                  checked={scheduleModel.autoFollowup}
                  onToggle={() => setScheduleModel((current) => ({ ...current, autoFollowup: !current.autoFollowup }))}
                />
                <div className="button-row wrap-actions">
                  <button className="primary-button" type="button" disabled={actionBusy === 'launch'} onClick={launchCampaignAction}>
                    <Check size={16} />
                    Launch campaign
                  </button>
                  <button className="secondary-button" type="button" onClick={() => setSchedulerOpen(false)}>Cancel</button>
                </div>
              </article>
            ) : null}
          </div>
        </section>
      ) : null}

      {activeTab === 'compose' && showComposePreview && previewResult ? (
        <article className="glass-card preview-card compose-preview-wide">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Email preview</p>
              <h4>{previewResult.subject}</h4>
            </div>
            <button className="secondary-button" type="button" onClick={() => setShowComposePreview(false)}>Close</button>
          </div>
          <div className="preview-frame">
            <p className="preview-meta">From: <strong>{composer.fromName}</strong> &lt;{composer.fromEmail}&gt;</p>
            <p className="preview-meta">Subject: <strong>{previewResult.subject}</strong></p>
            <p className="support-copy">Recipients in preview: {previewResult.recipientCount}</p>
            <hr className="compose-preview-divider" />
            <div className="preview-body" dangerouslySetInnerHTML={{ __html: previewResult.previewHtml }} />
          </div>
        </article>
      ) : null}

      {activeTab === 'contacts' ? (
        <section className="dual-grid align-start">
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Import contacts</p>
                <h4>Excel / CSV upload</h4>
              </div>
            </div>
            <div className="attachment-dropzone">
              <strong>Upload Excel / CSV</strong>
              <span>Col A: Email · Col B: Name · Col C: Company · Col D: Title · Col E: Tags</span>
              <label className="secondary-button file-trigger">
                Choose file
                <input type="file" accept=".xls,.xlsx,.csv" onChange={handleContactsTabImport} />
              </label>
            </div>
            {contactImportStatus ? <p className="import-status">{contactImportStatus}</p> : null}
            <div className="button-row wrap-actions">
              <button className="secondary-button" type="button" onClick={downloadContactImportTemplate}>
                <Download size={16} />
                Download template
              </button>
            </div>

            <div className="section-heading small-gap" style={{ marginTop: '1rem' }}>
              <div>
                <p className="eyebrow">Contact lists</p>
                <h4>List inventory</h4>
              </div>
              <button className="primary-button" type="button" disabled={actionBusy === 'newList'} onClick={createList}>
                <Plus size={16} />
                New list
              </button>
            </div>
            <div className="card-list compact-list">
              <div className="list-summary-row">
                <span>
                  <span className="list-dot" style={{ background: LIST_COLORS[0] }} />
                  All Contacts
                </span>
                <strong>{contacts.length}</strong>
              </div>
              {lists.map((list, index) => (
                <div key={list.name} className="list-summary-row">
                  <span>
                    <span className="list-dot" style={{ background: LIST_COLORS[index % LIST_COLORS.length] }} />
                    {list.name}
                  </span>
                  <strong>{list.contacts}</strong>
                </div>
              ))}
            </div>
          </article>
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Directory</p>
                <h4>All campaign contacts</h4>
              </div>
            </div>
            <label>
              Search contacts
              <input value={dirSearch} onChange={(event) => setDirSearch(event.target.value)} placeholder="Search contacts..." />
            </label>
            <div className="directory-list">
              {filteredDirectoryContacts.map((contact, index) => {
                const colors = avatarColorForIndex(index)
                return (
                  <div key={contact.email} className="directory-row">
                    <div className="contact-avatar-react" style={{ background: colors.bg, color: colors.text }}>{initials(contact.name)}</div>
                    <div className="directory-meta">
                      <strong>{contact.name}</strong>
                      <p>{contact.email}</p>
                    </div>
                    <div className="directory-company">
                      <div>{contact.company}</div>
                      <div>{contact.title ?? 'Contact'}</div>
                    </div>
                    <button className="secondary-button" type="button" onClick={() => quickEmailContact(contact)}>
                      <Send size={14} />
                    </button>
                  </div>
                )
              })}
            </div>
          </article>
        </section>
      ) : null}

      {activeTab === 'campaigns' ? (
        <section className="page-stack dense">
          <article className="glass-card">
            <div className="form-grid campaign-filter-grid">
              <label>
                Status
                <select value={campaignFilter} onChange={(event) => setCampaignFilter(event.target.value)}>
                  <option value="all">All Campaigns</option>
                  <option value="sent">Sent</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="draft">Draft</option>
                </select>
              </label>
              <label>
                Search campaigns
                <input value={campaignSearch} onChange={(event) => setCampaignSearch(event.target.value)} placeholder="Campaign name" />
              </label>
              <div className="button-row">
                <button className="primary-button" type="button" onClick={() => setActiveTab('compose')}>
                  <Plus size={16} />
                  New campaign
                </button>
              </div>
            </div>
          </article>
          <section className="card-grid three-up">
            {filteredCampaigns.map((campaign) => {
              const openPct = campaign.sent > 0 ? Math.round((campaign.opened / campaign.sent) * 100) : 0
              const replyPct = campaign.sent > 0 ? Math.round((campaign.replied / campaign.sent) * 100) : 0
              const progress = campaign.sent > 0 ? Math.min(100, openPct) : 0
              const statusKey = campaign.status.toLowerCase()
              return (
                <article key={`${campaign.name}-${campaign.scheduledFor}`} className="glass-card campaign-card">
                  <div className="module-header">
                    <div>
                      <h4>{campaign.name}</h4>
                      <p>{campaign.scheduledFor} · {campaign.sent} sent · {openPct}% open · {replyPct}% reply</p>
                    </div>
                    <span className={`tiny-pill ${statusKey === 'sent' ? 'sent' : statusKey === 'scheduled' ? 'queued' : 'opened'}`}>{campaign.status}</span>
                  </div>
                  {campaign.sent > 0 ? <div className="progress-track"><div className="progress-fill" style={{ width: `${progress}%` }} /></div> : null}
                  <div className="mini-stats">
                    <span>{campaign.opened} opens</span>
                    <span>{campaign.replied} replies</span>
                  </div>
                  <div className="button-row wrap-actions">
                    <button className="secondary-button" type="button" onClick={() => {
                      setViewCampaign(campaign)
                      setAnalyticsCampaign(null)
                    }}>View</button>
                    {campaign.status !== 'Sent' ? (
                      <button className="primary-button" type="button" onClick={() => openCampaignForSend(campaign)}>Send</button>
                    ) : null}
                    <button className="secondary-button" type="button" onClick={() => duplicateCampaign(campaign)}>Duplicate</button>
                    <button className="secondary-button" type="button" onClick={() => {
                      setAnalyticsCampaign({ ...buildCampaignAnalytics(campaign), name: campaign.name })
                      setViewCampaign(null)
                    }}>Analytics</button>
                  </div>
                </article>
              )
            })}
          </section>

          {viewCampaign ? (
            <article className="glass-card preview-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Campaign detail</p>
                  <h4>{viewCampaign.name}</h4>
                </div>
                <button className="secondary-button" type="button" onClick={() => setViewCampaign(null)}>Close</button>
              </div>
              <p className="preview-meta">Status: <strong>{viewCampaign.status}</strong></p>
              <p className="preview-meta">Scheduled: <strong>{viewCampaign.scheduledFor}</strong></p>
              <p className="preview-meta">Sent: <strong>{viewCampaign.sent}</strong> · Opened: <strong>{viewCampaign.opened}</strong> · Replied: <strong>{viewCampaign.replied}</strong></p>
            </article>
          ) : null}

          {analyticsCampaign ? (
            <article className="glass-card preview-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Campaign analytics</p>
                  <h4>{analyticsCampaign.name ?? viewCampaign?.name ?? 'Campaign performance'}</h4>
                </div>
                <button className="secondary-button" type="button" onClick={() => setAnalyticsCampaign(null)}>Close</button>
              </div>
              <div className="analytics-grid">
                <div className="analytics-tile"><strong>{analyticsCampaign.sent}</strong><span>Sent</span></div>
                <div className="analytics-tile"><strong>{analyticsCampaign.openRate}%</strong><span>Open rate</span></div>
                <div className="analytics-tile"><strong>{analyticsCampaign.replyRate}%</strong><span>Reply rate</span></div>
                <div className="analytics-tile"><strong>{analyticsCampaign.clickRate}%</strong><span>Click rate</span></div>
                <div className="analytics-tile"><strong>{analyticsCampaign.bounceRate}%</strong><span>Bounce rate</span></div>
                <div className="analytics-tile"><strong>{analyticsCampaign.deliveryRate}%</strong><span>Delivery rate</span></div>
                <div className="analytics-tile"><strong>{analyticsCampaign.opened}</strong><span>Opens</span></div>
                <div className="analytics-tile"><strong>{analyticsCampaign.replied}</strong><span>Replies</span></div>
              </div>
              <p className="support-copy">Top list: {analyticsCampaign.topList} · Last activity: {analyticsCampaign.lastActivity}</p>
            </article>
          ) : null}
        </section>
      ) : null}

      {activeTab === 'templates' ? (
        <section className="dual-grid align-start template-library-grid">
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Template library</p>
                <h4>Preview and apply templates</h4>
                <p className="support-copy">{templates.length} reusable email templates with merge tags.</p>
              </div>
            </div>
            <div className="card-list compact-list template-list">
              {templates.map((template) => {
                const categoryStyle = templateCategoryStyle(template.category)
                const isSelected = activeTemplate?.name === template.name
                return (
                  <div
                    key={template.name}
                    className={`template-card list-card selectable${isSelected ? ' selected' : ''}`}
                  >
                    <button type="button" className="template-card-main" onClick={() => selectTemplate(template)}>
                      <div className="template-card-copy">
                        <div className="template-card-title-row">
                          <strong>{template.name}</strong>
                          <span
                            className="template-category-pill"
                            style={{ background: categoryStyle.bg, color: categoryStyle.text }}
                          >
                            {template.category}
                          </span>
                        </div>
                        <p>{template.description ?? template.category}</p>
                        <p className="support-copy template-subject-snippet">
                          Subject: {template.subject.slice(0, 72)}{template.subject.length > 72 ? '…' : ''}
                        </p>
                      </div>
                      <span className="metric-chip">Preview</span>
                    </button>
                    <button
                      className="secondary-button template-use-button"
                      type="button"
                      onClick={() => applyTemplate(template)}
                    >
                      Use
                    </button>
                  </div>
                )
              })}
            </div>
          </article>
          <article className={`glass-card preview-card template-preview-card${activeTemplate ? ' is-visible' : ''}`}>
            <div className="section-heading">
              <div>
                <p className="eyebrow">Template preview</p>
                <h4>{templatePreview?.subject ?? activeTemplate?.subject ?? 'Select a template'}</h4>
                {activeTemplate ? (
                  <p className="support-copy">{activeTemplate.description ?? activeTemplate.category}</p>
                ) : null}
              </div>
              {activeTemplate ? (
                <button className="primary-button" type="button" onClick={() => applyTemplate(activeTemplate)}>
                  Use this template
                </button>
              ) : null}
            </div>
            {templatePreviewBusy ? (
              <div className="template-preview-empty">Generating preview with sample merge tags…</div>
            ) : activeTemplate && templatePreview ? (
              <>
                <div className="template-preview-meta">
                  <span className="metric-chip">Sample merge preview</span>
                  <span className="support-copy">{templatePreview.recipientCount} sample recipient</span>
                </div>
                <div className="preview-body template-preview-body" dangerouslySetInnerHTML={{ __html: templatePreview.previewHtml }} />
              </>
            ) : (
              <div className="template-preview-empty">
                Select a template from the library to preview subject, body, and merge tag substitution.
              </div>
            )}
          </article>
        </section>
      ) : null}

      {activeTab === 'settings' ? (
        <section className="dual-grid align-start">
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">SMTP configuration</p>
                <h4>Delivery settings</h4>
              </div>
              <Shield size={18} />
            </div>
            <div className="form-grid two-columns">
              <label>SMTP host<input value={settings.smtpHost} onChange={(event) => setSettings((current) => ({ ...current, smtpHost: event.target.value }))} /></label>
              <label>
                SMTP port
                <select value={settings.smtpPort} onChange={(event) => setSettings((current) => ({ ...current, smtpPort: Number(event.target.value) }))}>
                  {SMTP_PORT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>Username<input value={settings.smtpUsername ?? ''} onChange={(event) => setSettings((current) => ({ ...current, smtpUsername: event.target.value }))} /></label>
              <label>Password / app password<input type="password" value={settings.smtpPassword ?? ''} onChange={(event) => setSettings((current) => ({ ...current, smtpPassword: event.target.value }))} /></label>
              <label>Daily send limit<input type="number" value={settings.senderLimit} onChange={(event) => setSettings((current) => ({ ...current, senderLimit: Number(event.target.value) }))} /></label>
              <label>Delay between emails (seconds)<input type="number" value={settings.emailDelaySeconds ?? 3} onChange={(event) => setSettings((current) => ({ ...current, emailDelaySeconds: Number(event.target.value) }))} /></label>
            </div>
            <div className="button-row wrap-actions">
              <button className="secondary-button" type="button" disabled={settingsBusy} onClick={testSmtpConnection}>{settingsBusy ? 'Testing...' : 'Test connection'}</button>
              <button className="primary-button" type="button" disabled={settingsBusy} onClick={saveSettingsAction}>{settingsBusy ? 'Saving...' : 'Save settings'}</button>
            </div>
          </article>

          <div className="page-stack dense">
            <article className="glass-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Email integrations</p>
                  <h4>Provider sync</h4>
                </div>
              </div>
              <ToggleRow label="Gmail / Google Workspace" hint="Mirror campaign activities in Gmail." checked={settings.gmailSync} onToggle={() => setSettings((current) => ({ ...current, gmailSync: !current.gmailSync }))} />
              <ToggleRow label="Microsoft Outlook / 365" hint="Mirror campaign activities in Outlook." checked={settings.outlookSync} onToggle={() => setSettings((current) => ({ ...current, outlookSync: !current.outlookSync }))} />
              <ToggleRow label="SendGrid API" hint="Route outbound mail through SendGrid." checked={settings.sendgridSync ?? false} onToggle={() => setSettings((current) => ({ ...current, sendgridSync: !current.sendgridSync }))} />
            </article>

            <article className="glass-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Compliance & safety</p>
                  <h4>Deliverability controls</h4>
                </div>
              </div>
              <ToggleRow label="Auto-add unsubscribe footer" hint="Append compliance footer to every send." checked={settings.unsubscribeFooter} onToggle={() => setSettings((current) => ({ ...current, unsubscribeFooter: !current.unsubscribeFooter }))} />
              <ToggleRow label="Honor unsubscribes" hint="Skip recipients who opted out." checked={settings.honorUnsubscribes ?? true} onToggle={() => setSettings((current) => ({ ...current, honorUnsubscribes: !current.honorUnsubscribes }))} />
              <ToggleRow label="Bounce management" hint="Auto-remove hard bounces from lists." checked={settings.bounceManagement ?? true} onToggle={() => setSettings((current) => ({ ...current, bounceManagement: !current.bounceManagement }))} />
              <ToggleRow label="Smart warmup" hint="Gradually increase send volume for reputation." checked={settings.smartWarmup ?? true} onToggle={() => setSettings((current) => ({ ...current, smartWarmup: !current.smartWarmup }))} />
              <ToggleRow label="Spam guard" hint="Protect deliverability with pacing controls." checked={settings.spamGuard} onToggle={() => setSettings((current) => ({ ...current, spamGuard: !current.spamGuard }))} />
              <ToggleRow label="Open tracking" hint="Track opens and clicks." checked={settings.openTracking} onToggle={() => setSettings((current) => ({ ...current, openTracking: !current.openTracking }))} />
            </article>

            <article className="glass-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">AI settings</p>
                  <h4>Drafting defaults</h4>
                </div>
              </div>
              <div className="form-grid two-columns compact-gap">
                <label>
                  AI provider
                  <select value={settings.aiProvider ?? 'ollama'} onChange={(event) => setSettings((current) => ({ ...current, aiProvider: event.target.value }))}>
                    <option value="ollama">Ollama (local)</option>
                    <option value="claude">Claude (Anthropic)</option>
                    <option value="openai">OpenAI GPT-4</option>
                  </select>
                </label>
                <label>
                  Default tone
                  <select value={settings.aiDefaultTone ?? 'professional'} onChange={(event) => setSettings((current) => ({ ...current, aiDefaultTone: event.target.value }))}>
                    <option value="professional">Professional</option>
                    <option value="friendly">Friendly</option>
                    <option value="formal">Formal</option>
                  </select>
                </label>
              </div>
              <ToggleRow label="AI subject assist" hint="Suggest high-performing subject lines." checked={settings.aiSubjectAssist} onToggle={() => setSettings((current) => ({ ...current, aiSubjectAssist: !current.aiSubjectAssist }))} />
              <ToggleRow label="AI personalization" hint="Auto-personalize per recipient when enabled." checked={settings.aiPersonalization ?? true} onToggle={() => setSettings((current) => ({ ...current, aiPersonalization: !current.aiPersonalization }))} />
            </article>
          </div>
        </section>
      ) : null}

      <section className="dual-grid">
        <article className="glass-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Campaign features</p>
              <h4>What you can do</h4>
            </div>
          </div>
          <ul className="check-list">
            <li>Design rich HTML emails with merge tags and formatting.</li>
            <li>Import contact lists and segment by company, status, or role.</li>
            <li>Select from templates or create custom email templates.</li>
            <li>Schedule campaigns for future delivery or send immediately.</li>
            <li>Track opens, clicks, and replies in real-time.</li>
            <li>Manage SMTP settings, compliance, and email integrations.</li>
          </ul>
        </article>

        <article className="glass-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Best practices</p>
              <h4>Campaign optimization</h4>
            </div>
          </div>
          <ul className="check-list">
            <li>Test subject lines with A/B send splits for higher open rates.</li>
            <li>Use merge tags to personalize each email with candidate/company names.</li>
            <li>Start with a warmup period to establish sender reputation.</li>
            <li>Monitor bounce rates and remove invalid addresses promptly.</li>
            <li>Schedule sends during business hours for better engagement.</li>
            <li>Follow up with non-responders after 3-5 days.</li>
          </ul>
        </article>
      </section>
      <CampaignToastStack toasts={toasts} />
    </div>
  )
}