import { useState } from 'react'

const APP_TYPES = [
    { value: 'web', label: 'Web Application', icon: '🌐' },
    { value: 'api', label: 'REST API', icon: '⚡' },
    { value: 'static', label: 'Static Website', icon: '📄' },
    { value: 'ml', label: 'ML/AI Application', icon: '🤖' }
]

const PERFORMANCE_LEVELS = [
    { value: 'low', label: 'Low', desc: 'Basic performance' },
    { value: 'balanced', label: 'Balanced', desc: 'Recommended' },
    { value: 'high', label: 'High', desc: 'Maximum performance' }
]

const BUDGET_TIERS = [
    { value: 'low', label: 'Budget', desc: '~$50/mo' },
    { value: 'medium', label: 'Standard', desc: '~$150/mo' },
    { value: 'high', label: 'Premium', desc: '~$500/mo' }
]

function RequirementsForm({ onSubmit, loading }) {
    const [formData, setFormData] = useState({
        app_name: '',
        app_type: 'web',
        description: '',
        expected_users: 100,
        data_size_gb: 10,
        performance_priority: 'balanced',
        budget_tier: 'medium',
        requires_database: true,
        requires_load_balancer: false,
        requires_auto_scaling: false
    })
    const [codeFile, setCodeFile] = useState(null)
    const [repoUrl, setRepoUrl] = useState('')
    const [uploadMethod, setUploadMethod] = useState('none') // none, file, repo

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }))
    }

    const handleFileChange = (e) => {
        const file = e.target.files[0]
        if (file) {
            setCodeFile(file)
            setUploadMethod('file')
        }
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        onSubmit({
            ...formData,
            code_file: codeFile,
            repo_url: repoUrl,
            upload_method: uploadMethod
        })
    }

    return (
        <form onSubmit={handleSubmit} className="requirements-form">
            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">Application Details</h2>
                    <p className="card-subtitle">Tell us about your application</p>
                </div>

                <div className="form-group">
                    <label className="form-label">Application Name *</label>
                    <input
                        type="text"
                        className="form-input"
                        placeholder="my-awesome-app"
                        value={formData.app_name}
                        onChange={(e) => handleChange('app_name', e.target.value)}
                        required
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">Application Type *</label>
                    <div className="type-grid">
                        {APP_TYPES.map(type => (
                            <div
                                key={type.value}
                                className={`type-card ${formData.app_type === type.value ? 'selected' : ''}`}
                                onClick={() => handleChange('app_type', type.value)}
                            >
                                <span className="type-icon">{type.icon}</span>
                                <span className="type-label">{type.label}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="form-group">
                    <label className="form-label">Description</label>
                    <textarea
                        className="form-input"
                        placeholder="Brief description of your application..."
                        rows={3}
                        value={formData.description}
                        onChange={(e) => handleChange('description', e.target.value)}
                    />
                </div>
            </div>

            <div className="card" style={{ marginTop: '1.5rem' }}>
                <div className="card-header">
                    <h2 className="card-title">Capacity & Performance</h2>
                </div>

                <div className="grid grid-2">
                    <div className="form-group">
                        <label className="form-label">Expected Concurrent Users</label>
                        <input
                            type="number"
                            className="form-input"
                            min={1}
                            max={10000000}
                            value={formData.expected_users}
                            onChange={(e) => handleChange('expected_users', parseInt(e.target.value))}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Data Storage (GB)</label>
                        <input
                            type="number"
                            className="form-input"
                            min={0}
                            max={10000}
                            value={formData.data_size_gb}
                            onChange={(e) => handleChange('data_size_gb', parseInt(e.target.value))}
                        />
                    </div>
                </div>

                <div className="form-group">
                    <label className="form-label">Performance Priority</label>
                    <div className="option-group">
                        {PERFORMANCE_LEVELS.map(level => (
                            <div
                                key={level.value}
                                className={`option-card ${formData.performance_priority === level.value ? 'selected' : ''}`}
                                onClick={() => handleChange('performance_priority', level.value)}
                            >
                                <span className="option-label">{level.label}</span>
                                <span className="option-desc">{level.desc}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="form-group">
                    <label className="form-label">Budget Tier</label>
                    <div className="option-group">
                        {BUDGET_TIERS.map(tier => (
                            <div
                                key={tier.value}
                                className={`option-card ${formData.budget_tier === tier.value ? 'selected' : ''}`}
                                onClick={() => handleChange('budget_tier', tier.value)}
                            >
                                <span className="option-label">{tier.label}</span>
                                <span className="option-desc">{tier.desc}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="card" style={{ marginTop: '1.5rem' }}>
                <div className="card-header">
                    <h2 className="card-title">Additional Features</h2>
                </div>

                <div className="toggle-list">
                    <div className="toggle-item">
                        <div className="toggle-info">
                            <span className="toggle-label">Database Required</span>
                            <span className="toggle-desc">Include managed database service</span>
                        </div>
                        <div
                            className={`toggle ${formData.requires_database ? 'active' : ''}`}
                            onClick={() => handleChange('requires_database', !formData.requires_database)}
                        />
                    </div>

                    <div className="toggle-item">
                        <div className="toggle-info">
                            <span className="toggle-label">Load Balancer</span>
                            <span className="toggle-desc">Distribute traffic across instances</span>
                        </div>
                        <div
                            className={`toggle ${formData.requires_load_balancer ? 'active' : ''}`}
                            onClick={() => handleChange('requires_load_balancer', !formData.requires_load_balancer)}
                        />
                    </div>

                    <div className="toggle-item">
                        <div className="toggle-info">
                            <span className="toggle-label">Auto Scaling</span>
                            <span className="toggle-desc">Automatically scale based on demand</span>
                        </div>
                        <div
                            className={`toggle ${formData.requires_auto_scaling ? 'active' : ''}`}
                            onClick={() => handleChange('requires_auto_scaling', !formData.requires_auto_scaling)}
                        />
                    </div>
                </div>
            </div>

            {/* Code Upload Section */}
            <div className="card" style={{ marginTop: '1.5rem' }}>
                <div className="card-header">
                    <h2 className="card-title">📦 Application Code</h2>
                    <p className="card-subtitle">Upload your code or provide a repository URL (optional)</p>
                </div>

                <div className="upload-options">
                    <div
                        className={`upload-option ${uploadMethod === 'none' ? 'selected' : ''}`}
                        onClick={() => { setUploadMethod('none'); setCodeFile(null); setRepoUrl(''); }}
                    >
                        <span className="upload-icon">🚀</span>
                        <span className="upload-label">Deploy Sample App</span>
                        <span className="upload-desc">We'll deploy a demo application</span>
                    </div>

                    <div
                        className={`upload-option ${uploadMethod === 'file' ? 'selected' : ''}`}
                        onClick={() => document.getElementById('code-file-input').click()}
                    >
                        <span className="upload-icon">📁</span>
                        <span className="upload-label">Upload ZIP File</span>
                        <span className="upload-desc">
                            {codeFile ? codeFile.name : 'Upload your application code'}
                        </span>
                    </div>

                    <div
                        className={`upload-option ${uploadMethod === 'repo' ? 'selected' : ''}`}
                        onClick={() => setUploadMethod('repo')}
                    >
                        <span className="upload-icon">🔗</span>
                        <span className="upload-label">Git Repository</span>
                        <span className="upload-desc">Provide a GitHub/GitLab URL</span>
                    </div>
                </div>

                <input
                    id="code-file-input"
                    type="file"
                    accept=".zip,.tar.gz,.tgz"
                    style={{ display: 'none' }}
                    onChange={handleFileChange}
                />

                {uploadMethod === 'repo' && (
                    <div className="form-group" style={{ marginTop: '1rem' }}>
                        <label className="form-label">Repository URL</label>
                        <input
                            type="url"
                            className="form-input"
                            placeholder="https://github.com/username/repository"
                            value={repoUrl}
                            onChange={(e) => setRepoUrl(e.target.value)}
                        />
                        <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
                            Supports GitHub, GitLab, and Bitbucket URLs
                        </p>
                    </div>
                )}

                {codeFile && uploadMethod === 'file' && (
                    <div className="file-preview">
                        <div className="file-info">
                            <span className="file-name">📄 {codeFile.name}</span>
                            <span className="file-size">{(codeFile.size / 1024 / 1024).toFixed(2)} MB</span>
                        </div>
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => { setCodeFile(null); setUploadMethod('none'); }}
                        >
                            Remove
                        </button>
                    </div>
                )}
            </div>

            <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                <button
                    type="submit"
                    className="btn btn-primary btn-large"
                    disabled={loading || !formData.app_name}
                >
                    {loading ? (
                        <>
                            <span className="spinner" style={{ width: '20px', height: '20px' }}></span>
                            Analyzing...
                        </>
                    ) : (
                        <>🚀 Analyze & Get Recommendations</>
                    )}
                </button>
            </div>

            <style>{`
        .type-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 1rem;
        }
        .type-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 1.5rem;
          background: var(--color-bg-tertiary);
          border: 2px solid transparent;
          border-radius: var(--border-radius-md);
          cursor: pointer;
          transition: all var(--transition-fast);
        }
        .type-card:hover {
          border-color: var(--color-primary);
        }
        .type-card.selected {
          border-color: var(--color-primary);
          background: rgba(59, 130, 246, 0.1);
        }
        .type-icon {
          font-size: 2rem;
          margin-bottom: 0.5rem;
        }
        .type-label {
          font-weight: 500;
        }
        .option-group {
          display: flex;
          gap: 1rem;
        }
        .option-card {
          flex: 1;
          padding: 1rem;
          background: var(--color-bg-tertiary);
          border: 2px solid transparent;
          border-radius: var(--border-radius-sm);
          cursor: pointer;
          text-align: center;
          transition: all var(--transition-fast);
        }
        .option-card:hover {
          border-color: var(--color-primary);
        }
        .option-card.selected {
          border-color: var(--color-primary);
          background: rgba(59, 130, 246, 0.1);
        }
        .option-label {
          display: block;
          font-weight: 600;
        }
        .option-desc {
          display: block;
          font-size: 0.75rem;
          color: var(--color-text-muted);
        }
        .toggle-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .toggle-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background: var(--color-bg-tertiary);
          border-radius: var(--border-radius-sm);
        }
        .toggle-label {
          display: block;
          font-weight: 500;
        }
        .toggle-desc {
          display: block;
          font-size: 0.875rem;
          color: var(--color-text-muted);
        }
        @media (max-width: 768px) {
          .type-grid {
            grid-template-columns: repeat(2, 1fr);
          }
          .option-group {
            flex-direction: column;
          }
          .upload-options {
            flex-direction: column;
          }
        }
        .upload-options {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;
        }
        .upload-option {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 1.5rem;
          background: var(--color-bg-tertiary);
          border: 2px solid transparent;
          border-radius: var(--border-radius-md);
          cursor: pointer;
          transition: all var(--transition-fast);
          text-align: center;
        }
        .upload-option:hover {
          border-color: var(--color-primary);
        }
        .upload-option.selected {
          border-color: var(--color-primary);
          background: rgba(59, 130, 246, 0.1);
        }
        .upload-icon {
          font-size: 2rem;
          margin-bottom: 0.5rem;
        }
        .upload-label {
          font-weight: 600;
          margin-bottom: 0.25rem;
        }
        .upload-desc {
          font-size: 0.75rem;
          color: var(--color-text-muted);
        }
        .file-preview {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 1rem;
          padding: 1rem;
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid var(--color-success);
          border-radius: var(--border-radius-sm);
        }
        .file-info {
          display: flex;
          flex-direction: column;
        }
        .file-name {
          font-weight: 500;
          color: var(--color-success);
        }
        .file-size {
          font-size: 0.75rem;
          color: var(--color-text-muted);
        }
      `}</style>
        </form>
    )
}

export default RequirementsForm
