import { describe, expect, it } from 'vitest'

import { parseLinkedInCsvUrls, parseLinkedInPasteUrls } from './linkedinRecruiterHelpers'

describe('LinkedIn profile imports', () => {
  it('deduplicates pasted LinkedIn URLs', () => {
    const url = 'https://www.linkedin.com/in/example-recruiter'
    expect(parseLinkedInPasteUrls(`${url}\n${url}`)).toEqual([url])
  })

  it('extracts and normalizes LinkedIn URLs from CSV content', () => {
    const csv = [
      'name,profile_url,company',
      'Jane,https://www.linkedin.com/in/jane-recruiter,Example',
      'John,www.linkedin.com/in/john-recruiter,Example',
      'Duplicate,https://www.linkedin.com/in/jane-recruiter,Example',
    ].join('\n')

    expect(parseLinkedInCsvUrls(csv)).toEqual([
      'https://www.linkedin.com/in/jane-recruiter',
      'https://www.linkedin.com/in/john-recruiter',
    ])
  })

  it('ignores non-LinkedIn CSV values', () => {
    expect(parseLinkedInCsvUrls('name,url\nJane,https://example.com/profile')).toEqual([])
  })
})
