import { describe, expect, it } from 'vitest'

import {
  aggregateByDay,
  buildSubmissionCalendar,
  extractNumeric,
  fmtInt,
  recruiterTotals,
  sumMetric,
  technologyEntryTotals,
  toneDelta,
} from './reportingHelpers'

const SAMPLE_ROWS = [
  {
    date: '2026-02-16',
    recruiter: 'Sam',
    technology: 'Data Engineer',
    linkedin: 15,
    calls: 12,
    sourced: 2,
    marketing: 1,
  },
  {
    date: '2026-02-16',
    recruiter: 'Komal',
    technology: 'AI Engineer',
    linkedin: 15,
    calls: 10,
    sourced: 3,
    marketing: 0,
  },
]

describe('FUNCTIONAL_TEST_CASES — reportingHelpers', () => {
  describe('DR-FLT-02 Sam single day KPIs', () => {
    it('sums metrics for one recruiter on one day', () => {
      const samOnly = SAMPLE_ROWS.filter((row) => row.recruiter === 'Sam')
      expect(sumMetric(samOnly, 'linkedin')).toBe(15)
      expect(sumMetric(samOnly, 'calls')).toBe(12)
      expect(sumMetric(samOnly, 'sourced')).toBe(2)
      expect(sumMetric(samOnly, 'marketing')).toBe(1)
    })

    it('aggregates by day across recruiters', () => {
      const byDay = aggregateByDay(SAMPLE_ROWS)
      expect(byDay).toHaveLength(1)
      expect(byDay[0].linkedin).toBe(30)
      expect(byDay[0].calls).toBe(22)
    })
  })

  describe('DR-CHT recruiter and tech charts', () => {
    it('ranks recruiters by sourced total', () => {
      const totals = recruiterTotals(SAMPLE_ROWS)
      expect(totals[0].recruiter).toBe('Komal')
      expect(totals[0].sourced).toBe(3)
    })

    it('counts technology entries', () => {
      const tech = technologyEntryTotals(SAMPLE_ROWS)
      expect(tech).toHaveLength(2)
      expect(tech[0].count).toBe(1)
    })
  })

  describe('SP calendar and MoM display', () => {
    const months = [
      { month: '2026-01', submissions: 31, mom: null, yoy: null },
      { month: '2026-02', submissions: 34, mom: 9.7, yoy: null },
      { month: '2026-03', submissions: 39, mom: 14.7, yoy: null },
    ]

    it('builds calendar cells with intensity', () => {
      const years = buildSubmissionCalendar(months)
      expect(years).toHaveLength(1)
      const feb = years[0].cells.find((cell) => cell.month === '2026-02')
      expect(feb.submissions).toBe(34)
      expect(feb.intensity).toBeGreaterThan(0)
    })

    it('toneDelta for MoM/YoY pills', () => {
      expect(toneDelta(9.7)).toBe('positive')
      expect(toneDelta(-5)).toBe('negative')
      expect(toneDelta(null)).toBe('neutral')
    })
  })

  describe('fmtInt and extractNumeric', () => {
    it('extracts first number from free text', () => {
      expect(extractNumeric('20calls')).toBe(20)
      expect(extractNumeric(null)).toBe(0)
    })

    it('formats integers for KPI display', () => {
      expect(fmtInt(1234)).toBe('1,234')
      expect(fmtInt(null)).toBe('-')
    })
  })
})
