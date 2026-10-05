import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Bookmark,
  Building2,
  CalendarClock,
  Check,
  KeyRound,
  Link2,
  Loader,
  Mail,
  MessageSquare,
  Plug,
  Save,
  Search,
  Send,
  Settings2,
  Sparkles,
  Upload,
  UserPlus,
  Wand2,
  X,
} from 'lucide-react'

import {
  createLinkedInMessageTemplate,
  enrichLinkedInProfiles,
  generateLinkedInMessage,
  loadLinkedInWorkspace,
  runLinkedInDiscovery,
  saveLinkedInApiKeys,
  saveLinkedInSettings,
  sendLinkedInOutreach,
  setLinkedInRecruiterBookmark,
} from '../api/client'
import {
  DEFAULT_URL_QUEUE,
  LINKEDIN_TABS,
  MERGE_TAGS,
  MESSAGE_TYPE_BODIES,
  MESSAGE_TYPE_PROMPTS,
  MESSAGE_TYPE_SUBJECTS,
  OUTREACH_ANALYTICS,
  TOP_COMPANY_PERFORMANCE,
  apiKeyFieldForSource,
  avatarColorsForCompany,
  buildQuickConnectBody,
  buildSearchPreview,
  filterRecruiters,
  findRecruiterByName,
  formatApiUsageRow,
  formatToneForApi,
  mergeCompanyLists,
  mergeRecruiters,
  mergeTechLists,
  normalizeRecruiterIds,
  parseLinkedInCsvUrls,
  parseLinkedInPasteUrls,
  sequenceStatusClass,
  sortRecruiters,
} from '../utils/linkedinRecruiterHelpers'
import { pickFirstError, validateLinkedInSettings } from '../utils/validators'
import './LinkedInRecruiter.css'

const defaultDiscoveryForm = {
  seniority: 'Recruiter / Sr. Recruiter',
  location: 'United States',
  connections: '1st & 2nd degree',
  resultsPerCompany: 20,
}

const defaultApiKeys = {
  apollo: '',
  hunter: '',
  rocketreach: '',
  lusha: '',
}

function defaultOutreachSchedule() {
  const value = new Date(Date.now() + 24 * 60 * 60 * 1000)
  value.setHours(9, 0, 0, 0)
  const offset = value.getTimezoneOffset() * 60 * 1000
  return new Date(value.getTime() - offset).toISOString().slice(0, 16)
}

function ToggleSwitch({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      className={`toggle${checked ? ' on' : ''}`}
      onClick={() => !disabled && onChange(!checked)}
      aria-pressed={checked}
      disabled={disabled}
    />
  )
}

