import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import DeploymentProgress from '../components/DeploymentProgress'
import ResultsDashboard from '../components/ResultsDashboard'
import { getDeploymentStatus } from '../services/api'
import { useDeployment } from '../hooks/useDeployment'

function DeploymentPage() {
    const { jobId } = useParams()
    const { status, isComplete, error } = useDeployment(jobId)

    if (error) {
        return (
            <div className="deployment-page">
                <div className="card" style={{ borderColor: 'var(--color-error)' }}>
                    <h2>Deployment Error</h2>
                    <p>{error}</p>
                </div>
            </div>
        )
    }

    if (!status) {
        return (
            <div className="deployment-page">
                <div className="card" style={{ textAlign: 'center' }}>
                    <div className="spinner" style={{ margin: '0 auto' }}></div>
                    <p style={{ marginTop: '1rem' }}>Loading deployment status...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="deployment-page">
            <h1 style={{ marginBottom: '2rem' }}>
                Deployment: <span style={{ color: 'var(--color-primary)' }}>{status.app_name}</span>
            </h1>

            {!isComplete ? (
                <DeploymentProgress status={status} />
            ) : (
                <ResultsDashboard deployment={status} />
            )}
        </div>
    )
}

export default DeploymentPage
