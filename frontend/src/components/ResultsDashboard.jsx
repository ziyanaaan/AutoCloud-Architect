function ResultsDashboard({ deployment }) {
    const { endpoint_url, cloudwatch_dashboard_url, status, recommendations } = deployment

    return (
        <div className="results-dashboard">
            <div className="success-banner card">
                <div className="success-content">
                    <span className="success-icon">🎉</span>
                    <div>
                        <h2>Deployment Successful!</h2>
                        <p>Your application is now live on AWS</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-2" style={{ marginTop: '1.5rem' }}>
                <div className="card">
                    <h3 style={{ marginBottom: '1rem' }}>🌐 Application Endpoint</h3>
                    <div className="endpoint-box">
                        <a href={endpoint_url} target="_blank" rel="noopener noreferrer">
                            {endpoint_url}
                        </a>
                        <button
                            className="btn btn-secondary"
                            onClick={() => navigator.clipboard.writeText(endpoint_url)}
                        >
                            📋 Copy
                        </button>
                    </div>
                </div>

                <div className="card">
                    <h3 style={{ marginBottom: '1rem' }}>📊 Monitoring</h3>
                    <a
                        href={cloudwatch_dashboard_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary"
                        style={{ width: '100%' }}
                    >
                        Open CloudWatch Dashboard →
                    </a>
                </div>
            </div>

            <div className="card" style={{ marginTop: '1.5rem' }}>
                <h3 style={{ marginBottom: '1rem' }}>Provisioned Resources</h3>
                <div className="resource-list">
                    {status.resources?.map((resource, index) => (
                        <div key={index} className="resource-item">
                            <div className="resource-icon">
                                {getResourceIcon(resource.resource_type)}
                            </div>
                            <div className="resource-info">
                                <div className="resource-name">{resource.resource_type.split('::').pop()}</div>
                                <div className="resource-id">{resource.resource_id}</div>
                            </div>
                            <div className="badge badge-success">Active</div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="card" style={{ marginTop: '1.5rem' }}>
                <h3 style={{ marginBottom: '1rem' }}>Cost Summary</h3>
                <div className="cost-summary">
                    <div className="cost-row">
                        <span>Estimated Monthly Cost</span>
                        <span className="cost-value">${recommendations.estimated_monthly_cost_usd.toFixed(2)}</span>
                    </div>
                    <div className="cost-row">
                        <span>Instance Type</span>
                        <span>{recommendations.compute.instance_type}</span>
                    </div>
                    <div className="cost-row">
                        <span>Auto Scaling</span>
                        <span>{recommendations.use_auto_scaling ? 'Enabled' : 'Disabled'}</span>
                    </div>
                </div>
            </div>

            <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                <a href="/" className="btn btn-primary btn-large">
                    ← Deploy Another Application
                </a>
            </div>

            <style>{`
        .success-banner {
          background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(6, 182, 212, 0.1));
          border-color: var(--color-success);
        }
        .success-content {
          display: flex;
          align-items: center;
          gap: 1.5rem;
        }
        .success-icon {
          font-size: 3rem;
        }
        .success-content h2 {
          color: var(--color-success);
        }
        .endpoint-box {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          background: var(--color-bg-tertiary);
          border-radius: var(--border-radius-sm);
        }
        .endpoint-box a {
          flex: 1;
          color: var(--color-primary-light);
          word-break: break-all;
        }
        .cost-summary {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }
        .cost-row {
          display: flex;
          justify-content: space-between;
          padding: 0.75rem;
          background: var(--color-bg-tertiary);
          border-radius: var(--border-radius-sm);
        }
        .cost-value {
          font-weight: 700;
          color: var(--color-success);
        }
      `}</style>
        </div>
    )
}

function getResourceIcon(resourceType) {
    const iconMap = {
        'VPC': '🌐',
        'Instance': '💻',
        'Bucket': '📦',
        'Table': '🗃️',
        'DBInstance': '🗄️',
        'LoadBalancer': '⚖️',
        'SecurityGroup': '🔒'
    }
    for (const [key, icon] of Object.entries(iconMap)) {
        if (resourceType.includes(key)) return icon
    }
    return '☁️'
}

export default ResultsDashboard
