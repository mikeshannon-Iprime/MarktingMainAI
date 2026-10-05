export function extractNumeric(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const match = value.match(/-?\d+(\.\d+)?/)
    return match ? Number(match[0]) : 0
  }
  return 0
}

export function fmtInt(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '-'
  }
  return Math.round(value).toLocaleString()
}

export function aggregateByDay(rows) {
  const grouped = new Map()

  rows.forEach((row) => {
    const current = grouped.get(row.date) ?? {
      date: row.date,
      linkedin: 0,
      calls: 0,
      sourced: 0,
      marketing: 0,
    }

    current.linkedin += extractNumeric(row.linkedin)
    current.calls += extractNumeric(row.calls)
    current.sourced += extractNumeric(row.sourced)
    current.marketing += extractNumeric(row.marketing)
    grouped.set(row.date, current)
  })

  return Array.from(grouped.values()).sort((left, right) => left.date.localeCompare(right.date))
}

export function recruiterTotals(rows) {
  const grouped = new Map()

  rows.forEach((row) => {
    grouped.set(row.recruiter, (grouped.get(row.recruiter) ?? 0) + extractNumeric(row.sourced))
  })

  return Array.from(grouped.entries())
    .map(([recruiter, sourced]) => ({ recruiter, sourced }))
    .sort((left, right) => right.sourced - left.sourced)
}

/** Match HTML prototype: count each technology field as one entry (not split by comma). */
export function technologyEntryTotals(rows) {
  const grouped = new Map()

  rows.forEach((row) => {
    const key = row.technology?.trim() ? row.technology.trim() : 'Unknown'
    grouped.set(key, (grouped.get(key) ?? 0) + 1)
  })

  return Array.from(grouped.entries())
    .map(([technology, count]) => ({ technology, count }))
    .sort((left, right) => right.count - left.count)
    .slice(0, 10)
}

export function sumMetric(rows, field) {
  return rows.reduce((accumulator, row) => accumulator + extractNumeric(row[field]), 0)
}

export function resolveDefaultDayRange(workspace) {
  if (workspace?.defaultRange?.start && workspace?.defaultRange?.end) {
    return workspace.defaultRange
  }
  if (workspace?.range?.start && workspace?.range?.end) {
    return workspace.range
  }
  return { start: '', end: '' }
}

export function buildSubmissionCalendar(months = []) {
  const lookup = new Map(months.map((row) => [row.month, row]))
  const years = [...new Set(months.map((row) => row.month.slice(0, 4)))].sort()
  const maxSubmissions = Math.max(...months.map((row) => row.submissions), 1)

  return years.map((year) => ({
    year,
    maxSubmissions,
    cells: Array.from({ length: 12 }, (_, index) => {
      const month = `${year}-${String(index + 1).padStart(2, '0')}`
      const row = lookup.get(month)
      return {
        month,
        label: new Date(`${month}-01T00:00:00`).toLocaleString(undefined, { month: 'short' }),
        submissions: row?.submissions ?? null,
        mom: row?.mom ?? null,
        yoy: row?.yoy ?? null,
        intensity: row ? row.submissions / maxSubmissions : 0,
      }
    }),
  }))
}

export function toneDelta(value) {
  if (value === null || value === undefined) {
    return 'neutral'
  }
  return value >= 0 ? 'positive' : 'negative'
}
