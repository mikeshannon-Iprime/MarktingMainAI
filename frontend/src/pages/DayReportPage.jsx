import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { filterDayReportDashboard } from '../api/client'
import {
  aggregateByDay,
  extractNumeric,
  fmtInt,
  recruiterTotals,
  resolveDefaultDayRange,
  sumMetric,
  technologyEntryTotals,
} from '../utils/reportingHelpers'
import { validateDayReportFilters } from '../utils/validators'

function formatActivityMetric(value) {
  return value === null || value === undefined || value === '' ? '-' : fmtInt(extractNumeric(value))
}

export function DayReportPage({ workspace }) {
  const [draftStart, setDraftStart] = useState('')
  const [draftEnd, setDraftEnd] = useState('')
  const [draftRecruiter, setDraftRecruiter] = useState('__all__')
  const [rangeText, setRangeText] = useState('')
  const [busy, setBusy] = useState(false)
  const [rows, setRows] = useState([])
  const [recruiters, setRecruiters] = useState([])
  const [bounds, setBounds] = useState({ start: '', end: '' })
  const [validationMessage, setValidationMessage] = useState('')

  const applyFilterRequest = useCallback(async (payload, rangeLabel) => {
    setBusy(true)
    setValidationMessage('')
    try {
      const response = await filterDayReportDashboard(payload)
      setRows(response.rows ?? [])
      setRecruiters(response.recruiters ?? [])
      setRangeText(rangeLabel)
    } catch (err) {
      const locallyFiltered = (workspace?.rows ?? []).filter((row) => {
        const afterStart = !payload.start || row.date >= payload.start
        const beforeEnd = !payload.end || row.date <= payload.end
        const recruiterMatch = !payload.recruiter || row.recruiter === payload.recruiter
        return afterStart && beforeEnd && recruiterMatch
      })
      setRows(locallyFiltered)
      setRangeText(rangeLabel)
      setValidationMessage(err.message || 'Filter failed — showing local results.')
    } finally {
      setBusy(false)
    }
  }, [workspace])

  useEffect(() => {
    if (!workspace) {
      return
    }

    setRecruiters(workspace.recruiters ?? [])
    setBounds(workspace.bounds ?? workspace.range ?? { start: '', end: '' })

    const defaults = resolveDefaultDayRange(workspace)
    setDraftStart(defaults.start)
    setDraftEnd(defaults.end)
    setDraftRecruiter('__all__')

    applyFilterRequest(
      { start: defaults.start, end: defaults.end, recruiter: null },
      `${defaults.start} to ${defaults.end}`,
    )
  }, [workspace, applyFilterRequest])

  if (!workspace) {
    return null
  }

  const applyFilters = async () => {
    const validation = validateDayReportFilters({ start: draftStart, end: draftEnd })
    if (!validation.isValid) {
      setValidationMessage(Object.values(validation.errors).find(Boolean) ?? 'Invalid date range.')
      return
    }

    await applyFilterRequest(
      {
        start: draftStart || null,
        end: draftEnd || null,
        recruiter: draftRecruiter === '__all__' ? null : draftRecruiter,
      },
      `${draftStart || bounds.start} to ${draftEnd || bounds.end}`,
    )
  }

  const resetFilters = async () => {
    const defaults = resolveDefaultDayRange(workspace)
    setDraftStart(defaults.start)
    setDraftEnd(defaults.end)
    setDraftRecruiter('__all__')
    await applyFilterRequest(
      { start: defaults.start, end: defaults.end, recruiter: null },
      `${defaults.start} to ${defaults.end}`,
    )
  }

  const totals = useMemo(
    () => ({
      linkedin: sumMetric(rows, 'linkedin'),
      calls: sumMetric(rows, 'calls'),
      sourced: sumMetric(rows, 'sourced'),
      marketing: sumMetric(rows, 'marketing'),
    }),
    [rows],
  )

  const trendRows = useMemo(() => aggregateByDay(rows), [rows])
  const recruiterRows = useMemo(() => recruiterTotals(rows), [rows])
  const technologyRows = useMemo(() => technologyEntryTotals(rows), [rows])
  const recentRows = useMemo(
    () => [...rows].sort((left, right) => right.date.localeCompare(left.date)).slice(0, 25),
    [rows],
  )

  return (
    <div className="page-stack day-report-page">
      <section className="hero-panel compact">
        <div>
          <p className="eyebrow">DAY TO DAY REPORT Dashboard</p>
          <h3>Filters drive all charts and KPI cards.</h3>
          <p className="hero-copy">Data range: {rangeText}</p>
        </div>
      </section>

      <section className="glass-card day-report-controls">
        {validationMessage ? <div className="banner error">{validationMessage}</div> : null}
        <div className="form-grid day-filter-grid">
          <label>
            Start date
            <input
              type="date"
              min={bounds.start}
              max={bounds.end}
              value={draftStart}
              onChange={(event) => setDraftStart(event.target.value)}
            />
          </label>
          <label>
            End date
            <input
              type="date"
              min={bounds.start}
              max={bounds.end}
              value={draftEnd}
              onChange={(event) => setDraftEnd(event.target.value)}
            />
          </label>
          <label>
            Recruiter
            <select value={draftRecruiter} onChange={(event) => setDraftRecruiter(event.target.value)}>
              <option value="__all__">All</option>
              {recruiters.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <div className="button-row">
            <button className="primary-button" type="button" disabled={busy} onClick={applyFilters}>
              {busy ? 'Applying...' : 'Apply'}
            </button>
            <button className="secondary-button" type="button" disabled={busy} onClick={resetFilters}>
              Reset
            </button>
          </div>
        </div>
      </section>

      <section className="stat-row four-up">
        <article className="metric-card">
          <span>Total Linkedin Connections</span>
          <strong>{fmtInt(totals.linkedin)}</strong>
          <small>Filtered period</small>
        </article>
        <article className="metric-card">
          <span>Total Daily Calls</span>
          <strong>{fmtInt(totals.calls)}</strong>
          <small>Filtered period</small>
        </article>
        <article className="metric-card">
          <span>Total Sourced Data</span>
          <strong>{fmtInt(totals.sourced)}</strong>
          <small>Filtered period</small>
        </article>
        <article className="metric-card">
          <span>Total Marketing/Submissions</span>
          <strong>{fmtInt(totals.marketing)}</strong>
          <small>Filtered period</small>
        </article>
      </section>

      <section className="chart-grid">
        <article className="glass-card chart-card span-two">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Daily trend</p>
              <h4>Totals across filtered period</h4>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={trendRows}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="date" stroke="#98a4d3" />
              <YAxis stroke="#98a4d3" />
              <Tooltip
                cursor={{ stroke: 'rgba(152, 164, 211, 0.45)', strokeWidth: 1 }}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Legend />
              <Line type="monotone" dataKey="sourced" stroke="#2dd4bf" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} name="Sourced Data" />
              <Line type="monotone" dataKey="calls" stroke="#ff7a18" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} name="Daily Calls" />
              <Line type="monotone" dataKey="linkedin" stroke="#8b5cf6" strokeWidth={2} strokeDasharray="4 4" dot={false} activeDot={{ r: 4 }} name="Linkedin Connections" />
              <Line type="monotone" dataKey="marketing" stroke="#60a5fa" strokeWidth={2} strokeDasharray="6 3" dot={false} activeDot={{ r: 4 }} name="Marketing/Submissions" />
            </LineChart>
          </ResponsiveContainer>
        </article>

        <article className="glass-card chart-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Recruiter totals</p>
              <h4>Sourced Data</h4>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={recruiterRows} layout="vertical">
              <CartesianGrid stroke="rgba(255,255,255,0.08)" horizontal={false} />
              <XAxis type="number" stroke="#98a4d3" />
              <YAxis type="category" dataKey="recruiter" stroke="#98a4d3" width={90} />
              <Tooltip />
              <Bar dataKey="sourced" fill="#2dd4bf" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article className="glass-card chart-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Metric mix</p>
              <h4>Stacked by day</h4>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={trendRows}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="date" stroke="#98a4d3" />
              <YAxis stroke="#98a4d3" />
              <Tooltip />
              <Legend />
              <Bar dataKey="sourced" stackId="mix" fill="#2dd4bf" name="Sourced Data" />
              <Bar dataKey="calls" stackId="mix" fill="#ff7a18" name="Daily Calls" />
              <Bar dataKey="linkedin" stackId="mix" fill="#8b5cf6" name="Linkedin" />
              <Bar dataKey="marketing" stackId="mix" fill="#60a5fa" name="Marketing" />
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article className="glass-card chart-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Top technologies</p>
              <h4>By # entries</h4>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={technologyRows} layout="vertical">
              <CartesianGrid stroke="rgba(255,255,255,0.08)" horizontal={false} />
              <XAxis type="number" stroke="#98a4d3" />
              <YAxis type="category" dataKey="technology" stroke="#98a4d3" width={140} />
              <Tooltip />
              <Bar dataKey="count" fill="#ff7a18" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </section>

      <article className="glass-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Recent activity</p>
            <h4>Latest 25 rows</h4>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Recruiter</th>
                <th>Technology</th>
                <th>Linkedin</th>
                <th>Calls</th>
                <th>Sourced</th>
                <th>Marketing</th>
                <th>Notes?</th>
              </tr>
            </thead>
            <tbody>
              {recentRows.map((row, index) => (
                <tr key={`${row.date}-${row.recruiter}-${index}`}>
                  <td>{row.date}</td>
                  <td>{row.recruiter}</td>
                  <td>{row.technology}</td>
                  <td>{formatActivityMetric(row.linkedin)}</td>
                  <td>{formatActivityMetric(row.calls)}</td>
                  <td>{formatActivityMetric(row.sourced)}</td>
                  <td>{formatActivityMetric(row.marketing)}</td>
                  <td>{row.notes?.trim() ? 'Yes' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <p className="support-copy">
        Tip: if values are messy free text, numeric extraction takes the first number it finds.
      </p>
    </div>
  )
}
