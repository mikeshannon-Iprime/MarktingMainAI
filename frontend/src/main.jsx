import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { ErrorBoundary } from './components/ErrorBoundary.jsx'
import { logger } from './utils/logger.js'

window.addEventListener('unhandledrejection', (event) => {
  logger.error(event.reason, { type: 'unhandledrejection' })
})

window.addEventListener('error', (event) => {
  logger.error(event.error ?? event.message, {
    type: 'window_error',
    filename: event.filename,
    lineno: event.lineno,
  })
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
)
