import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { startTransition, useCallback, useEffect, useMemo, useState } from 'react'

import { filterSubmissionsDashboard } from '../api/client'
import { buildSubmissionCalendar, toneDelta } from '../utils/reportingHelpers'
import { validateSubmissionFilters } from '../utils/validators'

function SubmissionCalendar({ years, activeMonth, onSelectMonth }) {
  return (
    <div className="submission-calendar">
      <div className="submission-calendar-header">
        <span />
        {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
      {years.map((yearRow) => (
        <div key={yearRow.year} className="submission-calendar-row">
          <span className="submission-calendar-year">{yearRow.year}</span>
          {yearRow.cells.map((cell) => {
            const hasData = cell.submissions !== null
            const isActive = activeMonth === cell.month
            return (
              <button
                key={cell.month}
                type="button"
                className={`submission-calendar-cell${isActive ? ' active' : ''}${hasData ? '' : ' empty'}`}
                style={
                  hasData
                    ? {
                        background: `rgba(255, 148, 87, ${0.15 + cell.intensity * 0.75})`,
                        borderColor: `rgba(255, 148, 87, ${0.35 + cell.intensity * 0.5})`,
                      }
                    : undefined
                }
                title={
                  hasData
                    ? `${cell.month}: ${cell.submissions} submissions`
                    : `${cell.month}: no data`
                }
                onClick={() => hasData && onSelectMonth(cell.month)}
              >
                {hasData ? cell.submissions : '·'}
              </button>
            )
          })}
        </div>
      ))}
    </div>
  )
}

export function SubmissionProgressPage({ workspace }) {
  const [startMonth, setStartMonth] = useState('')
  const [endMonth, setEndMonth] = useState('')
  const [rangeText, setRangeText] = useState('')
  const [months, setMonths] = useState([])
  const [summary, setSummary] = useState({ total: 0, average: 0 })
  const [busy, setBusy] = useState(false)
  const [validationMessage, setValidationMessage] = useState('')

  const applyFilterRequest = useCallback(async (payload, label) => {
    setBusy(true)
    setValidationMessage('')
    try {
      const response = await filterSubmissionsDashboard(payload)
      setMonths(response.months ?? [])
      setSummary(response.summary ?? { total: 0, average: 0 })
      setRangeText(label)
    } catch (err) {
      const locallyFiltered = (workspace?.months ?? []).filter((row) => {
        const afterStart = !payload.startMonth || row.month >= payload.startMonth
        const beforeEnd = !payload.endMonth || row.month <= payload.endMonth
        return afterStart && beforeEnd
      })
      const total = locallyFiltered.reduce((sum, row) => sum + row.submissions, 0)
      setMonths(locallyFiltered)
      setSummary({
        total,
        average: locallyFiltered.length ? Math.round(total / locallyFiltered.length) : 0,
      })
      setRangeText(label)
      setValidationMessage(err.message || 'Filter failed — showing local results.')
    } finally {
      setBusy(false)
    }
  }, [workspace])

  useEffect(() => {
    if (!workspace) {
      return
    }

    const start = workspace.range?.start ?? ''
    const end = workspace.range?.end ?? ''
    startTransition(() => {
      setStartMonth(start)
      setEndMonth(end)
      setMonths(workspace.months ?? [])
      setSummary(workspace.summary ?? {
        total: (workspace.months ?? []).reduce((sum, row) => sum + row.submissions, 0),
        average: workspace.months?.length
          ? Math.round((workspace.months ?? []).reduce((sum, row) => sum + row.submissions, 0) / workspace.months.length)
          : 0,
      })
      setRangeText(`${start} to ${end}`)
    })
  }, [workspace])

  const calendarYears = useMemo(() => buildSubmissionCalendar(workspace?.months ?? []), [workspace])

  if (!workspace) {
    return null
  }

  const applyFilters = async () => {
    const validation = validateSubmissionFilters({ startMonth, endMonth })
    if (!validation.isValid) {
      setValidationMessage(Object.values(validation.errors).find(Boolean) ?? 'Invalid month range.')
      return
    }

    await applyFilterRequest(
      { startMonth: startMonth || null, endMonth: endMonth || null },
      `${startMonth || workspace.range.start} to ${endMonth || workspace.range.end}`,
    )
  }

  const resetFilters = async () => {
    const start = workspace.range.start
    const end = workspace.range.end
    setStartMonth(start)
    setEndMonth(end)
    await applyFilterRequest({ startMonth: start, endMonth: end }, `${start} to ${end}`)
  }

  const selectCalendarMonth = (month) => {
    setStartMonth(month)
    setEndMonth(month)
    applyFilterRequest({ startMonth: month, endMonth: month }, month)
  }

  return (
    <div className="page-stack submission-progress-page">
      <section className="hero-panel compact">
        <div>
          <p className="eyebrow">Submission Progress Dashboard</p>
          <h3>MoM and YoY tracking with calendar month filtering.</h3>
          <p className="hero-copy">Filtered range: {rangeText}</p>
        </div>
      </section>

      <section className="glass-card day-report-controls">
        {validationMessage ? <div className="banner error">{validationMessage}</div> : null}
        <div className="form-grid day-filter-grid">
          <label>
            Start month
            <input
              type="month"
              value={startMonth}
              min={workspace.range.start}
              max={workspace.range.end}
              onChange={(event) => setStartMonth(event.target.value)}
            />
          </label>
          <label>
            End month
            <input
              type="month"
              value={endMonth}
              min={workspace.range.start}
              max={workspace.range.end}
              onChange={(event) => setEndMonth(event.target.value)}
            />
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

      <section className="stat-row two-up">
        <article className="metric-card">
          <span>Total submissions</span>
          <strong>{summary.total}</strong>
        </article>
        <article className="metric-card">
          <span>Average per month</span>
          <strong>{summary.average}</strong>
        </article>
      </section>

      <article className="glass-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Calendar view</p>
            <h4>Submission intensity by month — click a cell to filter</h4>
          </div>
        </div>
        <SubmissionCalendar
          years={calendarYears}
          activeMonth={startMonth === endMonth ? startMonth : ''}
          onSelectMonth={selectCalendarMonth}
        />
      </article>

      <section className="chart-grid">
        <article className="glass-card chart-card span-two">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Trend line</p>
              <h4>Submission volume by month</h4>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={months}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="month" stroke="#98a4d3" />
              <YAxis stroke="#98a4d3" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="submissions" stroke="#ff9457" strokeWidth={3} name="Submissions" />
            </LineChart>
          </ResponsiveContainer>
        </article>

        <article className="glass-card chart-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">MoM</p>
              <h4>Month over month change</h4>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={months}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="month" stroke="#98a4d3" />
              <YAxis stroke="#98a4d3" />
              <Tooltip />
              <Bar dataKey="mom" radius={[8, 8, 0, 0]}>
                {months.map((entry) => (
                  <Cell
                    key={entry.month}
                    fill={entry.mom === null ? '#64748b' : entry.mom >= 0 ? '#30c0c7' : '#ff9457'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article className="glass-card chart-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">YoY</p>
              <h4>Year over year change</h4>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={months}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="month" stroke="#98a4d3" />
              <YAxis stroke="#98a4d3" />
              <Tooltip formatter={(value) => (value === null ? 'N/A' : `${value}%`)} />
              <Legend />
              <Line
                type="monotone"
                dataKey="yoy"
                stroke="#30c0c7"
                strokeWidth={3}
                connectNulls={false}
                name="YoY %"
                dot={{ fill: '#30c0c7', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </article>
      </section>

      <article className="glass-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Monthly table</p>
            <h4>Submission deltas</h4>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Month</th>
                <th>Submissions</th>
                <th>MoM</th>
                <th>YoY</th>
              </tr>
            </thead>
            <tbody>
              {months.map((row) => (
                <tr key={row.month}>
                  <td>{row.month}</td>
                  <td>{row.submissions}</td>
                  <td>
                    <span className={`delta-pill ${toneDelta(row.mom)}`}>
                      {row.mom === null ? 'N/A' : `${row.mom}%`}
                    </span>
                  </td>
                  <td>
                    <span className={`delta-pill ${toneDelta(row.yoy)}`}>
                      {row.yoy === null ? 'N/A' : `${row.yoy}%`}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </div>
  )
}
