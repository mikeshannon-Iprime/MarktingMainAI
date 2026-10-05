export const PROFILE_EXPERIENCE_OPTIONS = ['1-2 Years', '3-5 Years', '5-8 Years', '8-12 Years', '12+ Years']

export const PROFILE_EMPLOYMENT_OPTIONS = [
  'Contract (C2C)',
  'Contract (W2)',
  'Full Time',
  'Contract to Hire',
  'Both Contract & Full Time',
]

export const PROFILE_VISA_OPTIONS = ['US Citizen', 'Green Card', 'H1B', 'OPT/CPT', 'TN Visa']

export const PROFILE_WORK_MODE_OPTIONS = ['Remote Only', 'Hybrid', 'On-site', 'Any']

export const MATCH_THRESHOLD_OPTIONS = [40, 50, 60, 65, 70, 75, 80, 85, 90, 95]

/** Fixed CV↔JD routing used by auto-apply / discovery */
export const MATCH_POLICY = {
  applyMin: 65,
  tailorMin: 40,
  rejectBelow: 40,
  postedWindows: [
    { value: '1', label: 'Last 24 Hours' },
    { value: '2', label: 'Last 48 Hours' },
  ],
}

export const US_TIMEZONES = [
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time Zone (MST)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time Zone (PST)' },
]

export const SEARCH_RADIUS_OPTIONS = ['25 miles', '50 miles', '100 miles', 'Nationwide']

export const SEARCH_POSTED_WITHIN_OPTIONS = [
  { value: '1', label: 'Last 24 Hours' },
  { value: '2', label: 'Last 48 Hours' },
  { value: '3', label: 'Last 3 Days' },
  { value: '7', label: 'Last 7 Days' },
  { value: '14', label: 'Last 14 Days' },
  { value: '30', label: 'Last 30 Days' },
]

export const SEARCH_EXPERIENCE_OPTIONS = [
  'Any',
  'Mid-Level (3-5 yrs)',
  'Senior (5-8 yrs)',
  'Lead/Principal (8+ yrs)',
]

export const SEARCH_REPEAT_OPTIONS = ['Once daily', 'Every 6 hours', 'Every 3 hours', 'Every hour']

export const LINKEDIN_EXPERIENCE_LEVELS = [
  { value: 'all', label: 'All levels' },
  { value: 'entry', label: 'Entry level' },
  { value: 'mid', label: 'Mid-Senior' },
  { value: 'senior', label: 'Senior' },
  { value: 'director', label: 'Director' },
]

export const LINKEDIN_DATE_POSTED = [
  { value: 'all', label: 'Any time' },
  { value: '24h', label: 'Past 24 hours' },
  { value: 'week', label: 'Past week' },
]

export const LINKEDIN_SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'recent', label: 'Most Recent' },
  { value: 'applicants', label: 'Most Applicants' },
]

/** @deprecated use PROFILE_EMPLOYMENT_OPTIONS in profile; kept for search filter mapping */
export const EMPLOYMENT_TYPES = ['Contract', 'Full-Time', 'Both']

export function getPortalInitials(name) {
  return (name ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('') || 'JP'
}

export function getCompanyInitials(name) {
  return getPortalInitials(name)
}

export function parseSpreadsheetRows(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean)
  if (!lines.length) {
    return []
  }

  const rows = []
  const header = lines[0].toLowerCase()
  const startIndex = header.includes('name') && header.includes('url') ? 1 : 0

  for (const line of lines.slice(startIndex)) {
    const parts = line.includes('\t')
      ? line.split('\t').map((item) => item.trim())
      : line.split(',').map((item) => item.trim().replace(/^"|"$/g, ''))

    if (parts.length >= 2 && parts[0] && parts[1]) {
      const firstIsUrl = isValidPortalUrl(parts[0])
      const secondIsUrl = isValidPortalUrl(parts[1])
      const url = firstIsUrl ? parts[0] : (secondIsUrl ? parts[1] : '')
      if (!url) {
        continue
      }
      let name = firstIsUrl ? parts[1] : parts[0]
      if (!name || isSkippablePortalLabel(name) || isValidPortalUrl(name)) {
        name = hostnameFromUrl(url)
      }
      rows.push({ name, url })
    }
  }

  return rows
}

export function isValidPortalUrl(value) {
  const trimmed = String(value ?? '').trim()
  return /^https?:\/\//i.test(trimmed)
}

function hostnameFromUrl(url) {
  try {
    const host = new URL(url).hostname.replace(/^www\./i, '')
    const label = host.split('.')[0] ?? host
    return label.charAt(0).toUpperCase() + label.slice(1)
  } catch {
    return 'Job Portal'
  }
}

function isSkippablePortalLabel(value) {
  const normalized = String(value ?? '').trim().toLowerCase()
  if (!normalized) {
    return true
  }
  return /^(apis?\s*found|api|notes?|status|n\/?a|none|-|—|link|url|portal|name)$/i.test(normalized)
}

function resolvePortalColumns(headerRow) {
  const cells = headerRow.map((cell) => String(cell ?? '').trim().toLowerCase())
  const urlCol = cells.findIndex((cell) => (
    (cell === 'url'
    || cell.includes('portal url')
    || cell.includes('job board url')
    || cell === 'link'
    || cell.includes('website'))
    && !cell.includes('api')
  ))
  const nameCol = cells.findIndex((cell) => (
    (cell === 'name'
    || cell.includes('portal name')
    || cell === 'portal'
    || cell.includes('job board')
    || cell.includes('source'))
    && !cell.includes('api')
  ))
  return {
    urlCol: urlCol >= 0 ? urlCol : 0,
    nameCol: nameCol >= 0 ? nameCol : 1,
  }
}

