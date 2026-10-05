export function isNonEmpty(value, minLength = 1) {
  return typeof value === 'string' && value.trim().length >= minLength
}

export function isEmail(value) {
  if (typeof value !== 'string') {
    return false
  }
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

export function isHttpUrl(value) {
  if (typeof value !== 'string') {
    return false
  }
  try {
    const parsed = new URL(value.trim())
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

export function isLinkedInUrl(value) {
  if (!isHttpUrl(value)) {
    return false
  }
  return /linkedin\.com/i.test(value.trim())
}

export function isPhone(value, minLength = 6) {
  if (typeof value !== 'string') {
    return false
  }
  const digits = value.replace(/\D/g, '')
  return digits.length >= minLength
}

export function isPassword(value, minLength = 6) {
  return isNonEmpty(value, minLength)
}

export function isPositiveInt(value, min = 1, max = 9999) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed >= min && parsed <= max
}

export function isPort(value) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed >= 1 && parsed <= 65535
}

export function isDateRangeValid(start, end) {
  if (!start || !end) {
    return true
  }
  return start <= end
}

export function isMonthRangeValid(startMonth, endMonth) {
  if (!startMonth || !endMonth) {
    return true
  }
  return startMonth <= endMonth
}

export function isRequiredDate(value) {
  return typeof value === 'string' && value.trim().length > 0
}

export function isRequiredMonth(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}$/.test(value.trim())
}

export function pickFirstError(errors) {
  return Object.values(errors).find(Boolean) ?? ''
}

export function validateLoginForm({ email, password }) {
  const errors = {}
  if (!isEmail(email)) {
    errors.email = 'Enter a valid email address.'
  }
  if (!isPassword(password)) {
    errors.password = 'Password must be at least 6 characters.'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

export function validateRegisterForm({ name, email, password, role }) {
  const errors = {}
  if (!isNonEmpty(name, 2)) {
    errors.name = 'Name must be at least 2 characters.'
  }
  if (!isEmail(email)) {
    errors.email = 'Enter a valid email address.'
  }
  if (!isPassword(password)) {
    errors.password = 'Password must be at least 6 characters.'
  }
  if (!isNonEmpty(role, 1)) {
    errors.role = 'Select a role.'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

export function validateUserProfileForm(form) {
  const errors = {}
  if (!isNonEmpty(form.name, 2)) {
    errors.name = 'Name must be at least 2 characters.'
  }
  if (form.phone && !isPhone(form.phone)) {
    errors.phone = 'Enter a valid phone number (6+ digits).'
  }
  if (form.location && !isNonEmpty(form.location, 2)) {
    errors.location = 'Location must be at least 2 characters.'
  }
  if (form.bio && form.bio.length > 500) {
    errors.bio = 'Bio must be 500 characters or fewer.'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

export function validatePasswordChangeForm({ currentPassword, newPassword, confirmPassword }) {
  const errors = {}
  if (!isPassword(currentPassword)) {
    errors.currentPassword = 'Current password is required (6+ characters).'
  }
  if (!isPassword(newPassword)) {
    errors.newPassword = 'New password must be at least 6 characters.'
  }
  if (newPassword !== confirmPassword) {
    errors.confirmPassword = 'Passwords do not match.'
  }
  if (currentPassword && newPassword && currentPassword === newPassword) {
    errors.newPassword = 'New password must differ from current password.'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

export function validateLinkedInSettings(settings) {
  const errors = {}
  if (settings?.accountEmail && !isEmail(settings.accountEmail)) {
    errors.accountEmail = 'Account email must be valid.'
  }
  if (settings?.maxPerDay !== undefined && !isPositiveInt(settings.maxPerDay, 1, 500)) {
    errors.maxPerDay = 'Max per day must be between 1 and 500.'
  }
  if (settings?.delaySeconds !== undefined && !isPositiveInt(settings.delaySeconds, 1, 600)) {
    errors.delaySeconds = 'Delay must be between 1 and 600 seconds.'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

export function validateLinkedInPasteUrl(url) {
  const errors = {}
  if (!isNonEmpty(url, 10)) {
    errors.pasteUrl = 'Paste a LinkedIn profile URL.'
  } else if (!isLinkedInUrl(url)) {
    errors.pasteUrl = 'URL must be a valid LinkedIn profile link (https://linkedin.com/...).'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

export function validateSmtpSettings(settings) {
  const errors = {}
  if (!isNonEmpty(settings.smtpHost, 3)) {
    errors.smtpHost = 'SMTP host is required.'
  }
  if (!isPort(settings.smtpPort)) {
    errors.smtpPort = 'SMTP port must be between 1 and 65535.'
  }
  if (!isPositiveInt(settings.senderLimit, 1, 100000)) {
    errors.senderLimit = 'Sender limit must be a positive number.'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

export function validateDayReportFilters({ start, end }) {
  const errors = {}
  if (start && !isRequiredDate(start)) {
    errors.start = 'Start date must be a valid date.'
  }
  if (end && !isRequiredDate(end)) {
    errors.end = 'End date must be a valid date.'
  }
  if (isRequiredDate(start) && isRequiredDate(end) && !isDateRangeValid(start, end)) {
    errors.end = 'End date cannot be before start date.'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

export function validateSubmissionFilters({ startMonth, endMonth }) {
  const errors = {}
  if (!isRequiredMonth(startMonth)) {
    errors.startMonth = 'Start month is required.'
  }
  if (!isRequiredMonth(endMonth)) {
    errors.endMonth = 'End month is required.'
  }
  if (isRequiredMonth(startMonth) && isRequiredMonth(endMonth) && !isMonthRangeValid(startMonth, endMonth)) {
    errors.endMonth = 'End month cannot be before start month.'
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}
