import { useEffect, useState } from 'react'
import {
  Bell,
  Building2,
  Calendar,
  CheckCircle2,
  Lock,
  LogOut,
  Mail,
  MapPin,
  Phone,
  Save,
  Shield,
  Smartphone,
  User,
} from 'lucide-react'

import {
  changeUserPassword,
  getNotificationHistory,
  getNotificationSetup,
  getUserProfile,
  getUserSettings,
  sendNotificationTestEmail,
  sendNotificationTestSms,
  updateUserProfile,
  updateUserSettings,
  logoutUser,
} from '../api/client'
import { pickFirstError, validatePasswordChangeForm, validateUserProfileForm } from '../utils/validators'
import { getErrorMessage, logger } from '../utils/logger'

const tabs = [
  { key: 'profile', label: 'Profile', icon: Mail },
  { key: 'settings', label: 'Settings', icon: Smartphone },
  { key: 'notifications', label: 'Notifications', icon: Bell },
  { key: 'password', label: 'Password', icon: Lock },
]

export function UserProfilePage({ currentUser, onLogout, onProfileUpdated }) {
  const [activeTab, setActiveTab] = useState('profile')
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState({ tone: 'success', text: '' })
  const [busy, setBusy] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})

  // Profile form state
  const [profileForm, setProfileForm] = useState({
    name: '',
    phone: '',
    company: '',
    title: '',
    department: '',
    location: '',
    timezone: '',
    bio: '',
  })

  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })

  // Notifications form state
  const [notificationsForm, setNotificationsForm] = useState({
    emailNotifications: true,
    campaignAlerts: true,
    jobAlerts: true,
    dailyReport: false,
    weeklyDigest: true,
    smsNotifications: false,
    smsPhone: '',
  })
  const [notificationSetup, setNotificationSetup] = useState(null)
  const [notificationHistory, setNotificationHistory] = useState([])

  // Settings form state
  const [settingsForm, setSettingsForm] = useState({
    language: 'en',
    dateFormat: 'MM/DD/YYYY',
    theme: 'light',
  })

  const pushMessage = (text, tone = 'success') => {
    setMessage({ text, tone })
    setTimeout(() => setMessage({ tone: 'success', text: '' }), 4000)
  }

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        const [profileData, settingsData, setupData, historyData] = await Promise.all([
          getUserProfile(),
          getUserSettings(),
          getNotificationSetup(),
          getNotificationHistory(10),
        ])

        setProfile(profileData.user)
        setNotificationSetup(setupData)
        setNotificationHistory(historyData.items ?? [])

        setProfileForm({
          name: profileData.user.name || '',
          phone: profileData.user.phone || '',
          company: profileData.user.company || '',
          title: profileData.user.title || '',
          department: profileData.user.department || '',
          location: profileData.user.location || '',
          timezone: profileData.user.timezone || '',
          bio: profileData.user.bio || '',
        })

        setNotificationsForm({
          ...settingsData.notifications,
          smsPhone: settingsData.notifications.smsPhone || profileData.user.phone || '',
        })
        setSettingsForm({
          language: settingsData.language,
          dateFormat: settingsData.dateFormat,
          theme: settingsData.theme,
        })
      } catch (error) {
        logger.error(error, { action: 'loadUserProfile' })
        pushMessage(getErrorMessage(error, 'Failed to load profile data.'), 'error')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  const saveProfile = async () => {
    const validation = validateUserProfileForm(profileForm)
    setFieldErrors(validation.errors)
    if (!validation.isValid) {
      pushMessage(pickFirstError(validation.errors), 'error')
      return
    }

    setBusy(true)
    try {
      await updateUserProfile(profileForm)
      setProfile((current) => ({
        ...current,
        ...profileForm,
      }))
      onProfileUpdated?.({
        ...currentUser,
        name: profileForm.name,
      })
      pushMessage('Profile updated successfully.')
    } catch {
      pushMessage('Failed to update profile.', 'error')
    } finally {
      setBusy(false)
    }
  }

  const savePassword = async () => {
    const validation = validatePasswordChangeForm(passwordForm)
    setFieldErrors(validation.errors)
    if (!validation.isValid) {
      pushMessage(pickFirstError(validation.errors), 'error')
      return
    }

    setBusy(true)
    try {
      await changeUserPassword(passwordForm)
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
      setFieldErrors({})
      pushMessage('Password changed successfully.')
    } catch {
      pushMessage('Failed to change password.', 'error')
    } finally {
      setBusy(false)
    }
  }

  const saveSettings = async () => {
    setBusy(true)
    try {
      await updateUserSettings({
        notifications: notificationsForm,
        language: settingsForm.language,
        dateFormat: settingsForm.dateFormat,
        theme: settingsForm.theme,
      })
      pushMessage('Settings updated successfully.')
    } catch {
      pushMessage('Failed to update settings.', 'error')
    } finally {
      setBusy(false)
    }
  }

  const runTestEmail = async () => {
    setBusy(true)
    try {
      const response = await sendNotificationTestEmail(profile?.email || '')
      pushMessage(response.message || 'Test email sent.')
      const historyData = await getNotificationHistory(10)
      setNotificationHistory(historyData.items ?? [])
    } catch (error) {
      pushMessage(getErrorMessage(error, 'Test email failed.'), 'error')
    } finally {
      setBusy(false)
    }
  }

  const runTestSms = async () => {
    setBusy(true)
    try {
      const response = await sendNotificationTestSms(notificationsForm.smsPhone || profileForm.phone || '')
      pushMessage(response.message || 'Test SMS sent.')
      const historyData = await getNotificationHistory(10)
      setNotificationHistory(historyData.items ?? [])
    } catch (error) {
      pushMessage(getErrorMessage(error, 'Test SMS failed.'), 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleLogout = async () => {
    if (window.confirm('Are you sure you want to logout?')) {
      await logoutUser()
      onLogout()
    }
  }

  const initials = profile?.name?.split(' ').map((n) => n[0]).join('') ?? 'U'
  const roleLabel = profile?.role?.replaceAll('_', ' ') ?? 'User'

  if (loading) {
    return (
      <div className="page-stack profile-dashboard-page">
        <section className="hero-panel">
          <div>
            <p className="eyebrow">Loading profile</p>
            <h3>Retrieving your account dashboard...</h3>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="page-stack profile-dashboard-page">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Account dashboard</p>
          <h3>My Profile & workspace preferences</h3>
          <p className="hero-copy">
            Manage your identity, security, notifications, and application settings from one place.
          </p>
        </div>
        <div className="hero-grid four-up">
          <div className="metric-tile accent-cobalt">
            <Shield size={18} />
            <strong className="metric-text">{roleLabel}</strong>
            <span>Access role</span>
          </div>
          <div className="metric-tile accent-teal">
            <CheckCircle2 size={18} />
            <strong>Active</strong>
            <span>Account status</span>
          </div>
          <div className="metric-tile accent-amber">
            <Calendar size={18} />
            <strong className="metric-text">
              {profile?.lastLogin ? new Date(profile.lastLogin).toLocaleDateString() : '—'}
            </strong>
            <span>Last login</span>
          </div>
          <div className="metric-tile accent-amber">
            <Bell size={18} />
            <strong>{Object.values(notificationsForm).filter((value) => typeof value === 'boolean' && value).length}/6</strong>
            <span>Alerts enabled</span>
          </div>
        </div>
      </section>

      {message.text ? <div className={`banner ${message.tone}`}>{message.text}</div> : null}

      <section className="profile-dashboard-layout">
        <aside className="profile-dashboard-sidebar glass-card">
          <div className="profile-sidebar-identity">
            <div className="profile-avatar-large">{initials}</div>
            <div>
              <h4>{profile?.name}</h4>
              <p className="profile-sidebar-email">{profile?.email}</p>
              <span className="status-pill available">{roleLabel}</span>
            </div>
          </div>

          <div className="profile-sidebar-meta">
            <div className="profile-meta-row">
              <Building2 size={15} />
              <span>{profileForm.company || '—'}</span>
            </div>
            <div className="profile-meta-row">
              <User size={15} />
              <span>{profileForm.title || '—'}</span>
            </div>
            <div className="profile-meta-row">
              <MapPin size={15} />
              <span>{profileForm.location || '—'}</span>
            </div>
            <div className="profile-meta-row">
              <Phone size={15} />
              <span>{profileForm.phone || '—'}</span>
            </div>
          </div>

          <nav className="profile-sidebar-nav" aria-label="Profile sections">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.key}
                  type="button"
                  className={`profile-nav-item${activeTab === tab.key ? ' active' : ''}`}
                  onClick={() => setActiveTab(tab.key)}
                >
                  <Icon size={16} />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </nav>

          <button type="button" className="secondary-button profile-sidebar-logout" onClick={handleLogout}>
            <LogOut size={16} />
            Logout
          </button>
        </aside>

        <div className="profile-dashboard-main">
      {activeTab === 'profile' ? (
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Personal Information</p>
                <h4>Manage your profile details</h4>
              </div>
            </div>

            <div className="form-grid two-columns">
              <label className={fieldErrors.name ? 'form-field has-error' : 'form-field'}>
                Full Name
                <input value={profileForm.name} onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })} />
                {fieldErrors.name ? <span className="field-error">{fieldErrors.name}</span> : null}
              </label>
              <label className="form-field">Email<input value={profile?.email} disabled /></label>
              <label className={fieldErrors.phone ? 'form-field has-error' : 'form-field'}>
                Phone
                <input value={profileForm.phone} onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })} />
                {fieldErrors.phone ? <span className="field-error">{fieldErrors.phone}</span> : null}
              </label>
              <label className="form-field">Company<input value={profileForm.company} onChange={(e) => setProfileForm({ ...profileForm, company: e.target.value })} /></label>
              <label className="form-field">Title<input value={profileForm.title} onChange={(e) => setProfileForm({ ...profileForm, title: e.target.value })} /></label>
              <label className="form-field">Department<input value={profileForm.department} onChange={(e) => setProfileForm({ ...profileForm, department: e.target.value })} /></label>
              <label className={fieldErrors.location ? 'form-field has-error' : 'form-field'}>
                Location
                <input value={profileForm.location} onChange={(e) => setProfileForm({ ...profileForm, location: e.target.value })} />
                {fieldErrors.location ? <span className="field-error">{fieldErrors.location}</span> : null}
              </label>
              <label className="form-field">Timezone<input value={profileForm.timezone} onChange={(e) => setProfileForm({ ...profileForm, timezone: e.target.value })} /></label>
            </div>

            <label className={fieldErrors.bio ? 'form-field has-error' : 'form-field'}>
              Bio
              <textarea value={profileForm.bio} onChange={(e) => setProfileForm({ ...profileForm, bio: e.target.value })} placeholder="Tell us about yourself" rows={4} />
              {fieldErrors.bio ? <span className="field-error">{fieldErrors.bio}</span> : null}
            </label>

            <div className="button-row">
              <button className="primary-button" onClick={saveProfile} disabled={busy}>
                <Save size={16} />
                Save Profile
              </button>
            </div>
          </article>
      ) : null}

      {activeTab === 'settings' ? (
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Application Settings</p>
                <h4>Customize your experience</h4>
              </div>
            </div>

            <div className="form-grid two-columns">
              <label>
                Language
                <select value={settingsForm.language} onChange={(e) => setSettingsForm({ ...settingsForm, language: e.target.value })}>
                  <option value="en">English</option>
                  <option value="es">Español</option>
                  <option value="fr">Français</option>
                </select>
              </label>
              <label>
                Date Format
                <select value={settingsForm.dateFormat} onChange={(e) => setSettingsForm({ ...settingsForm, dateFormat: e.target.value })}>
                  <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                  <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                  <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                </select>
              </label>
              <label>
                Theme
                <select value={settingsForm.theme} onChange={(e) => setSettingsForm({ ...settingsForm, theme: e.target.value })}>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="auto">Auto</option>
                </select>
              </label>
            </div>

            <div className="button-row">
              <button className="primary-button" onClick={saveSettings} disabled={busy}>
                <Save size={16} />
                Save Settings
              </button>
            </div>
          </article>
      ) : null}

      {activeTab === 'notifications' ? (
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Notification Preferences</p>
                <h4>Control how you stay informed</h4>
              </div>
            </div>

            <div className="notification-settings">
              {notificationSetup ? (
                <div className="banner info" style={{ marginBottom: '1rem' }}>
                  Email channel: {notificationSetup.emailConfigured ? 'configured' : 'demo/simulated'} ·
                  SMS channel: {notificationSetup.smsConfigured ? 'configured' : 'demo/simulated'}
                  {notificationSetup.demoMode ? ' · demo mode active' : ''}
                </div>
              ) : null}

              <label className="toggle-row toggle-button">
                <div>
                  <strong>Email Notifications</strong>
                  <p>Receive email notifications for important updates</p>
                </div>
                <input
                  type="checkbox"
                  checked={notificationsForm.emailNotifications}
                  onChange={(e) => setNotificationsForm({ ...notificationsForm, emailNotifications: e.target.checked })}
                />
              </label>

              <label className="toggle-row toggle-button">
                <div>
                  <strong>Campaign Alerts</strong>
                  <p>Get notified when campaigns are sent or completed</p>
                </div>
                <input
                  type="checkbox"
                  checked={notificationsForm.campaignAlerts}
                  onChange={(e) => setNotificationsForm({ ...notificationsForm, campaignAlerts: e.target.checked })}
                />
              </label>

              <label className="toggle-row toggle-button">
                <div>
                  <strong>Job Alerts</strong>
                  <p>Notifications about job automation matches</p>
                </div>
                <input
                  type="checkbox"
                  checked={notificationsForm.jobAlerts}
                  onChange={(e) => setNotificationsForm({ ...notificationsForm, jobAlerts: e.target.checked })}
                />
              </label>

              <label className="toggle-row toggle-button">
                <div>
                  <strong>Daily Report</strong>
                  <p>Receive daily performance reports</p>
                </div>
                <input
                  type="checkbox"
                  checked={notificationsForm.dailyReport}
                  onChange={(e) => setNotificationsForm({ ...notificationsForm, dailyReport: e.target.checked })}
                />
              </label>

              <label className="toggle-row toggle-button">
                <div>
                  <strong>SMS Notifications</strong>
                  <p>Receive SMS alerts for job automation events</p>
                </div>
                <input
                  type="checkbox"
                  checked={notificationsForm.smsNotifications}
                  onChange={(e) => setNotificationsForm({ ...notificationsForm, smsNotifications: e.target.checked })}
                />
              </label>

              <label className="form-field">
                SMS phone number
                <input
                  value={notificationsForm.smsPhone}
                  onChange={(e) => setNotificationsForm({ ...notificationsForm, smsPhone: e.target.value })}
                  placeholder="+1 (555) 555-0123"
                />
              </label>

              <label className="toggle-row toggle-button">
                <div>
                  <strong>Weekly Digest</strong>
                  <p>Summary of weekly activities and metrics</p>
                </div>
                <input
                  type="checkbox"
                  checked={notificationsForm.weeklyDigest}
                  onChange={(e) => setNotificationsForm({ ...notificationsForm, weeklyDigest: e.target.checked })}
                />
              </label>
            </div>

            <div className="button-row">
              <button className="secondary-button" type="button" onClick={runTestEmail} disabled={busy}>
                <Mail size={16} />
                Send test email
              </button>
              <button className="secondary-button" type="button" onClick={runTestSms} disabled={busy}>
                <Smartphone size={16} />
                Send test SMS
              </button>
              <button className="primary-button" onClick={saveSettings} disabled={busy}>
                <Save size={16} />
                Save Preferences
              </button>
            </div>

            {notificationHistory.length ? (
              <div className="glass-card" style={{ marginTop: '1rem' }}>
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Recent deliveries</p>
                    <h4>Notification history</h4>
                  </div>
                </div>
                <div className="table-wrap">
                  <table className="data-table compact">
                    <thead>
                      <tr>
                        <th>Channel</th>
                        <th>Event</th>
                        <th>Recipient</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {notificationHistory.map((item) => (
                        <tr key={item.id}>
                          <td>{item.channel}</td>
                          <td>{item.eventType}</td>
                          <td>{item.recipient}</td>
                          <td>{item.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </article>
      ) : null}

      {activeTab === 'password' ? (
        <>
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Security</p>
                <h4>Change your password</h4>
              </div>
            </div>

            <div className="form-grid">
              <label className={fieldErrors.currentPassword ? 'form-field has-error' : 'form-field'}>
                Current Password
                <input
                  type="password"
                  value={passwordForm.currentPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                />
                {fieldErrors.currentPassword ? <span className="field-error">{fieldErrors.currentPassword}</span> : null}
              </label>
              <label className={fieldErrors.newPassword ? 'form-field has-error' : 'form-field'}>
                New Password
                <input
                  type="password"
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                />
                {fieldErrors.newPassword ? <span className="field-error">{fieldErrors.newPassword}</span> : null}
              </label>
              <label className={fieldErrors.confirmPassword ? 'form-field has-error' : 'form-field'}>
                Confirm Password
                <input
                  type="password"
                  value={passwordForm.confirmPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                />
                {fieldErrors.confirmPassword ? <span className="field-error">{fieldErrors.confirmPassword}</span> : null}
              </label>
            </div>

            <p className="hint-text">Password must be at least 6 characters long.</p>

            <div className="button-row">
              <button className="primary-button" onClick={savePassword} disabled={busy}>
                <Lock size={16} />
                Change Password
              </button>
            </div>
          </article>

          <article className="glass-card warning-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Session Management</p>
                <h4>Logout and manage your session</h4>
              </div>
            </div>

            <p>You are currently logged in as <strong>{currentUser?.email}</strong>.</p>

            <div className="button-row">
              <button className="secondary-button" onClick={handleLogout}>
                <LogOut size={16} />
                Logout
              </button>
            </div>
          </article>
        </>
      ) : null}
        </div>
      </section>
    </div>
  )
}
