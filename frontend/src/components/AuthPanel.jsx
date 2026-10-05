import { useEffect, useState } from 'react'
import { Lock, LogIn, Mail, Shield, Sparkles, User, UserPlus } from 'lucide-react'

import { fetchAuthOptions, loginUser, registerUser } from '../api/client'
import { FormField } from './FormField'
import { pickFirstError, validateLoginForm, validateRegisterForm } from '../utils/validators'

export function AuthPanel({ onAuthenticated }) {
  const [mode, setMode] = useState('login')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [roles, setRoles] = useState(['super_admin', 'admin', 'user'])

  const [loginPayload, setLoginPayload] = useState({
    email: '',
    password: '',
  })

  const [registerPayload, setRegisterPayload] = useState({
    name: '',
    email: '',
    password: '',
    role: 'user',
  })

  useEffect(() => {
    const loadOptions = async () => {
      try {
        const response = await fetchAuthOptions()
        if (response?.roles?.length) {
          setRoles(response.roles)
        }
      } catch {
        // Keep fallback roles for offline/backend-down states.
      }
    }

    loadOptions()
  }, [])

  const switchMode = (nextMode) => {
    setMode(nextMode)
    setError('')
    setFieldErrors({})
  }

  const updateLoginField = (field, value) => {
    setLoginPayload((prev) => ({ ...prev, [field]: value }))
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: '' }))
    }
    if (error) {
      setError('')
    }
  }

  const updateRegisterField = (field, value) => {
    setRegisterPayload((prev) => ({ ...prev, [field]: value }))
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: '' }))
    }
    if (error) {
      setError('')
    }
  }

  const submitLogin = async (event) => {
    event.preventDefault()
    const validation = validateLoginForm(loginPayload)
    setFieldErrors(validation.errors)
    if (!validation.isValid) {
      setError(pickFirstError(validation.errors))
      return
    }

    setBusy(true)
    setError('')
    try {
      const auth = await loginUser(loginPayload)
      onAuthenticated(auth)
    } catch (requestError) {
      setError(requestError?.response?.data?.detail ?? 'Login failed. Check credentials and backend status.')
    } finally {
      setBusy(false)
    }
  }

  const submitRegister = async (event) => {
    event.preventDefault()
    const validation = validateRegisterForm(registerPayload)
    setFieldErrors(validation.errors)
    if (!validation.isValid) {
      setError(pickFirstError(validation.errors))
      return
    }

    setBusy(true)
    setError('')
    try {
      const auth = await registerUser(registerPayload)
      onAuthenticated(auth)
    } catch (requestError) {
      setError(requestError?.response?.data?.detail ?? 'Registration failed. Try a different email.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-portal">
      <div className="auth-portal-backdrop" aria-hidden="true" />

      <nav className="auth-mode-toggle" aria-label="Authentication mode">
        <button
          type="button"
          className={`auth-mode-btn${mode === 'login' ? ' active' : ''}`}
          onClick={() => switchMode('login')}
          aria-pressed={mode === 'login'}
          title="Login"
        >
          <LogIn size={18} aria-hidden="true" />
          <span>Login</span>
        </button>
        <button
          type="button"
          className={`auth-mode-btn${mode === 'register' ? ' active' : ''}`}
          onClick={() => switchMode('register')}
          aria-pressed={mode === 'register'}
          title="Register"
        >
          <UserPlus size={18} aria-hidden="true" />
          <span>Register</span>
        </button>
      </nav>

      <div className="auth-portal-center">
        <article className="auth-portal-card">
          <div className="auth-brand">
            <div className="auth-brand-mark">
              <Sparkles size={22} aria-hidden="true" />
            </div>
            <div>
              <p className="auth-eyebrow">MarketingMind AI</p>
              <h1>Access Control</h1>
            </div>
          </div>

          <div className="auth-portal-intro">
            <Shield size={16} aria-hidden="true" />
            <p>Sign in to continue to your recruiting operations workspace.</p>
          </div>

          {error ? <div className="auth-banner error" role="alert">{error}</div> : null}

          {mode === 'login' ? (
            <form className="auth-form" onSubmit={submitLogin} noValidate>
              <FormField label="Email address" required error={fieldErrors.email}>
                <div className="input-with-icon">
                  <Mail size={16} aria-hidden="true" />
                  <input
                    type="email"
                    autoComplete="email"
                    placeholder="you@company.com"
                    value={loginPayload.email}
                    onChange={(event) => updateLoginField('email', event.target.value)}
                  />
                </div>
              </FormField>

              <FormField label="Password" required error={fieldErrors.password}>
                <div className="input-with-icon">
                  <Lock size={16} aria-hidden="true" />
                  <input
                    type="password"
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    value={loginPayload.password}
                    onChange={(event) => updateLoginField('password', event.target.value)}
                  />
                </div>
              </FormField>

              <button className="auth-submit" type="submit" disabled={busy}>
                {busy ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          ) : (
            <form className="auth-form" onSubmit={submitRegister} noValidate>
              <FormField label="Full name" required error={fieldErrors.name}>
                <div className="input-with-icon">
                  <User size={16} aria-hidden="true" />
                  <input
                    autoComplete="name"
                    placeholder="Your name"
                    value={registerPayload.name}
                    onChange={(event) => updateRegisterField('name', event.target.value)}
                  />
                </div>
              </FormField>

              <FormField label="Email address" required error={fieldErrors.email}>
                <div className="input-with-icon">
                  <Mail size={16} aria-hidden="true" />
                  <input
                    type="email"
                    autoComplete="email"
                    placeholder="you@company.com"
                    value={registerPayload.email}
                    onChange={(event) => updateRegisterField('email', event.target.value)}
                  />
                </div>
              </FormField>

              <FormField label="Password" required error={fieldErrors.password} hint="Minimum 6 characters">
                <div className="input-with-icon">
                  <Lock size={16} aria-hidden="true" />
                  <input
                    type="password"
                    autoComplete="new-password"
                    placeholder="Create a password"
                    value={registerPayload.password}
                    onChange={(event) => updateRegisterField('password', event.target.value)}
                  />
                </div>
              </FormField>

              <FormField label="Role" required error={fieldErrors.role}>
                <select
                  value={registerPayload.role}
                  onChange={(event) => updateRegisterField('role', event.target.value)}
                >
                  {roles.map((role) => (
                    <option key={role} value={role}>{role.replaceAll('_', ' ')}</option>
                  ))}
                </select>
              </FormField>

              <button className="auth-submit" type="submit" disabled={busy}>
                {busy ? 'Creating account…' : 'Create account'}
              </button>
            </form>
          )}

          <p className="auth-footer-note">
            Role-based access is enforced on every API endpoint.
          </p>
        </article>
      </div>
    </div>
  )
}
