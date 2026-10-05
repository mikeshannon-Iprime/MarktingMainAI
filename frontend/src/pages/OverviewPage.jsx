import { ArrowRight, Radar, Rocket, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

export function OverviewPage({ overview }) {
  if (!overview) {
    return null
  }

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Unified front office</p>
          <h3>Operational UX rebuilt from the legacy HTML dashboards.</h3>
          <p className="hero-copy">{overview.headline}</p>
        </div>
        <div className="hero-grid">
          <div className="metric-tile accent-amber">
            <Rocket size={18} />
            <strong>{overview.modules[0].metric}</strong>
            <span>Campaign throughput</span>
          </div>
          <div className="metric-tile accent-teal">
            <Radar size={18} />
            <strong>{overview.modules[1].metric}</strong>
            <span>Automation queue</span>
          </div>
        </div>
      </section>

      <section className="module-grid">
        {overview.modules.map((module) => (
          <article key={module.slug} className="module-card">
            <div className="module-header">
              <div>
                <p className="eyebrow">Module</p>
                <h4>{module.label}</h4>
              </div>
              <span className="metric-chip">{module.metric}</span>
            </div>
            <p>{module.description}</p>
            <Link className="inline-link" to={`/${module.slug}`}>
              Open workspace
              <ArrowRight size={16} />
            </Link>
          </article>
        ))}
      </section>

      <section className="dual-grid">
        <article className="glass-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Recent activity</p>
              <h4>Operational feed</h4>
            </div>
          </div>
          <div className="activity-list">
            {overview.activity.map((item) => (
              <div key={item.title} className="activity-row">
                <div className="activity-icon">
                  <ShieldCheck size={16} />
                </div>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="glass-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Platform</p>
              <h4>Workspace notes</h4>
            </div>
          </div>
          <ul className="check-list">
            <li>API surface is split by module-specific endpoints.</li>
            <li>Frontend routing preserves all child pages from the source HTML modules.</li>
            <li>Each dashboard is seeded with rich test data while you wire live tables later.</li>
          </ul>
        </article>
      </section>
    </div>
  )
}
