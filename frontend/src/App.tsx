import { useState, useEffect } from 'react'
import './App.css'

interface HealthResponse {
  status: string
  service: string
  version: string
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const checkHealth = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:8000/api/health/')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setHealth(data)
    } catch (err: any) {
      setError(err.message || 'Failed to connect to backend service')
      setHealth(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    checkHealth()
  }, [])

  return (
    <div className="documind-scaffold">
      <header className="hero-header">
        <div className="gradient-glow"></div>
        <div className="header-badge">Phase 0: Skeleton Scaffold</div>
        <h1 className="hero-title">
          <span className="accent-text">DocuMind</span> Platform
        </h1>
        <p className="hero-subtitle">
          An enterprise document ingestion, analysis, and semantic search (RAG) system built with Django 5.x, React, and Azure AI.
        </p>
      </header>

      <section className="dashboard-grid">
        {/* Connection Status Panel */}
        <div className="panel status-panel">
          <div className="panel-header">
            <span className="panel-icon">🔌</span>
            <h2>Backend Integration</h2>
          </div>
          <div className="panel-body">
            <p className="description">
              Checks connection to Django API endpoint at <code>/api/health/</code>
            </p>
            
            <div className="status-indicator-box">
              {loading && (
                <div className="status-state loading">
                  <div className="spinner"></div>
                  <span>Probing local backend...</span>
                </div>
              )}
              
              {error && (
                <div className="status-state disconnected">
                  <span className="badge-dot red"></span>
                  <span className="status-text">Disconnected</span>
                  <div className="error-box">{error}</div>
                  <p className="hint">Ensure the Django API is running locally: <code>poetry run python manage.py runserver</code></p>
                </div>
              )}

              {health && (
                <div className="status-state connected">
                  <span className="badge-dot green"></span>
                  <span className="status-text">Connected Successfully</span>
                  <div className="response-preview">
                    <div><strong>Service:</strong> {health.service}</div>
                    <div><strong>Status:</strong> {health.status}</div>
                    <div><strong>Version:</strong> {health.version}</div>
                  </div>
                </div>
              )}
            </div>

            <button 
              onClick={checkHealth} 
              className="btn-primary" 
              disabled={loading}
            >
              {loading ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
        </div>

        {/* System Stack Panel */}
        <div className="panel info-panel">
          <div className="panel-header">
            <span className="panel-icon">🛠️</span>
            <h2>Technology Stack</h2>
          </div>
          <div className="panel-body">
            <ul className="tech-list">
              <li>
                <span className="tech-tag python">Python 3.12</span>
                <span className="tech-desc">Django 5.x + REST Framework</span>
              </li>
              <li>
                <span className="tech-tag db">PostgreSQL 16</span>
                <span className="tech-desc">Flexible Server + pgvector</span>
              </li>
              <li>
                <span className="tech-tag search">Azure AI Search</span>
                <span className="tech-desc">Standard (S1) Hybrid & Semantic Search</span>
              </li>
              <li>
                <span className="tech-tag ai">Azure OpenAI</span>
                <span className="tech-desc">gpt-4o & text-embedding-3-large</span>
              </li>
              <li>
                <span className="tech-tag deploy">Containers</span>
                <span className="tech-desc">Azure Container Apps (ACA)</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="repo-status">
        <h3>Repository Directories</h3>
        <div className="folder-grid">
          <div className="folder-item">
            <span className="icon">📁</span>
            <strong>backend/</strong>
            <span>Django REST API</span>
          </div>
          <div className="folder-item">
            <span className="icon">📁</span>
            <strong>frontend/</strong>
            <span>Vite React SPA</span>
          </div>
          <div className="folder-item">
            <span className="icon">📁</span>
            <strong>infra/</strong>
            <span>Azure Bicep IaC</span>
          </div>
          <div className="folder-item">
            <span className="icon">📁</span>
            <strong>eval/</strong>
            <span>Evaluation Harness</span>
          </div>
          <div className="folder-item">
            <span className="icon">📁</span>
            <strong>docs/</strong>
            <span>ADRs & Architecture</span>
          </div>
        </div>
      </section>
    </div>
  )
}

export default App
