import { describe, expect, it } from 'vitest'

import {
  isDateRangeValid,
  isEmail,
  isLinkedInUrl,
  isMonthRangeValid,
  isPhone,
  isRequiredMonth,
  validateDayReportFilters,
  validateLoginForm,
  validateSubmissionFilters,
  validateUserProfileForm,
} from './validators'

describe('FUNCTIONAL_TEST_CASES — validators', () => {
  describe('SP-FLT-04/05 submission filters', () => {
    it('rejects end month before start month', () => {
      const result = validateSubmissionFilters({ startMonth: '2026-05', endMonth: '2026-01' })
      expect(result.isValid).toBe(false)
      expect(result.errors.endMonth).toMatch(/cannot be before/i)
    })

    it('requires start month', () => {
      const result = validateSubmissionFilters({ startMonth: '', endMonth: '2026-05' })
      expect(result.isValid).toBe(false)
      expect(result.errors.startMonth).toBeTruthy()
    })

    it('accepts valid month range', () => {
      const result = validateSubmissionFilters({ startMonth: '2026-01', endMonth: '2026-05' })
      expect(result.isValid).toBe(true)
    })
  })

  describe('DR-FLT day report filters', () => {
    it('rejects end before start date', () => {
      const result = validateDayReportFilters({ start: '2026-05-01', end: '2026-04-01' })
      expect(result.isValid).toBe(false)
      expect(result.errors.end).toMatch(/cannot be before/i)
    })

    it('accepts valid date range', () => {
      const result = validateDayReportFilters({ start: '2026-01-13', end: '2026-02-16' })
      expect(result.isValid).toBe(true)
    })

    it('accepts open-ended date ranges', () => {
      expect(validateDayReportFilters({ start: '', end: '2026-02-16' }).isValid).toBe(true)
      expect(validateDayReportFilters({ start: '2026-01-13', end: '' }).isValid).toBe(true)
      expect(validateDayReportFilters({ start: '', end: '' }).isValid).toBe(true)
    })
  })

  describe('JA-PRF / CM auth validation', () => {
    it('validates login email and password', () => {
      expect(validateLoginForm({ email: 'user@test.com', password: 'secret' }).isValid).toBe(true)
      expect(validateLoginForm({ email: 'bad', password: 'x' }).isValid).toBe(false)
    })

    it('validates user profile phone optional', () => {
      const valid = validateUserProfileForm({
        name: 'John Smith',
        phone: '+1 (555) 123-4567',
        location: 'Dallas',
        bio: '',
      })
      expect(valid.isValid).toBe(true)

      const invalid = validateUserProfileForm({ name: 'J', phone: '123', location: '', bio: '' })
      expect(invalid.isValid).toBe(false)
    })
  })

  describe('LI paste URL validation', () => {
    it('accepts linkedin profile URLs', () => {
      expect(isLinkedInUrl('https://www.linkedin.com/in/recruiter')).toBe(true)
    })

    it('rejects non-linkedin URLs', () => {
      expect(isLinkedInUrl('https://example.com/profile')).toBe(false)
    })
  })

  describe('primitive helpers', () => {
    it('isRequiredMonth matches YYYY-MM', () => {
      expect(isRequiredMonth('2026-03')).toBe(true)
      expect(isRequiredMonth('2026-3')).toBe(false)
    })

    it('isMonthRangeValid ordering', () => {
      expect(isMonthRangeValid('2026-01', '2026-05')).toBe(true)
      expect(isMonthRangeValid('2026-05', '2026-01')).toBe(false)
    })

    it('isDateRangeValid ordering', () => {
      expect(isDateRangeValid('2026-01-01', '2026-02-01')).toBe(true)
      expect(isDateRangeValid('2026-02-01', '2026-01-01')).toBe(false)
    })

    it('isEmail and isPhone', () => {
      expect(isEmail('recruiter@techstaff.com')).toBe(true)
      expect(isPhone('+1 (555) 555-0128')).toBe(true)
      expect(isPhone('123')).toBe(false)
    })
  })
})
