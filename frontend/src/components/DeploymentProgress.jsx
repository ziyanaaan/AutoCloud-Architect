const STEPS = [
    { key: 'pending', label: 'Initializing', icon: '⏳' },
    { key: 'analyzing', label: 'Analyzing', icon: '🔍' },
    { key: 'provisioning', label: 'Provisioning', icon: '🏗️' },
    { key: 'deploying', label: 'Deploying', icon: '📦' },
    { key: 'verifying', label: 'Verifying', icon: '✅' },
    { key: 'completed', label: 'Complete', icon: '🎉' }
]

function DeploymentProgress({ status }) {
    const { state, progress_percent, current_step, message, resources } = status.status

    const currentStepIndex = STEPS.findIndex(s => s.key === state)

    return (
        <div className="deployment-progress">
            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">Deployment in Progress</h2>
                    <p className="card-subtitle">{message}</p>
                </div>

                <div className="progress-section">
                    <div className="progress-info">
                        <span>{current_step}</span>
                        <span>{progress_percent}%</span>
                    </div>
                    <div className="progress-bar" style={{ height: '12px' }}>
                        <div
                            className="progress-fill"
                            style={{ width: `${progress_percent}%` }}
                        ></div>
                    </div>
                </div>

                <div className="steps-timeline">
                    {STEPS.map((step, index) => (
                        <div
                            key={step.key}
                            className={`step ${index < currentStepIndex ? 'completed' : ''} ${index === currentStepIndex ? 'active' : ''}`}
                        >
                            <div className="step-icon">
                                {index < currentStepIndex ? '✓' : step.icon}
                            </div>
                            <div className="step-label">{step.label}</div>
                        </div>
                    ))}
                </div>
            </div>

            {resources && resources.length > 0 && (
                <div className="card" style={{ marginTop: '1.5rem' }}>
                    <h3 style={{ marginBottom: '1rem' }}>Provisioned Resources</h3>
                    <div className="resource-list">
                        {resources.map((resource, index) => (
                            <div key={index} className="resource-item">
                                <div className="resource-icon">
                                    {getResourceIcon(resource.resource_type)}
                                </div>
                                <div className="resource-info">
                                    <div className="resource-name">{resource.resource_type.split('::').pop()}</div>
                                    <div className="resource-id">{resource.resource_id}</div>
                                </div>
                                <div className={`badge badge-${resource.status === 'CREATE_COMPLETE' ? 'success' : 'info'}`}>
                                    {resource.status}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <style>{`
        .progress-section {
          margin: 2rem 0;
        }
        .progress-info {
          display: flex;
          justify-content: space-between;
          margin-bottom: 0.5rem;
          color: var(--color-text-secondary);
        }
        .steps-timeline {
          display: flex;
          justify-content: space-between;
          margin-top: 2rem;
        }
        .step {
          display: flex;
          flex-direction: column;
          align-items: center;
          flex: 1;
          position: relative;
        }
        .step::after {
          content: '';
          position: absolute;
          top: 20px;
          left: 50%;
          width: 100%;
          height: 2px;
          background: var(--color-bg-tertiary);
        }
        .step:last-child::after {
          display: none;
        }
        .step.completed::after {
          background: var(--color-success);
        }
        .step.active::after {
          background: linear-gradient(to right, var(--color-primary), var(--color-bg-tertiary));
        }
        .step-icon {
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--color-bg-tertiary);
          border-radius: 50%;
          font-size: 1.2rem;
          position: relative;
          z-index: 1;
        }
        .step.completed .step-icon {
          background: var(--color-success);
          color: white;
        }
        .step.active .step-icon {
          background: var(--gradient-primary);
          animation: pulse 2s infinite;
        }
        .step-label {
          margin-top: 0.5rem;
          font-size: 0.75rem;
          color: var(--color-text-muted);
        }
        .step.active .step-label {
          color: var(--color-primary);
          font-weight: 600;
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

export default DeploymentProgress
