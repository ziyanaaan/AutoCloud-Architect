const API_BASE = '/api/v1'

export async function analyzeRequirements(requirements) {
    const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requirements)
    })

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Analysis failed')
    }

    return response.json()
}

export async function startDeployment(deploymentRequest) {
    const response = await fetch(`${API_BASE}/deploy`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(deploymentRequest)
    })

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Deployment failed')
    }

    return response.json()
}

export async function getDeploymentStatus(jobId) {
    const response = await fetch(`${API_BASE}/deploy/${jobId}`)

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to get status')
    }

    return response.json()
}

export async function uploadCode(file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
    })

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
    }

    return response.json()
}

export function createWebSocket(jobId) {
    const wsUrl = `ws://${window.location.host}/ws/deploy/${jobId}`
    return new WebSocket(wsUrl)
}
