import { useEffect, useState } from 'react'
import { ExternalLink, ListTree } from 'lucide-react'

import { fetchApiEndpointCatalog } from '../api/client'

function getApiDocsUrls() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

  try {
    const normalized = new URL(baseUrl)
    return {
      docsUrl: new URL('/docs', normalized).toString(),
      openApiUrl: new URL('/openapi.json', normalized).toString(),
    }
  } catch {
    return {
      docsUrl: 'http://localhost:8000/docs',
      openApiUrl: 'http://localhost:8000/openapi.json',
    }
  }
}

function JsonBlock({ value }) {
  const formatted = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  return <pre className="code-block">{formatted}</pre>
}

export function ApiExplorerPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [items, setItems] = useState([])
  const { docsUrl, openApiUrl } = getApiDocsUrls()

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const data = await fetchApiEndpointCatalog()
        setItems(Array.isArray(data?.items) ? data.items : [])
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : 'Failed to fetch endpoint catalog.')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  return (
    <div className="page-stack">
      <section className="hero-panel compact api-explorer-hero">
        <div>
          <p className="eyebrow">API Explorer</p>
          <h3>Backend endpoint catalog</h3>
          <p className="hero-copy">Live endpoint map fetched from backend code so request payloads stay in sync.</p>
        </div>
        <a className="primary-button" href={docsUrl} target="_blank" rel="noreferrer">
          <ExternalLink size={16} />
          Open Swagger Docs
        </a>
      </section>

      <section className="glass-card">
        <div className="page-stack dense">
          <p className="eyebrow">API Docs Endpoint</p>
          <a href={docsUrl} target="_blank" rel="noreferrer">{docsUrl}</a>
          <p className="eyebrow">OpenAPI Spec</p>
          <a href={openApiUrl} target="_blank" rel="noreferrer">{openApiUrl}</a>
        </div>
      </section>

      {loading ? <div className="empty-state"><span>Loading API endpoint catalog...</span></div> : null}
      {error ? <div className="banner error">{error}</div> : null}

      {!loading && !error ? (
        <section className="page-stack">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Endpoints</p>
              <h4>{items.length} routes discovered</h4>
            </div>
          </div>

          <div className="page-stack dense">
            {items.map((item) => (
              <article key={`${item.method}-${item.path}`} className="glass-card api-endpoint-card">
                <div className="section-heading inline-actions small-gap">
                  <div>
                    <p className="eyebrow">{item.method}</p>
                    <h4>{item.path}</h4>
                  </div>
                  <span className="metric-chip">
                    <ListTree size={14} />
                    {item.summary}
                  </span>
                </div>

                <div className="dual-grid api-example-grid">
                  <section>
                    <p className="eyebrow">Request Example</p>
                    <JsonBlock value={item.requestExample ?? { note: 'No request body for this endpoint.' }} />
                  </section>
                  <section>
                    <p className="eyebrow">Response Example</p>
                    <JsonBlock value={item.responseExample ?? {}} />
                  </section>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
