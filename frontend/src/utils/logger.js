const isDev = import.meta.env.DEV
const configuredLevel = (import.meta.env.VITE_LOG_LEVEL ?? (isDev ? 'debug' : 'warn')).toLowerCase()

const LEVELS = { debug: 0, info: 1, warn: 2, error: 3 }

function shouldLog(level) {
  return (LEVELS[level] ?? 0) >= (LEVELS[configuredLevel] ?? 0)
}

function formatContext(context) {
  if (!context || typeof context !== 'object') {
    return ''
  }
  try {
    return JSON.stringify(context)
  } catch {
    return String(context)
  }
}

export const logger = {
  debug(message, context) {
    if (shouldLog('debug')) {
      console.debug(`[MM] ${message}`, context ?? '')
    }
  },
  info(message, context) {
    if (shouldLog('info')) {
      console.info(`[MM] ${message}`, context ?? '')
    }
  },
  warn(message, context) {
    if (shouldLog('warn')) {
      console.warn(`[MM] ${message}`, context ?? '')
    }
  },
  error(error, context = {}) {
    if (!shouldLog('error')) {
      return
    }
    const message = error instanceof Error ? error.message : String(error)
    console.error(`[MM] ${message}`, {
      ...context,
      stack: error instanceof Error ? error.stack : undefined,
    })
  },
  apiFailure(error, context = {}) {
    const status = error?.response?.status
    const method = error?.config?.method?.toUpperCase() ?? 'GET'
    const url = error?.config?.url ?? 'unknown'
    this.error(error, {
      ...context,
      status,
      method,
      url,
      detail: formatContext(error?.response?.data?.detail),
    })
  },
}

export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error) {
    return fallback
  }
  if (typeof error === 'string') {
    return error
  }
  if (error.message) {
    return error.message
  }
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg ?? JSON.stringify(item)).join('; ')
  }
  return fallback
}
