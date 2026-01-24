import { useState, useEffect, useCallback } from 'react'
import { getDeploymentStatus, createWebSocket } from '../services/api'

export function useDeployment(jobId) {
    const [status, setStatus] = useState(null)
    const [error, setError] = useState(null)
    const [isComplete, setIsComplete] = useState(false)

    const fetchStatus = useCallback(async () => {
        try {
            const data = await getDeploymentStatus(jobId)
            setStatus(data)

            if (data.status.state === 'completed' || data.status.state === 'failed') {
                setIsComplete(true)
            }

            if (data.status.state === 'failed') {
                setError(data.status.error || 'Deployment failed')
            }
        } catch (err) {
            setError(err.message)
        }
    }, [jobId])

    useEffect(() => {
        if (!jobId) return

        // Initial fetch
        fetchStatus()

        // Set up WebSocket for real-time updates
        let ws = null
        try {
            ws = createWebSocket(jobId)

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data)
                if (data.type === 'deployment_update') {
                    setStatus(prev => ({
                        ...prev,
                        status: data.status
                    }))

                    if (data.status.state === 'completed' || data.status.state === 'failed') {
                        setIsComplete(true)
                    }
                }
            }

            ws.onerror = () => {
                // Fall back to polling if WebSocket fails
                console.log('WebSocket error, falling back to polling')
            }
        } catch (err) {
            console.log('WebSocket not available, using polling')
        }

        // Polling fallback
        const pollInterval = setInterval(() => {
            if (!isComplete) {
                fetchStatus()
            }
        }, 3000)

        return () => {
            if (ws) ws.close()
            clearInterval(pollInterval)
        }
    }, [jobId, fetchStatus, isComplete])

    return { status, error, isComplete, refetch: fetchStatus }
}
