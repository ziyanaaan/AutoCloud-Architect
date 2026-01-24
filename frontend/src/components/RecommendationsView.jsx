function RecommendationsView({ recommendations, appName, onDeploy, onBack, loading }) {
    const { compute, storage, database, networking, estimated_monthly_cost_usd, confidence_score } = recommendations

    return (
        <div className="recommendations-view">
            <div style={{ marginBottom: '2rem' }}>
                <button className="btn btn-secondary" onClick={onBack}>
                    ← Back to Form
                </button>
            </div>

            <div className="card" style={{ marginBottom: '1.5rem' }}>
                <div className="card-header">
                    <h2 className="card-title">Recommended Architecture for {appName}</h2>
                    <p className="card-subtitle">
                        Based on your requirements, here's our recommended AWS setup
                    </p>
                </div>

                <div className="confidence-bar">
                    <span>AI Confidence: {(confidence_score * 100).toFixed(0)}%</span>
                    <div className="progress-bar" style={{ width: '200px', marginLeft: '1rem' }}>
                        <div className="progress-fill" style={{ width: `${confidence_score * 100}%` }}></div>
                    </div>
                </div>
            </div>

            <div className="grid grid-2" style={{ marginBottom: '1.5rem' }}>
                <div className="card">
                    <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>💻</span> Compute
                    </h3>
                    <div className="rec-item">
                        <span className="rec-label">Instance Type</span>
                        <span className="rec-value">{compute.instance_type}</span>
                    </div>
                    <div className="rec-item">
                        <span className="rec-label">Instance Count</span>
                        <span className="rec-value">{compute.instance_count}</span>
                    </div>
                    <div className="rec-item">
                        <span className="rec-label">Spot Instances</span>
                        <span className="rec-value">{compute.use_spot ? 'Yes' : 'No'}</span>
                    </div>
                </div>

                <div className="card">
                    <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>🗄️</span> Storage
                    </h3>
                    <div className="rec-item">
                        <span className="rec-label">S3 Bucket</span>
                        <span className="rec-value">{storage.s3_bucket ? 'Yes' : 'No'}</span>
                    </div>
                    <div className="rec-item">
                        <span className="rec-label">Storage Class</span>
                        <span className="rec-value">{storage.storage_class}</span>
                    </div>
                </div>

                {database && (
                    <div className="card">
                        <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span>🗃️</span> Database
                        </h3>
                        <div className="rec-item">
                            <span className="rec-label">Type</span>
                            <span className="rec-value">{database.db_type}</span>
                        </div>
                        {database.instance_class && (
                            <div className="rec-item">
                                <span className="rec-label">Instance Class</span>
                                <span className="rec-value">{database.instance_class}</span>
                            </div>
                        )}
                        <div className="rec-item">
                            <span className="rec-label">Multi-AZ</span>
                            <span className="rec-value">{database.multi_az ? 'Yes' : 'No'}</span>
                        </div>
                    </div>
                )}

                <div className="card">
                    <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>🌐</span> Networking
                    </h3>
                    <div className="rec-item">
                        <span className="rec-label">Load Balancer</span>
                        <span className="rec-value">{networking.use_alb ? 'ALB' : 'None'}</span>
                    </div>
                    <div className="rec-item">
                        <span className="rec-label">Public Subnets</span>
                        <span className="rec-value">{networking.public_subnets}</span>
                    </div>
                    <div className="rec-item">
                        <span className="rec-label">Private Subnets</span>
                        <span className="rec-value">{networking.private_subnets}</span>
                    </div>
                </div>
            </div>

            <div className="card cost-card">
                <div className="cost-content">
                    <div>
                        <h3>Estimated Monthly Cost</h3>
                        <p className="cost-disclaimer">Actual costs may vary based on usage</p>
                    </div>
                    <div className="cost-amount">
                        ${estimated_monthly_cost_usd.toFixed(2)}
                        <span>/month</span>
                    </div>
                </div>
            </div>

            <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                <button
                    className="btn btn-primary btn-large"
                    onClick={onDeploy}
                    disabled={loading}
                >
                    {loading ? (
                        <>
                            <span className="spinner" style={{ width: '20px', height: '20px' }}></span>
                            Starting Deployment...
                        </>
                    ) : (
                        <>🚀 Deploy Infrastructure</>
                    )}
                </button>
            </div>

            <style>{`
        .confidence-bar {
          display: flex;
          align-items: center;
          margin-top: 1rem;
          color: var(--color-text-secondary);
        }
        .rec-item {
          display: flex;
          justify-content: space-between;
          padding: 0.75rem 0;
          border-bottom: 1px solid var(--border-color);
        }
        .rec-item:last-child {
          border-bottom: none;
        }
        .rec-label {
          color: var(--color-text-secondary);
        }
        .rec-value {
          font-weight: 600;
          color: var(--color-primary-light);
        }
        .cost-card {
          background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.1));
          border-color: var(--color-success);
        }
        .cost-content {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .cost-amount {
          font-size: 2.5rem;
          font-weight: 700;
          color: var(--color-success);
        }
        .cost-amount span {
          font-size: 1rem;
          color: var(--color-text-muted);
        }
        .cost-disclaimer {
          color: var(--color-text-muted);
          font-size: 0.875rem;
        }
      `}</style>
        </div>
    )
}

export default RecommendationsView
