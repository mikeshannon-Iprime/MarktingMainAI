import { Activity, Compass, LayoutDashboard, Linkedin, Mail, RefreshCcw, Send, Sparkles, User } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navigation = [
  { to: '/', label: 'Command Center', icon: LayoutDashboard },
  { to: '/campaigns', label: 'Campaign Studio', icon: Mail },
  { to: '/job-automation', label: 'Job Automation', icon: Sparkles },
  { to: '/linkedin', label: 'LinkedIn Recruiter', icon: Linkedin },
  { to: '/day-report', label: 'Day Report', icon: Activity },
  { to: '/submissions', label: 'Submissions', icon: Send },
  { to: '/api-explorer', label: 'API Explorer', icon: Compass },
  { to: '/profile', label: 'My Profile', icon: User },
]

export function AppShell({ children, health, onRefresh, refreshing, currentUser, onLogout }) {
  const apiStatus = health?.status ?? 'loading'
  const apiBadgeClass = apiStatus === 'ok' ? 'available' : apiStatus
  const statusLabel = apiStatus.replaceAll('_', ' ')

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">MM</div>
          <div>
            <p className="eyebrow">Production Console</p>
            <h1>MarketingMind AI</h1>
            <p className="brand-copy">Campaigns, recruiter dashboards, and job automation in one frontend root.</p>
          </div>
        </div>

        <nav className="nav-stack" aria-label="Primary navigation">
          {navigation.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `nav-link${isActive ? ' active' : ''}`
                }
                aria-label={item.label}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        <section className="sidebar-panel" aria-label="Backend health and controls">
          {currentUser ? (
            <NavLink to="/profile" className="profile-link profile-link-card" aria-label="View profile">
              <div className="profile-avatar-small" aria-hidden="true">
                {currentUser.name?.split(' ').map((part) => part[0]).join('') || 'U'}
              </div>
              <div className="profile-link-copy">
                <strong>{currentUser.name}</strong>
                <span className="status-pill available" title={currentUser.role}>
                  {currentUser.role.replaceAll('_', ' ')}
                </span>
              </div>
            </NavLink>
          ) : null}
          <div className="status-row" aria-live="polite">
            <span>API status</span>
            <span className={`status-pill ${apiBadgeClass}`} title={statusLabel}>{statusLabel}</span>
          </div>
          <button
            className="ghost-button"
            type="button"
            onClick={() => {
              if (!refreshing) {
                onRefresh?.()
              }
            }}
            disabled={refreshing}
            aria-busy={refreshing}
            aria-label={refreshing ? 'Flushing and refreshing workspace data' : 'Flush cached data and refresh from API'}
            title="One click: clear cached workspace UI state and reload fresh data from the API"
          >
            <RefreshCcw size={16} className={refreshing ? 'spin' : ''} aria-hidden="true" />
            {refreshing ? 'Flushing…' : 'Refresh data'}
          </button>
          {currentUser ? (
            <button className="secondary-button" type="button" onClick={onLogout}>
              Logout
            </button>
          ) : null}
        </section>
      </aside>

      <div className="workspace">
        <header className="workspace-header">
          <h2 className="workspace-title-fancy">Recruiting operations surface</h2>
        </header>
        <main className="workspace-content">{children}</main>
      </div>
    </div>
  )
}