function RecruiterCard({ rec, selected, onToggle, onConnect, onMessage, onEmail, onBookmark, readOnly }) {
  const [bg, text] = avatarColorsForCompany(rec.company)
  return (
    <div className={`recruiter-card${selected ? ' selected' : ''}`}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggle(rec.id)}
          style={{ width: 'auto', marginTop: 3, cursor: 'pointer' }}
        />
        <div className="r-avatar" style={{ background: bg, color: text }}>
          {rec.avatar ?? rec.name?.slice(0, 2)?.toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
            <div>
              <div className="r-name">{rec.name}</div>
              <div className="r-title">{rec.title}</div>
              <div className="r-company">
                {rec.company} · {rec.location}
              </div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#0077b5' }}>{rec.match}%</div>
              <div style={{ fontSize: 10, color: '#9ca3af' }}>match</div>
            </div>
          </div>
          <div className="r-meta">
            {(rec.techs ?? []).map((tech) => (
              <span key={tech} className="pill pill-tech">
                {tech}
              </span>
            ))}
            <span className="pill pill-conn">{rec.conn}</span>
            {rec.source ? <span className="pill pill-source">{rec.source}</span> : null}
            {rec.conn === '1st' ? <span className="pill pill-conn">Connected</span> : null}
          </div>
          <div className="match-bar">
            <div className="match-fill" style={{ width: `${rec.match ?? 0}%` }} />
          </div>
          {rec.note ? <div style={{ fontSize: 10, color: '#9ca3af', marginTop: 4 }}>{rec.note}</div> : null}
          <div className="recruiter-card-actions">
            <button className="btn btn-li btn-xs" type="button" disabled={readOnly} onClick={() => onConnect(rec)}>
              <UserPlus size={12} /> Connect
            </button>
            <button className="btn btn-ghost btn-xs" type="button" disabled={readOnly} onClick={() => onMessage(rec)}>
              <MessageSquare size={12} /> Message
            </button>
            <button className="btn btn-secondary btn-xs" type="button" onClick={() => onEmail(rec)}>
              <Mail size={12} /> Email
            </button>
            <button
              className={`btn btn-secondary btn-xs${rec.bookmarked ? ' active' : ''}`}
              type="button"
              aria-pressed={Boolean(rec.bookmarked)}
              onClick={() => onBookmark(rec)}
            >
              <Bookmark size={12} fill={rec.bookmarked ? 'currentColor' : 'none'} />
              {rec.bookmarked ? 'Saved' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function SequenceTimeline({ sequence, onFollowUp, onMarkReplied, readOnly }) {
  const statusColors = {
    sent: '#059669',
    pending: '#d97706',
    scheduled: '#2563eb',
    replied: '#7c3aed',
  }

  return (
    <div className="sequence-card">
      <div style={{ fontSize: 12, fontWeight: 600, color: '#111827', marginBottom: 8 }}>{sequence.name}</div>
      <div className="sequence-steps">
        {(sequence.steps ?? []).map((step, index) => {
          const color = statusColors[step.status] ?? '#9ca3af'
          const done = step.status === 'sent' || step.status === 'replied'
          return (
            <div key={`${step.label}-${index}`} className="sequence-step">
              {index < (sequence.steps?.length ?? 0) - 1 ? (
                <div
                  style={{
                    position: 'absolute',
                    top: 7,
                    left: '50%',
                    right: '-50%',
                    height: 2,
                    background: done ? color : '#e5e7eb',
                    zIndex: 0,
                  }}
                />
              ) : null}
              <div className="sequence-step-dot" style={{ background: color }}>
                {done ? '✓' : '◷'}
              </div>
              <div className="sequence-step-label">{step.label}</div>
              <div className="sequence-step-date">{step.date}</div>
            </div>
          )
        })}
      </div>
      <div className="btn-row">
        <button className="btn btn-xs btn-ghost" type="button" disabled={readOnly} onClick={() => onFollowUp(sequence)}>
          <Send size={12} /> Follow up
        </button>
        <button className="btn btn-xs btn-secondary" type="button" disabled={readOnly} onClick={() => onMarkReplied(sequence)}>
          <Check size={12} /> Mark replied
        </button>
      </div>
    </div>
  )
}

const LinkedInRecruiterPage = ({ currentUser, onRefresh }) => {
  const [workspace, setWorkspace] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [activeTab, setActiveTab] = useState('discover')
  const [selectedRecs, setSelectedRecs] = useState(new Set())
  const [filteredRecs, setFilteredRecs] = useState([])
  const [recSearch, setRecSearch] = useState('')
  const [recSort, setRecSort] = useState('match')
  const [companyOptions, setCompanyOptions] = useState([])
  const [techOptions, setTechOptions] = useState([])
  const [activeCompanies, setActiveCompanies] = useState(new Set(['TEKsystems', 'Infosys BPM']))
  const [activeTechs, setActiveTechs] = useState(new Set(['Java', 'Spring Boot']))
  const [newCompany, setNewCompany] = useState('')
  const [newTech, setNewTech] = useState('')
  const [discoveryLoading, setDiscoveryLoading] = useState(false)
  const [discoveryForm, setDiscoveryForm] = useState(defaultDiscoveryForm)

  const [pasteUrls, setPasteUrls] = useState('')
  const [pasteTechContext, setPasteTechContext] = useState('Java, Spring Boot')
  const [enrichLoading, setEnrichLoading] = useState(false)
  const [enrichedProfiles, setEnrichedProfiles] = useState([])
  const [urlQueue, setUrlQueue] = useState(DEFAULT_URL_QUEUE)
  const [newQueueUrl, setNewQueueUrl] = useState('')

  const [apiKeyDraft, setApiKeyDraft] = useState(defaultApiKeys)
  const [showApiKeys, setShowApiKeys] = useState({})

  const [aiPrompt, setAiPrompt] = useState('')
  const [messageType, setMessageType] = useState('connect')
  const [aiTone, setAiTone] = useState('professional')
  const [aiChannel, setAiChannel] = useState('LinkedIn Message')
  const [aiBusy, setAiBusy] = useState(false)
  const [aiStatus, setAiStatus] = useState('')
  const [msgSubject, setMsgSubject] = useState('')
  const [outreachFilter, setOutreachFilter] = useState('')
  const [outreachLoading, setOutreachLoading] = useState(false)
  const [queueLoading, setQueueLoading] = useState(false)
  const [scheduleBusy, setScheduleBusy] = useState(false)
  const [scheduleAt, setScheduleAt] = useState(defaultOutreachSchedule)
  const [templateName, setTemplateName] = useState('')
  const [templateBusy, setTemplateBusy] = useState(false)
  const [settingsDraft, setSettingsDraft] = useState(null)
  const [settingsBusy, setSettingsBusy] = useState(false)

  const [toast, setToast] = useState(null)
  const msgBodyRef = useRef(null)
  const csvInputRef = useRef(null)
  const [charCount, setCharCount] = useState(0)

  const isReadOnly = currentUser?.role === 'user'

  const showNotification = useCallback((message, type = 'info') => {
    setToast({ message, type })
    window.setTimeout(() => setToast(null), 3200)
  }, [])

  const reloadWorkspace = useCallback(async () => {
    const data = await loadLinkedInWorkspace({ bustCache: true })
    setWorkspace(data)
    setFilteredRecs(data.recruiters ?? [])
    setCompanyOptions(mergeCompanyLists(data.companies))
    setTechOptions(mergeTechLists(data.technologies))
    if (data.settings) {
      setSettingsDraft(data.settings)
    }
    return data
  }, [])

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        await reloadWorkspace()
        setError(null)
      } catch (err) {
        setError(err.message || 'Failed to load workspace data')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [reloadWorkspace])

  const displayedRecs = useMemo(
    () => sortRecruiters(filterRecruiters(filteredRecs, recSearch), recSort),
    [filteredRecs, recSearch, recSort],
  )

  const searchPreview = useMemo(() => buildSearchPreview(activeTechs), [activeTechs])

  const outreachRecruiters = useMemo(() => {
    const selected = filteredRecs.filter((rec) => selectedRecs.has(rec.id))
    return filterRecruiters(selected, outreachFilter)
  }, [filteredRecs, selectedRecs, outreachFilter])

  const stats = {
    totalFound: workspace?.stats?.recruitersFound ?? filteredRecs.length,
    contacted: workspace?.stats?.contacted ?? 0,
    replied: workspace?.stats?.replied ?? 0,
    pending: workspace?.stats?.followupsDue ?? workspace?.followups?.length ?? 0,
  }

  const updateCharCount = () => {
    setCharCount(msgBodyRef.current?.innerText?.length ?? 0)
  }

  const handleToggleRec = (id) => {
    setSelectedRecs((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleToggleCompany = (company) => {
    setActiveCompanies((current) => {
      const next = new Set(current)
      if (next.has(company)) next.delete(company)
      else next.add(company)
      return next
    })
  }

  const handleToggleTech = (tech) => {
    setActiveTechs((current) => {
      const next = new Set(current)
      if (next.has(tech)) next.delete(tech)
      else next.add(tech)
      return next
    })
  }

  const addCompanyChip = () => {
    const value = newCompany.trim()
    if (!value) return
    setCompanyOptions((current) => (current.includes(value) ? current : [...current, value]))
    setActiveCompanies((current) => new Set([...current, value]))
    setNewCompany('')
    showNotification(`${value} added to target companies`, 'li')
  }

  const addTechChip = () => {
    const value = newTech.trim()
    if (!value) return
    setTechOptions((current) => (current.includes(value) ? current : [...current, value]))
    setActiveTechs((current) => new Set([...current, value]))
    setNewTech('')
    showNotification(`${value} added to technology keywords`, 'success')
  }

  const handleRunDiscovery = async () => {
    if (activeCompanies.size === 0) {
      showNotification('Select at least one target company', 'error')
      return
    }
    if (activeTechs.size === 0) {
      showNotification('Select at least one technology keyword', 'error')
      return
    }

    try {
      setDiscoveryLoading(true)
      showNotification(`Searching ${activeCompanies.size} companies via Apollo/Hunter...`, 'li')
      const response = await runLinkedInDiscovery({
        companies: Array.from(activeCompanies),
        technologies: Array.from(activeTechs),
        seniority: discoveryForm.seniority,
        location: discoveryForm.location,
        connections: discoveryForm.connections,
        resultsPerCompany: discoveryForm.resultsPerCompany,
      })
      const discovered = response.recruiters ?? []
      setFilteredRecs(discovered)
      setWorkspace((current) =>
        current
          ? {
              ...current,
              stats: {
                ...current.stats,
                recruitersFound: response.totalFound ?? discovered.length,
              },
            }
          : current,
      )
      showNotification(response.message ?? `Found ${discovered.length} matching recruiters!`, 'success')
    } catch (err) {
      showNotification(err.message || 'Discovery search failed', 'error')
    } finally {
      setDiscoveryLoading(false)
    }
  }

  const clearDiscoveryResults = async () => {
    setSelectedRecs(new Set())
    try {
      const data = await reloadWorkspace()
      setFilteredRecs(data.recruiters ?? [])
      showNotification('Results cleared — workspace reloaded', 'success')
    } catch {
      setFilteredRecs([])
      showNotification('Results cleared', 'success')
    }
  }

  const selectAllRecruiters = () => {
    setSelectedRecs(new Set(displayedRecs.map((rec) => rec.id)))
    showNotification('All visible recruiters selected', 'success')
  }

  const openBulkOutreach = () => {
    if (selectedRecs.size === 0) {
      showNotification('Select recruiters first', 'error')
      return
    }
    setActiveTab('outreach')
    showNotification(`Opening AI Outreach for ${selectedRecs.size} recruiters...`, 'li')
  }

  const quickConnect = async (rec) => {
    if (isReadOnly) {
      showNotification('Admin access required to send connection requests', 'error')
      return
    }
    const body = buildQuickConnectBody(rec)
    const subject = `Java Developer available for C2C — ${rec.company}`
    try {
      setOutreachLoading(true)
      const response = await sendLinkedInOutreach({
        recruiterIds: normalizeRecruiterIds([rec.id]),
        subject,
        body,
        channel: 'Connection note',
        scheduleAt: null,
      })
      showNotification(response.message ?? `Connection request sent to ${rec.name}!`, 'li')
      await reloadWorkspace()
    } catch (err) {
      showNotification(err.message || `Failed to connect with ${rec.name}`, 'error')
    } finally {
      setOutreachLoading(false)
    }
  }

  const quickMessage = (rec) => {
    setSelectedRecs(new Set([rec.id]))
    setActiveTab('outreach')
    if (msgBodyRef.current) {
      msgBodyRef.current.innerHTML = `<p>Hi ${rec.name},</p><p>Hope you are doing well! I noticed your work in IT staffing at ${rec.company} and wanted to reach out about a Senior Java Developer with ${(rec.techs ?? []).join(', ')} expertise available immediately for C2C contract roles.</p><p>Would love to connect and share more details!</p><p>Best regards,<br>{{candidate_name}}</p>`
      updateCharCount()
    }
    setMsgSubject(`Java Developer available for C2C — ${rec.company}`)
    showNotification(`Message composer opened for ${rec.name}`, 'li')
  }

  const showRecruiterEmail = (rec) => {
    showNotification(rec.email ? `Email: ${rec.email}` : 'Email not available for this recruiter', 'li')
  }

  const handleBookmarkRecruiter = async (rec) => {
    const nextValue = !rec.bookmarked
    try {
      const response = await setLinkedInRecruiterBookmark(rec.id, nextValue)
      const updateRows = (rows = []) => rows.map((row) => (
        row.id === rec.id ? { ...row, bookmarked: nextValue } : row
      ))
      setFilteredRecs(updateRows)
      setWorkspace((current) => (
        current ? { ...current, recruiters: updateRows(current.recruiters) } : current
      ))
      showNotification(response.message ?? `${rec.name} ${nextValue ? 'saved' : 'removed'}.`, 'success')
    } catch (err) {
      showNotification(err.message || 'Could not update saved recruiter', 'error')
    }
  }

  const enrichProfileUrls = async (urls) => {
    setEnrichLoading(true)
    try {
      showNotification(`Enriching ${urls.length} profiles via Apollo/Hunter...`, 'li')
      const response = await enrichLinkedInProfiles({
        urls,
        techContext: pasteTechContext,
      })
      const profiles = response.profiles ?? []
      setEnrichedProfiles(profiles)
      if (profiles.length) {
        setFilteredRecs((current) => mergeRecruiters(current, profiles))
        setSelectedRecs((current) => new Set([...current, ...profiles.map((profile) => profile.id)]))
      }
      showNotification(response.message ?? `${profiles.length} profiles enriched successfully!`, 'success')
    } catch (err) {
      showNotification(err.message || 'Profile enrichment failed', 'error')
    } finally {
      setEnrichLoading(false)
    }
  }

  const handleEnrichProfiles = async () => {
    const urls = parseLinkedInPasteUrls(pasteUrls)
    if (!urls.length) {
      showNotification('Paste some LinkedIn URLs first', 'error')
      return
    }
    await enrichProfileUrls(urls)
  }

  const handleCsvImport = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (file.size > 2 * 1024 * 1024) {
      showNotification('CSV must be 2 MB or smaller', 'error')
      return
    }
    try {
      const urls = parseLinkedInCsvUrls(await file.text()).slice(0, 100)
      if (!urls.length) {
        showNotification('No LinkedIn profile URLs were found in the CSV', 'error')
        return
      }
      setPasteUrls(urls.join('\n'))
      showNotification(`Imported ${urls.length} unique LinkedIn URL(s) from CSV`, 'success')
      await enrichProfileUrls(urls)
    } catch {
      showNotification('Could not read the CSV file', 'error')
    }
  }

  const addQueueUrl = () => {
    const value = newQueueUrl.trim()
    if (!value) return
    setUrlQueue((current) => [
      ...current,
      { id: `q-${Date.now()}`, url: value.replace(/^https?:\/\//, ''), status: 'Pending' },
    ])
    setNewQueueUrl('')
    showNotification('URL added to queue', 'success')
  }

  const runUrlQueue = async () => {
    const pending = urlQueue.filter((row) => row.status !== 'Done')
    if (!pending.length) {
      showNotification('Add URLs to the queue first', 'error')
      return
    }

    const urls = pending.map((row) => (row.url.startsWith('http') ? row.url : `https://${row.url}`))

    try {
      setQueueLoading(true)
      showNotification('Running API lookup on all queued URLs...', 'li')
      const response = await enrichLinkedInProfiles({
        urls,
        techContext: pasteTechContext,
      })
      const profiles = response.profiles ?? []
      setUrlQueue((current) =>
        current.map((row) => (row.status === 'Done' ? row : { ...row, status: 'Done' })),
      )
      setEnrichedProfiles((current) => mergeRecruiters(current, profiles))
      if (profiles.length) {
        setFilteredRecs((current) => mergeRecruiters(current, profiles))
        setSelectedRecs((current) => new Set([...current, ...profiles.map((profile) => profile.id)]))
      }
      showNotification(response.message ?? `Queue complete — ${profiles.length} recruiter(s) found!`, 'success')
    } catch (err) {
      showNotification(err.message || 'Queue lookup failed', 'error')
    } finally {
      setQueueLoading(false)
    }
  }

  const applyMessageType = (type) => {
    setMessageType(type)
    setAiPrompt(MESSAGE_TYPE_PROMPTS[type] ?? '')
    setMsgSubject(MESSAGE_TYPE_SUBJECTS[type] ?? '')
    if (msgBodyRef.current) {
      msgBodyRef.current.innerHTML = MESSAGE_TYPE_BODIES[type] ?? ''
      updateCharCount()
    }
  }

  const insertMergeTag = (tag) => {
    msgBodyRef.current?.focus()
    document.execCommand('insertText', false, tag)
    updateCharCount()
  }

  const formatEditor = (command) => {
    msgBodyRef.current?.focus()
    document.execCommand(command, false, null)
    updateCharCount()
  }

  const insertEditorLink = () => {
    const rawUrl = window.prompt('Enter a secure URL', 'https://')
    if (!rawUrl) return
    try {
      const url = new URL(rawUrl)
      if (!['http:', 'https:'].includes(url.protocol)) {
        throw new Error('Unsupported protocol')
      }
      msgBodyRef.current?.focus()
      document.execCommand('createLink', false, url.toString())
      updateCharCount()
    } catch {
      showNotification('Enter a valid http:// or https:// URL', 'error')
    }
  }

  const handleGenerateMessage = async (options = {}) => {
    const prompt = options.prompt ?? aiPrompt
    const type = options.messageType ?? messageType
    if (!prompt.trim()) {
      showNotification('Enter a prompt or select a message type first', 'error')
      return
    }

    setAiBusy(true)
    setAiStatus(options.improve ? 'Improving your message...' : 'Analyzing recruiter profile...')
    const steps = ['Personalizing for {{company}}...', 'Applying tech keyword matching...', 'Finalizing message...']
    let step = 0
    const interval = window.setInterval(() => {
      if (step < steps.length) {
        setAiStatus(steps[step])
        step += 1
      }
    }, 650)

    try {
      const response = await generateLinkedInMessage({
        prompt,
        messageType: type,
        tone: formatToneForApi(aiTone),
        channel: aiChannel,
      })
      setMsgSubject(response.subject ?? MESSAGE_TYPE_SUBJECTS[type] ?? MESSAGE_TYPE_SUBJECTS.inmail)
      if (msgBodyRef.current) {
        msgBodyRef.current.innerHTML = (response.body ?? response.message ?? '').replace(/\n/g, '<br/>')
        updateCharCount()
      }
      if (response.messageType) {
        setMessageType(response.messageType)
      }
      showNotification(options.improve ? 'Message improved!' : 'AI message generated!', 'purple')
    } catch (err) {
      if (!options.improve && msgBodyRef.current) {
        msgBodyRef.current.innerHTML = MESSAGE_TYPE_BODIES[type] ?? MESSAGE_TYPE_BODIES.inmail
        updateCharCount()
      }
      setMsgSubject(MESSAGE_TYPE_SUBJECTS[type] ?? MESSAGE_TYPE_SUBJECTS.inmail)
      showNotification(err.message || 'AI generation failed — loaded template fallback', 'purple')
    } finally {
      window.clearInterval(interval)
      setAiBusy(false)
      setAiStatus('')
    }
  }

  const handleImproveMessage = () => {
    const currentBody = msgBodyRef.current?.innerText?.trim()
    const improvePrompt = currentBody
      ? `Improve this outreach message. Keep merge tags intact and make it more concise and personal:\n\n${currentBody}`
      : `${aiPrompt}\n\nMake the message shorter, warmer, and more specific.`
    handleGenerateMessage({ prompt: improvePrompt, messageType, improve: true })
  }

  const handleGenerateVariants = async () => {
    const tones = ['professional', 'friendly', 'concise']
    setAiBusy(true)
    try {
      for (const tone of tones) {
        const response = await generateLinkedInMessage({
          prompt: aiPrompt || MESSAGE_TYPE_PROMPTS[messageType],
          messageType,
          tone: formatToneForApi(tone),
          channel: aiChannel,
        })
        if (tone === 'professional' && msgBodyRef.current) {
          setMsgSubject(response.subject ?? msgSubject)
          msgBodyRef.current.innerHTML = (response.body ?? response.message ?? '').replace(/\n/g, '<br/>')
          updateCharCount()
        }
      }
      showNotification('Generated 3 tone variants — professional variant loaded in editor', 'purple')
    } catch (err) {
      showNotification(err.message || 'Failed to generate variants', 'error')
    } finally {
      setAiBusy(false)
    }
  }

  const handleSendOutreach = async ({ scheduleAt = null } = {}) => {
    if (selectedRecs.size === 0) {
      showNotification('No recruiters selected', 'error')
      return
    }
    const body = msgBodyRef.current?.innerHTML ?? ''
    if (!body.replace(/<[^>]+>/g, '').trim()) {
      showNotification('Write a message first', 'error')
      return
    }

    const recruiterIds = normalizeRecruiterIds(selectedRecs)
    if (!recruiterIds.length) {
      showNotification('Selected recruiters have invalid IDs', 'error')
      return
    }

    try {
      if (scheduleAt) {
        setScheduleBusy(true)
      } else {
        setOutreachLoading(true)
      }
      showNotification(
        scheduleAt
          ? `Scheduling outreach for ${recruiterIds.length} recruiters...`
          : `Sending messages to ${recruiterIds.length} recruiters...`,
        'li',
      )
      const response = await sendLinkedInOutreach({
        recruiterIds,
        subject: msgSubject || 'Available Senior Java Developer | C2C | Immediate',
        body,
        channel: aiChannel,
        scheduleAt,
      })
      showNotification(response.message ?? `Sent to ${response.count ?? recruiterIds.length} recruiters!`, 'success')
      onRefresh?.()
      await reloadWorkspace()
    } catch (err) {
      showNotification(err.message || 'Failed to send outreach', 'error')
    } finally {
      setOutreachLoading(false)
      setScheduleBusy(false)
    }
  }

  const handleScheduleOutreach = () => {
    const scheduled = new Date(scheduleAt)
    if (!scheduleAt || Number.isNaN(scheduled.getTime())) {
      showNotification('Choose a valid date and time for outreach', 'error')
      return
    }
    handleSendOutreach({ scheduleAt: scheduled.toISOString() })
  }

  const handleFollowUpRecruiter = async (followupItem) => {
    const rec = findRecruiterByName(filteredRecs, followupItem.name)
    if (!rec) {
      showNotification(`Recruiter ${followupItem.name} not found in current results`, 'error')
      return
    }
    if (isReadOnly) {
      showNotification('Admin access required to send follow-ups', 'error')
      return
    }

    try {
      setOutreachLoading(true)
      const gen = await generateLinkedInMessage({
        prompt: `Write a ${followupItem.type} follow-up to ${rec.name} at ${rec.company} about a Java Developer still available for C2C.`,
        messageType: 'followup',
        tone: formatToneForApi(aiTone),
        channel: aiChannel,
      })
      const rawBody = gen.body ?? gen.message ?? MESSAGE_TYPE_BODIES.followup.replace(/<[^>]+>/g, '\n')
      const htmlBody = rawBody.includes('<') ? rawBody : rawBody.replace(/\n/g, '<br/>')
      const response = await sendLinkedInOutreach({
        recruiterIds: normalizeRecruiterIds([rec.id]),
        subject: gen.subject ?? MESSAGE_TYPE_SUBJECTS.followup,
        body: htmlBody,
        channel: aiChannel,
        scheduleAt: null,
      })
      showNotification(response.message ?? `Follow-up sent to ${rec.name}!`, 'li')
      await reloadWorkspace()
    } catch (err) {
      showNotification(err.message || `Failed to send follow-up to ${followupItem.name}`, 'error')
    } finally {
      setOutreachLoading(false)
    }
  }

  const handleSequenceFollowUp = async (sequence) => {
    const name = String(sequence.name ?? '').split(' — ')[0]
    const rec = findRecruiterByName(filteredRecs, name)
    if (!rec) {
      showNotification(`Could not find recruiter for sequence "${sequence.name}"`, 'error')
      return
    }
    await handleFollowUpRecruiter({ name: rec.name, company: rec.company, type: 'sequence follow-up' })
  }

  const handleSequenceMarkReplied = async (sequence) => {
    const name = String(sequence.name ?? '').split(' — ')[0]
    showNotification(`Marked ${name} as replied`, 'success')
    await reloadWorkspace()
  }

  const loadTemplate = (template) => {
    if (msgBodyRef.current) {
      msgBodyRef.current.innerHTML = template.body
      updateCharCount()
    }
    showNotification(`Template "${template.name}" loaded!`, 'success')
  }

  const handleSaveTemplate = async () => {
    const body = msgBodyRef.current?.innerHTML?.trim() ?? ''
    if (templateName.trim().length < 2) {
      showNotification('Enter a template name with at least 2 characters', 'error')
      return
    }
    if (!body.replace(/<[^>]+>/g, '').trim()) {
      showNotification('Write a message before saving a template', 'error')
      return
    }
    try {
      setTemplateBusy(true)
      const saved = await createLinkedInMessageTemplate({ name: templateName.trim(), body })
      setWorkspace((current) => {
        if (!current) return current
        const templates = [...(current.templates ?? [])]
        const index = templates.findIndex((item) => item.name.toLowerCase() === saved.name.toLowerCase())
        if (index >= 0) templates[index] = saved
        else templates.push(saved)
        return { ...current, templates }
      })
      setTemplateName('')
      showNotification(`Template "${saved.name}" saved`, 'success')
    } catch (err) {
      showNotification(err.message || 'Could not save template', 'error')
    } finally {
      setTemplateBusy(false)
    }
  }

  const testApiSource = async (sourceName) => {
    const field = apiKeyFieldForSource(sourceName)
    if (!field) {
      showNotification(`${sourceName} does not require an API key in this demo`, 'li')
      return
    }
    if (!apiKeyDraft[field]?.trim()) {
      showNotification(`Enter your ${sourceName} API key first`, 'error')
      return
    }
    try {
      const response = await saveLinkedInApiKeys({ [field]: apiKeyDraft[field] })
      showNotification(response.message ?? `${sourceName} connection verified!`, 'success')
      await reloadWorkspace()
    } catch (err) {
      showNotification(err.message || `${sourceName} test failed`, 'error')
    }
  }

  const connectApiSource = async (sourceName) => {
    const field = apiKeyFieldForSource(sourceName)
    if (!field) {
      showNotification('LinkedIn Official API requires partner approval — apply at developer.linkedin.com', 'li')
      return
    }
    if (!apiKeyDraft[field]?.trim()) {
      showNotification(`Enter your ${sourceName} API key in the configuration panel`, 'error')
      return
    }
    try {
      const response = await saveLinkedInApiKeys({ [field]: apiKeyDraft[field] })
      showNotification(response.message ?? `${sourceName} connected!`, 'success')
      await reloadWorkspace()
    } catch (err) {
      showNotification(err.message || `Failed to connect ${sourceName}`, 'error')
    }
  }

  const handleSaveSettings = async () => {
    if (!settingsDraft) return
    const validation = validateLinkedInSettings(settingsDraft)
    if (!validation.isValid) {
      showNotification(pickFirstError(validation.errors), 'error')
      return
    }
    setSettingsBusy(true)
    try {
      const response = await saveLinkedInSettings({ settings: settingsDraft })
      showNotification(response.message ?? 'LinkedIn settings saved!', 'li')
      onRefresh?.()
    } catch {
      showNotification('Failed to save LinkedIn settings', 'error')
    } finally {
      setSettingsBusy(false)
    }
  }

  const handleSaveApiKeys = async () => {
    try {
      const response = await saveLinkedInApiKeys(apiKeyDraft)
      showNotification(response.message ?? 'All API keys saved!', 'success')
      onRefresh?.()
    } catch {
      showNotification('Failed to save API keys', 'error')
    }
  }

  if (loading) {
    return (
      <div className="linkedin-recruiter-page page-loading">
        <div style={{ textAlign: 'center' }}>
          <Loader size={40} className="spin" style={{ margin: '0 auto 12px', color: '#0077b5' }} />
          <p style={{ color: '#6b7280', fontSize: 13 }}>Loading LinkedIn Recruiter...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="linkedin-recruiter-page">
      <div className="li-hero">
        <div>
          <h2>
            <Search size={16} /> LinkedIn Recruiter Discovery
          </h2>
          <p>Find recruiters via Apollo/Hunter APIs · Paste profiles · Track outreach sequences</p>
        </div>
        <div className="li-hero-badges">
          <span className="live-pill-li">● LIVE</span>
          {workspace?.apiConnected ? (
            <span className="li-hero-badge">
              <Plug size={12} /> APIs Ready
            </span>
          ) : null}
          <span className="li-hero-badge">{selectedRecs.size} selected</span>
        </div>
      </div>

      <div className="g4" style={{ marginBottom: 13 }}>
        <div className="stat-card">
          <div className="stat-num">{stats.totalFound}</div>
          <div className="stat-label">Recruiters Found</div>
        </div>
        <div className="stat-card">
          <div className="stat-num" style={{ color: '#059669' }}>
            {stats.contacted}
          </div>
          <div className="stat-label">Contacted</div>
        </div>
        <div className="stat-card">
          <div className="stat-num" style={{ color: '#7c3aed' }}>
            {stats.replied}
          </div>
          <div className="stat-label">Replied</div>
        </div>
        <div className="stat-card">
          <div className="stat-num" style={{ color: '#d97706' }}>
            {stats.pending}
          </div>
          <div className="stat-label">Follow-ups Due</div>
        </div>
      </div>

      {error ? (
        <div className="card" style={{ borderColor: '#fca5a5', color: '#991b1b', marginBottom: 12 }}>
          {error}
        </div>
      ) : null}

      <div className="sub-tabs">
        {LINKEDIN_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`sub-tab${activeTab === tab.key ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'discover' ? (
        <div className="g2">
          <div>
            <div className="card">
              <div className="card-title">
                <Building2 size={15} /> Target Companies (LinkedIn People Tab)
              </div>
              <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 8 }}>
                Select firms whose LinkedIn <code>/people/</code> page will be queued for recruiter lookup via API.
              </p>
              <div style={{ marginBottom: 9 }}>
                {companyOptions.map((company) => (
                  <span
                    key={company}
                    className={`company-chip${activeCompanies.has(company) ? ' active' : ''}`}
                    onClick={() => handleToggleCompany(company)}
                    onKeyDown={(event) => event.key === 'Enter' && handleToggleCompany(company)}
                    role="button"
                    tabIndex={0}
                  >
                    {activeCompanies.has(company) ? '✓' : '+'} {company}
                  </span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  value={newCompany}
                  onChange={(event) => setNewCompany(event.target.value)}
                  placeholder="Add company name..."
                  style={{ flex: 1, fontSize: 11 }}
                />
                <button className="btn btn-li btn-sm" type="button" onClick={addCompanyChip}>
                  Add
                </button>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Technology Keywords (AND / OR)</div>
              <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 8 }}>
                Search string: <strong>&quot;Recruiter&quot; AND [selected tech]</strong>
              </p>
              <div style={{ marginBottom: 9 }}>
                {techOptions.map((tech) => (
                  <span
                    key={tech}
                    className={`tech-chip${activeTechs.has(tech) ? ' active' : ''}`}
                    onClick={() => handleToggleTech(tech)}
                    onKeyDown={(event) => event.key === 'Enter' && handleToggleTech(tech)}
                    role="button"
                    tabIndex={0}
                  >
                    {tech}
                  </span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  value={newTech}
                  onChange={(event) => setNewTech(event.target.value)}
                  placeholder="Add technology..."
                  style={{ flex: 1, fontSize: 11 }}
                />
                <button className="btn btn-primary btn-sm" type="button" onClick={addTechChip}>
                  Add
                </button>
              </div>
              <div className="search-preview-box">
                <Search size={12} style={{ verticalAlign: 'middle' }} /> Search string preview: <strong>{searchPreview}</strong>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Discovery Filters</div>
              <div className="g2" style={{ gap: 8 }}>
                <div className="fg">
                  <label>Seniority Level</label>
                  <select
                    value={discoveryForm.seniority}
                    onChange={(event) => setDiscoveryForm((current) => ({ ...current, seniority: event.target.value }))}
                  >
                    <option>Any</option>
                    <option>Recruiter / Sr. Recruiter</option>
                    <option>Technical Recruiter</option>
                    <option>Talent Acquisition</option>
                  </select>
                </div>
                <div className="fg">
                  <label>Location</label>
                  <input
                    value={discoveryForm.location}
                    onChange={(event) => setDiscoveryForm((current) => ({ ...current, location: event.target.value }))}
                    placeholder="USA, Texas, Remote..."
                  />
                </div>
              </div>
              <div className="g2" style={{ gap: 8 }}>
                <div className="fg">
                  <label>Connections</label>
                  <select
                    value={discoveryForm.connections}
                    onChange={(event) => setDiscoveryForm((current) => ({ ...current, connections: event.target.value }))}
                  >
                    <option>Any</option>
                    <option>1st & 2nd degree</option>
                    <option>2nd degree only</option>
                    <option>3rd degree</option>
                  </select>
                </div>
                <div className="fg">
                  <label>Results per company</label>
                  <input
                    type="number"
                    min={5}
                    max={100}
                    value={discoveryForm.resultsPerCompany}
                    onChange={(event) =>
                      setDiscoveryForm((current) => ({ ...current, resultsPerCompany: Number(event.target.value) || 20 }))
                    }
                  />
                </div>
              </div>
              <div className="btn-row">
                <button className="btn btn-li" type="button" disabled={discoveryLoading} onClick={handleRunDiscovery}>
                  {discoveryLoading ? <Loader size={14} className="spin" /> : <Search size={14} />}
                  Run Discovery
                </button>
                <button className="btn btn-secondary btn-sm" type="button" onClick={clearDiscoveryResults}>
                  Clear
                </button>
              </div>
            </div>
          </div>

          <div>
            <div className="discover-results-toolbar">
              <input
                value={recSearch}
                onChange={(event) => setRecSearch(event.target.value)}
                placeholder="Filter recruiter results..."
              />
              <select value={recSort} onChange={(event) => setRecSort(event.target.value)}>
                <option value="match">Best match</option>
                <option value="conn">By connection</option>
                <option value="company">By company</option>
              </select>
              <button className="btn btn-sm btn-secondary" type="button" onClick={selectAllRecruiters}>
                All
              </button>
              <button className="btn btn-success btn-sm" type="button" onClick={openBulkOutreach}>
                Outreach ({selectedRecs.size})
              </button>
            </div>

            <div className="recruiter-results-scroll">
              {discoveryLoading ? (
                <div className="loading-inline">
                  <Loader size={16} className="spin" /> Querying APIs for recruiters...
                </div>
              ) : displayedRecs.length === 0 ? (
                <div className="empty-state">No recruiters found. Run discovery first.</div>
              ) : (
                displayedRecs.map((rec) => (
                  <RecruiterCard
                    key={rec.id}
                    rec={rec}
                    selected={selectedRecs.has(rec.id)}
                    onToggle={handleToggleRec}
                    onConnect={quickConnect}
                    onMessage={quickMessage}
                    onEmail={showRecruiterEmail}
                    onBookmark={handleBookmarkRecruiter}
                    readOnly={isReadOnly}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === 'paste' ? (
        <div className="g2">
          <div>
            <div className="card">
              <div className="card-title">
                <Link2 size={15} /> Paste LinkedIn Profile URLs
              </div>
              <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 9 }}>
                Find recruiters manually on LinkedIn, copy their profile URLs, paste them here. AI will look up details via Apollo/Hunter.
              </p>
              <div className="fg">
                <label>Profile URLs (one per line)</label>
                <textarea
                  rows={6}
                  value={pasteUrls}
                  onChange={(event) => setPasteUrls(event.target.value)}
                  placeholder={'https://www.linkedin.com/in/john-smith-recruiter/\nhttps://www.linkedin.com/in/jane-doe-ta/'}
                />
              </div>
              <div className="fg">
                <label>Technology context for these recruiters</label>
                <input value={pasteTechContext} onChange={(event) => setPasteTechContext(event.target.value)} />
              </div>
              <div className="btn-row">
                <button className="btn btn-li" type="button" disabled={enrichLoading} onClick={handleEnrichProfiles}>
                  {enrichLoading ? <Loader size={14} className="spin" /> : <Sparkles size={14} />}
                  Lookup & Enrich
                </button>
                <input
                  ref={csvInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  hidden
                  onChange={handleCsvImport}
                />
                <button
                  className="btn btn-secondary btn-sm"
                  type="button"
                  disabled={enrichLoading}
                  onClick={() => csvInputRef.current?.click()}
                >
                  <Upload size={14} /> Import CSV
                </button>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Company People Page Queue</div>
              <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 8 }}>
                Add company LinkedIn people-page URLs to queue for recruiter lookup.
              </p>
              {urlQueue.map((row) => (
                <div key={row.id} className="url-row">
                  <Link2 size={13} style={{ color: '#0077b5' }} />
                  <span style={{ flex: 1 }}>{row.url}</span>
                  <span
                    style={{
                      fontSize: 10,
                      background: row.status === 'Queued' ? '#d1fae5' : '#fef3c7',
                      color: row.status === 'Queued' ? '#065f46' : '#92400e',
                      padding: '1px 6px',
                      borderRadius: 4,
                    }}
                  >
                    {row.status}
                  </span>
                  <button className="btn btn-xs btn-secondary" type="button" onClick={() => setUrlQueue((current) => current.filter((item) => item.id !== row.id))}>
                    <X size={12} />
                  </button>
                </div>
              ))}
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <input
                  value={newQueueUrl}
                  onChange={(event) => setNewQueueUrl(event.target.value)}
                  placeholder="https://linkedin.com/company/.../people/"
                  style={{ flex: 1, fontSize: 11 }}
                />
                <button className="btn btn-li btn-sm" type="button" onClick={addQueueUrl}>
                  Add
                </button>
              </div>
              <div className="btn-row">
                <button className="btn btn-primary btn-sm" type="button" disabled={queueLoading || enrichLoading} onClick={runUrlQueue}>
                  {queueLoading ? <Loader size={14} className="spin" /> : null}
                  Run Queue via API
                </button>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Enriched Profiles</div>
            {enrichedProfiles.length === 0 ? (
              <div className="empty-state">
                <span className="empty-state-icon">🔗</span>
                Paste LinkedIn URLs above and click &quot;Lookup & Enrich&quot; to see recruiter profiles here
              </div>
            ) : (
              enrichedProfiles.map((profile) => {
                const [bg, text] = avatarColorsForCompany(profile.company)
                return (
                  <div key={profile.id ?? profile.email} className="recruiter-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                      <div className="r-avatar" style={{ background: bg, color: text }}>
                        {profile.avatar ?? profile.name?.slice(0, 2)}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div className="r-name">{profile.name}</div>
                        <div className="r-title">{profile.title}</div>
                        <div className="r-company">{profile.company}</div>
                        <div className="r-meta">
                          {(profile.techs ?? []).map((tech) => (
                            <span key={tech} className="pill pill-tech">
                              {tech}
                            </span>
                          ))}
                          <span className="pill pill-source">Enriched via Apollo</span>
                        </div>
                        {profile.note ? <div style={{ fontSize: 10, color: '#6b7280', marginTop: 3 }}>{profile.note}</div> : null}
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      ) : null}

      {activeTab === 'apis' ? (
        <div className="g2">
          <div className="card">
            <div className="card-title">Connected Data Sources</div>
            <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 10 }}>
              These APIs legally find recruiter emails, job titles, and company info.
            </p>
            {(workspace?.apiSources ?? []).map((source) => (
              <div key={source.id} className="api-card">
                <div className="api-logo" style={{ background: `${source.color}22`, color: source.color }}>
                  {source.shortCode}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{source.name}</div>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>{source.description}</div>
                </div>
                <span className={source.status === 'connected' ? 'api-connected' : 'api-disconnected'}>
                  {source.status === 'connected' ? 'Connected' : source.status === 'pending' ? 'Pending approval' : 'Not connected'}
                </span>
                <button
                  className={`btn btn-sm ${source.status === 'connected' ? 'btn-secondary' : 'btn-li'}`}
                  type="button"
                  disabled={isReadOnly}
                  onClick={() => (source.status === 'connected' ? testApiSource(source.name) : connectApiSource(source.name))}
                >
                  <Plug size={12} /> {source.status === 'connected' ? 'Test' : 'Connect'}
                </button>
              </div>
            ))}
          </div>

          <div>
            <div className="card">
              <div className="card-title">
                <KeyRound size={15} /> API Key Configuration
              </div>
              {Object.keys(apiKeyDraft).map((key) => (
                <div key={key} className="fg">
                  <label>{key.charAt(0).toUpperCase() + key.slice(1)} API Key</label>
                  <div style={{ display: 'flex', gap: 5 }}>
                    <input
                      type={showApiKeys[key] ? 'text' : 'password'}
                      value={apiKeyDraft[key]}
                      onChange={(event) => setApiKeyDraft((current) => ({ ...current, [key]: event.target.value }))}
                      placeholder={`Enter ${key} API key...`}
                      style={{ flex: 1 }}
                    />
                    <button className="btn btn-secondary btn-xs" type="button" onClick={() => setShowApiKeys((current) => ({ ...current, [key]: !current[key] }))}>
                      {showApiKeys[key] ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>
              ))}
              <div className="btn-row">
                <button className="btn btn-primary btn-sm" type="button" disabled={isReadOnly} onClick={handleSaveApiKeys}>
                  Save All Keys
                </button>
              </div>
            </div>

            <div className="card">
              <div className="card-title">API Usage This Month</div>
              {(workspace?.apiUsage ?? []).map((row) => (
                <div key={row.label} className="company-performance-row">
                  <span style={{ color: '#6b7280' }}>{row.label}</span>
                  <span style={{ fontWeight: 600 }}>{formatApiUsageRow(row)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === 'outreach' ? (
        <div className="g2">
          <div>
            <div className="ai-box">
              <div className="ai-title">
                <Sparkles size={14} /> AI Message Generator
              </div>
              <div className="fg">
                <label style={{ color: '#5b21b6' }}>Recruiter context & what to say</label>
                <textarea
                  rows={3}
                  value={aiPrompt}
                  onChange={(event) => setAiPrompt(event.target.value)}
                  placeholder="Write a LinkedIn connection message to a Java Technical Recruiter at TEKsystems..."
                  style={{ borderColor: '#c4b5fd', background: '#faf5ff' }}
                />
              </div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#5b21b6', marginBottom: 5 }}>Quick message types</div>
                {Object.keys(MESSAGE_TYPE_PROMPTS).map((type) => (
                  <span key={type} className="tech-chip msg-type-chip" onClick={() => applyMessageType(type)} role="button" tabIndex={0}>
                    {type}
                  </span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                <select value={aiTone} onChange={(event) => setAiTone(event.target.value)} style={{ flex: 1, fontSize: 11 }}>
                  <option value="professional">Tone: Professional</option>
                  <option value="friendly">Tone: Friendly</option>
                  <option value="concise">Tone: Concise</option>
                  <option value="enthusiastic">Tone: Enthusiastic</option>
                </select>
                <select value={aiChannel} onChange={(event) => setAiChannel(event.target.value)} style={{ flex: 1, fontSize: 11 }}>
                  <option>LinkedIn Message</option>
                  <option>InMail</option>
                  <option>Email</option>
                  <option>Connection note</option>
                </select>
              </div>
              {aiBusy ? (
                <div className="ai-gen show">
                  <span className="spin" />
                  <span>{aiStatus || 'Generating message...'}</span>
                </div>
              ) : null}
              <div className="btn-row" style={{ marginTop: 6 }}>
                <button className="btn btn-purple" type="button" disabled={aiBusy} onClick={() => handleGenerateMessage()}>
                  <Sparkles size={14} /> Generate Message
                </button>
                <button className="btn btn-ghost btn-sm" type="button" disabled={aiBusy} onClick={handleImproveMessage}>
                  <Wand2 size={14} /> Improve
                </button>
                <button className="btn btn-secondary btn-sm" type="button" disabled={aiBusy} onClick={handleGenerateVariants}>
                  3 Variants
                </button>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Message Editor</div>
              <div className="fg">
                <label>Subject / Connection Note Title</label>
                <input value={msgSubject} onChange={(event) => setMsgSubject(event.target.value)} />
              </div>
              <div className="fg">
                <label>Merge tags — click to insert</label>
                <div style={{ marginBottom: 6 }}>
                  {MERGE_TAGS.map((tag) => (
                    <span key={tag} className="merge-tag" onClick={() => insertMergeTag(tag)} role="button" tabIndex={0}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <div className="toolbar">
                <button className="tb-btn" type="button" onClick={() => formatEditor('bold')}>
                  B
                </button>
                <button className="tb-btn" type="button" onClick={() => formatEditor('italic')}>
                  I
                </button>
                <button className="tb-btn" type="button" onClick={() => formatEditor('insertUnorderedList')}>
                  •
                </button>
                <button className="tb-btn" type="button" onClick={() => formatEditor('insertOrderedList')} title="Numbered list">
                  1.
                </button>
                <button className="tb-btn" type="button" onClick={insertEditorLink} title="Insert link">
                  <Link2 size={12} />
                </button>
                <span style={{ fontSize: 10, color: '#9ca3af', marginLeft: 4, alignSelf: 'center' }}>{charCount} chars</span>
              </div>
              <div
                className="rich-area"
                ref={msgBodyRef}
                contentEditable={!isReadOnly}
                suppressContentEditableWarning
                onInput={updateCharCount}
              />
              <div className="g2" style={{ gap: 8, marginTop: 8 }}>
                <div className="fg">
                  <label>Schedule date and time</label>
                  <input
                    type="datetime-local"
                    value={scheduleAt}
                    onChange={(event) => setScheduleAt(event.target.value)}
                    disabled={isReadOnly}
                  />
                </div>
                <div className="fg">
                  <label>Template name</label>
                  <input
                    value={templateName}
                    onChange={(event) => setTemplateName(event.target.value)}
                    placeholder="e.g. Java recruiter follow-up"
                    disabled={isReadOnly}
                    maxLength={120}
                  />
                </div>
              </div>
              <div className="btn-row">
                <button className="btn btn-li" type="button" disabled={isReadOnly || outreachLoading} onClick={() => handleSendOutreach()}>
                  {outreachLoading ? <Loader size={14} className="spin" /> : <Send size={14} />}
                  Send to Selected ({selectedRecs.size})
                </button>
                <button className="btn btn-secondary btn-sm" type="button" disabled={isReadOnly || scheduleBusy} onClick={handleScheduleOutreach}>
                  {scheduleBusy ? <Loader size={14} className="spin" /> : <CalendarClock size={14} />}
                  Schedule
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  type="button"
                  disabled={isReadOnly || templateBusy}
                  onClick={handleSaveTemplate}
                >
                  {templateBusy ? <Loader size={14} className="spin" /> : <Save size={14} />} Save Template
                </button>
              </div>
            </div>
          </div>

          <div>
            <div className="card">
              <div className="card-title">Send to Recruiters</div>
              <input
                value={outreachFilter}
                onChange={(event) => setOutreachFilter(event.target.value)}
                placeholder="Filter selected recruiters..."
                style={{ marginBottom: 8, fontSize: 11 }}
              />
              <div style={{ maxHeight: 260, overflowY: 'auto' }}>
                {outreachRecruiters.length === 0 ? (
                  <div className="empty-state" style={{ padding: 14 }}>
                    Select recruiters from the Discover tab
                  </div>
                ) : (
                  outreachRecruiters.map((rec) => {
                    const [bg, text] = avatarColorsForCompany(rec.company)
                    return (
                      <div key={rec.id} className="outreach-row">
                        <div className="r-avatar" style={{ width: 28, height: 28, fontSize: 10, background: bg, color: text }}>
                          {rec.avatar}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12, fontWeight: 600 }}>{rec.name}</div>
                          <div style={{ fontSize: 10, color: '#6b7280' }}>{rec.company}</div>
                        </div>
                        <span className="pill pill-conn">{rec.conn}</span>
                        <button
                          className="btn btn-xs btn-secondary"
                          type="button"
                          onClick={() => handleToggleRec(rec.id)}
                        >
                          <X size={12} />
                        </button>
                      </div>
                    )
                  })
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-title">Saved Message Templates</div>
              {(workspace?.templates ?? []).map((template) => (
                <div key={template.name} className="template-row" onClick={() => loadTemplate(template)} role="button" tabIndex={0}>
                  <strong>{template.name}</strong>
                  <p>{template.body.slice(0, 60)}...</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === 'tracker' ? (
        <div className="g2">
          <div className="card">
            <div className="card-title">Outreach Sequences</div>
            {(workspace?.sequences ?? []).length === 0 ? (
              <div className="empty-state">No sequences yet. Start an outreach campaign to create a sequence.</div>
            ) : (
              (workspace?.sequences ?? []).map((sequence) => (
                <SequenceTimeline
                  key={sequence.id ?? sequence.name}
                  sequence={sequence}
                  readOnly={isReadOnly}
                  onFollowUp={handleSequenceFollowUp}
                  onMarkReplied={handleSequenceMarkReplied}
                />
              ))
            )}
          </div>

          <div className="card">
            <div className="card-title">Outreach Analytics</div>
            <div className="analytics-grid-li">
              <div className="analytics-tile-li" style={{ background: '#f0f9ff' }}>
                <strong style={{ color: '#0369a1' }}>{OUTREACH_ANALYTICS.openRate}%</strong>
                <span>Open Rate</span>
              </div>
              <div className="analytics-tile-li" style={{ background: '#f0fdf4' }}>
                <strong style={{ color: '#065f46' }}>{OUTREACH_ANALYTICS.replyRate}%</strong>
                <span>Reply Rate</span>
              </div>
              <div className="analytics-tile-li" style={{ background: '#fdf4ff' }}>
                <strong style={{ color: '#7e22ce' }}>{OUTREACH_ANALYTICS.avgTouches}</strong>
                <span>Avg touches</span>
              </div>
              <div className="analytics-tile-li" style={{ background: '#fff7ed' }}>
                <strong style={{ color: '#c2410c' }}>{OUTREACH_ANALYTICS.avgReplyDays}</strong>
                <span>Avg reply time</span>
              </div>
            </div>

            <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 7 }}>Best performing companies</div>
            {TOP_COMPANY_PERFORMANCE.map((row) => (
              <div key={row.company} className="company-performance-row">
                <span style={{ color: '#6b7280' }}>{row.company}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="company-performance-bar">
                    <div className="company-performance-fill" style={{ width: `${row.pct}%` }} />
                  </div>
                  <span style={{ fontWeight: 600, color: '#0077b5' }}>{row.pct}%</span>
                </div>
              </div>
            ))}

            <div style={{ marginTop: 10, paddingTop: 8, borderTop: '0.5px solid #f3f4f6' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Follow-ups due today</div>
              {(workspace?.followups ?? []).map((item) => (
                <div key={`${item.name}-${item.type}`} className="followup-row">
                  <div className={`seq-dot ${sequenceStatusClass(item.due === 'Today' ? 'pending' : 'scheduled')}`} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: '#111827' }}>{item.name}</div>
                    <div style={{ color: '#6b7280' }}>
                      {item.company} · {item.type}
                    </div>
                  </div>
                  <span className={`followup-due ${item.due === 'Today' ? 'today' : 'tomorrow'}`}>{item.due}</span>
                  <button className="btn btn-xs btn-li" type="button" disabled={isReadOnly || outreachLoading} onClick={() => handleFollowUpRecruiter(item)}>
                    <Send size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === 'settings' ? (
        <div className="g2">
          <div className="card">
            <div className="card-title">
              <Settings2 size={15} /> Discovery Automation
            </div>
            {settingsDraft ? (
              <>
                {[
                  ['autoRunDaily', 'Auto-run discovery daily', 'Runs at 8am every weekday'],
                  ['autoEnrich', 'Auto-enrich new profiles', 'Use Apollo/Hunter on every result'],
                  ['skipContacted', 'Skip already-contacted recruiters', ''],
                  ['autoFollowup', 'Auto follow-up after 3 days', ''],
                  ['aiPersonalize', 'AI personalize each message', 'Uses recruiter name, company, tech'],
                ].map(([field, label, hint]) => (
                  <div key={field} className="toggle-row">
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>{label}</div>
                      {hint ? <div style={{ fontSize: 10, color: '#9ca3af' }}>{hint}</div> : null}
                    </div>
                    <ToggleSwitch
                      checked={Boolean(settingsDraft[field])}
                      disabled={isReadOnly}
                      onChange={(value) => setSettingsDraft((current) => ({ ...current, [field]: value }))}
                    />
                  </div>
                ))}
                <div className="fg" style={{ marginTop: 10 }}>
                  <label>Max outreach messages per day</label>
                  <input
                    type="number"
                    value={settingsDraft.maxPerDay}
                    onChange={(event) => setSettingsDraft((current) => ({ ...current, maxPerDay: Number(event.target.value) || 0 }))}
                  />
                </div>
                <div className="fg">
                  <label>Delay between messages (seconds)</label>
                  <input
                    type="number"
                    value={settingsDraft.delaySeconds}
                    onChange={(event) => setSettingsDraft((current) => ({ ...current, delaySeconds: Number(event.target.value) || 0 }))}
                  />
                </div>
              </>
            ) : null}
          </div>

          <div>
            <div className="card">
              <div className="card-title">LinkedIn Account</div>
              {settingsDraft ? (
                <>
                  <div className="fg">
                    <label>LinkedIn Account Email</label>
                    <input
                      value={settingsDraft.accountEmail}
                      onChange={(event) => setSettingsDraft((current) => ({ ...current, accountEmail: event.target.value }))}
                    />
                  </div>
                  <div className="fg">
                    <label>Daily connection request limit</label>
                    <input
                      type="number"
                      value={settingsDraft.dailyConnections}
                      onChange={(event) => setSettingsDraft((current) => ({ ...current, dailyConnections: Number(event.target.value) || 0 }))}
                    />
                  </div>
                  <div className="fg">
                    <label>Daily InMail limit</label>
                    <input
                      type="number"
                      value={settingsDraft.dailyInmails}
                      onChange={(event) => setSettingsDraft((current) => ({ ...current, dailyInmails: Number(event.target.value) || 0 }))}
                    />
                  </div>
                  <div className="toggle-row">
                    <div style={{ fontSize: 12, fontWeight: 600 }}>LinkedIn Premium / Recruiter account</div>
                    <ToggleSwitch
                      checked={Boolean(settingsDraft.isPremium)}
                      disabled={isReadOnly}
                      onChange={(value) => setSettingsDraft((current) => ({ ...current, isPremium: value }))}
                    />
                  </div>
                  <div className="btn-row">
                    <button className="btn btn-li btn-sm" type="button" disabled={isReadOnly || settingsBusy} onClick={handleSaveSettings}>
                      {settingsBusy ? <Loader size={14} className="spin" /> : <Save size={14} />}
                      Save
                    </button>
                  </div>
                </>
              ) : null}
            </div>

            <div className="card">
              <div className="card-title">Compliance</div>
              {settingsDraft ? (
                <>
                  {[
                    ['respectDnc', 'Respect "do not contact" list'],
                    ['honorUnsubscribes', 'Honor unsubscribes & opt-outs'],
                    ['usePermittedSources', 'Use only permitted API sources'],
                  ].map(([field, label]) => (
                    <div key={field} className="toggle-row">
                      <div style={{ fontSize: 12, fontWeight: 600 }}>{label}</div>
                      <ToggleSwitch
                        checked={Boolean(settingsDraft[field])}
                        disabled={isReadOnly}
                        onChange={(value) => setSettingsDraft((current) => ({ ...current, [field]: value }))}
                      />
                    </div>
                  ))}
                </>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {toast ? (
        <div className={`toast show ${toast.type === 'success' ? 'success' : toast.type === 'purple' ? 'purple' : toast.type === 'li' ? 'li' : ''}`}>
          {toast.message}
        </div>
      ) : null}
    </div>
  )
}

export default LinkedInRecruiterPage