function parsePortalMatrixRow(line, columns) {
  if (!Array.isArray(line) || !line.length) {
    return null
  }

  const cells = line.map((cell) => String(cell ?? '').trim())
  if (!cells.some(Boolean)) {
    return null
  }

  let url = String(cells[columns.urlCol] ?? '').trim()
  if (!isValidPortalUrl(url)) {
    url = cells.find((cell) => isValidPortalUrl(cell)) ?? ''
  }
  if (!isValidPortalUrl(url)) {
    return null
  }

  let name = String(cells[columns.nameCol] ?? '').trim()
  if (!name || isSkippablePortalLabel(name) || isValidPortalUrl(name) || name === url) {
    name = cells.find((cell) => (
      cell
      && !isSkippablePortalLabel(cell)
      && !isValidPortalUrl(cell)
      && cell !== url
    )) ?? ''
  }
  if (!name || isSkippablePortalLabel(name)) {
    name = hostnameFromUrl(url)
  }

  return { name, url }
}

function parseWorksheetRows(matrix) {
  if (!Array.isArray(matrix) || !matrix.length) {
    return []
  }

  let startIndex = 0
  let columns = { urlCol: 0, nameCol: 1 }

  for (let index = 0; index < Math.min(matrix.length, 8); index += 1) {
    const row = matrix[index]
    if (!Array.isArray(row)) {
      continue
    }
    const headerCells = row.map((cell) => String(cell ?? '').trim().toLowerCase())
    const looksLikeHeader = headerCells.some((cell) => (
      cell.includes('url')
      || cell.includes('link')
      || cell.includes('portal')
      || cell.includes('name')
      || cell.includes('api')
    ))
    if (looksLikeHeader) {
      columns = resolvePortalColumns(row)
      startIndex = index + 1
      break
    }
  }

  const rows = []
  const seen = new Set()

  for (let index = startIndex; index < matrix.length; index += 1) {
    const parsed = parsePortalMatrixRow(matrix[index], columns)
    if (!parsed) {
      continue
    }
    const key = `${parsed.name.toLowerCase()}|${parsed.url.toLowerCase()}`
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    rows.push(parsed)
  }

  return rows
}

export async function readImportFile(file) {
  if (!file) {
    return { text: '', rows: [] }
  }

  const lowered = file.name.toLowerCase()
  if (lowered.endsWith('.xlsx') || lowered.endsWith('.xls')) {
    const XLSX = await import('xlsx')
    const buffer = await file.arrayBuffer()
    const workbook = XLSX.read(buffer, { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    const matrix = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })
    return { text: '', rows: parseWorksheetRows(matrix) }
  }

  const text = await file.text()
  return { text, rows: parseSpreadsheetRows(text) }
}

export function mergeUniqueTitles(existing, incoming) {
  const seen = new Set(existing.map((item) => item.trim().toLowerCase()))
  const merged = [...existing]

  incoming.forEach((title) => {
    const normalized = title.trim()
    if (!normalized) {
      return
    }
    const key = normalized.toLowerCase()
    if (!seen.has(key)) {
      seen.add(key)
      merged.push(normalized)
    }
  })

  return merged
}

export function mergeUniqueSkills(existing, incoming) {
  return mergeUniqueTitles(existing, incoming)
}

export function downloadTextFile(filename, content) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function sortLinkedInJobs(rows, sortKey) {
  const sorted = [...rows]
  if (sortKey === 'recent') {
    sorted.sort((left, right) => String(left.posted ?? left.datePosted ?? '').localeCompare(String(right.posted ?? right.datePosted ?? '')))
  } else if (sortKey === 'applicants') {
    sorted.sort((left, right) => (right.applicants ?? 0) - (left.applicants ?? 0))
  } else {
    sorted.sort((left, right) => (right.match ?? 0) - (left.match ?? 0))
  }
  return sorted
}

export function countSearchConfigItems(searchConfig) {
  if (!searchConfig) {
    return 0
  }
  return (
    (searchConfig.titles?.length ?? 0)
    + (searchConfig.requiredSkills?.length ?? 0)
    + (searchConfig.optionalSkills?.length ?? 0)
  )
}

export function mapYearsToExperienceText(years) {
  if (years == null || Number.isNaN(Number(years))) {
    return null
  }
  const value = Number(years)
  if (value <= 0) {
    return null
  }
  if (Number.isInteger(value)) {
    return `${value} years`
  }
  return `${value} years`
}

export function formatMatchSource(source) {
  if (!source) {
    return null
  }
  const labels = {
    embeddings: 'Embeddings',
    'embeddings+llm': 'Embeddings + AI',
    ml: 'ML fallback',
    'llm+ml': 'AI + ML',
  }
  return labels[source] ?? source
}

export function formatPipelineMatchSource(source, llmUsed) {
  if (source === 'embeddings+llm' || source === 'llm+ml' || llmUsed) {
    return 'Embeddings + AI reasoning'
  }
  if (source === 'embeddings') {
    return 'Embeddings only'
  }
  if (source === 'ml') {
    return 'ML fallback'
  }
  return 'Matching'
}
