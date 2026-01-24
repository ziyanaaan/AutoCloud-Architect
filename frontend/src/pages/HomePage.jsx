import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import RequirementsForm from '../components/RequirementsForm'
import RecommendationsView from '../components/RecommendationsView'
import { analyzeRequirements, startDeployment, uploadCode } from '../services/api'

function HomePage() {
    const navigate = useNavigate()
    const [step, setStep] = useState('form') // form | recommendations | deploying
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [analysisResult, setAnalysisResult] = useState(null)
    const [requirements, setRequirements] = useState(null)
    const [uploadedCodeUrl, setUploadedCodeUrl] = useState(null)

    const handleAnalyze = async (formData) => {
        setLoading(true)
        setError(null)
        setRequirements(formData)

        try {
            // If user uploaded a file, upload it first
            let codeUrl = null
            if (formData.upload_method === 'file' && formData.code_file) {
                const uploadResult = await uploadCode(formData.code_file)
                codeUrl = uploadResult.url
                setUploadedCodeUrl(codeUrl)
            } else if (formData.upload_method === 'repo' && formData.repo_url) {
                codeUrl = formData.repo_url
                setUploadedCodeUrl(codeUrl)
            }

            const result = await analyzeRequirements(formData)
            setAnalysisResult(result)
            setStep('recommendations')
        } catch (err) {
            setError(err.message || 'Analysis failed')
        } finally {
            setLoading(false)
        }
    }

    const handleDeploy = async () => {
        setLoading(true)
        setError(null)

        try {
            await startDeployment({
                job_id: analysisResult.job_id,
                requirements: requirements,
                recommendations: analysisResult.recommendations,
                code_url: uploadedCodeUrl
            })
            navigate(`/deploy/${analysisResult.job_id}`)
        } catch (err) {
            setError(err.message || 'Deployment failed')
            setLoading(false)
        }
    }

    const handleBack = () => {
        setStep('form')
        setAnalysisResult(null)
    }

    return (
        <div className="home-page">
            {step === 'form' && (
                <>
                    <div className="hero">
                        <h1 className="hero-title">Deploy to AWS in Minutes</h1>
                        <p className="hero-subtitle">
                            Tell us about your application and let AI recommend the perfect
                            AWS infrastructure. We'll provision everything automatically.
                        </p>
                    </div>

                    <RequirementsForm
                        onSubmit={handleAnalyze}
                        loading={loading}
                    />
                </>
            )}

            {step === 'recommendations' && analysisResult && (
                <RecommendationsView
                    recommendations={analysisResult.recommendations}
                    appName={requirements?.app_name}
                    onDeploy={handleDeploy}
                    onBack={handleBack}
                    loading={loading}
                />
            )}

            {error && (
                <div className="error-message card" style={{ marginTop: '1rem', borderColor: 'var(--color-error)' }}>
                    <strong>Error:</strong> {error}
                </div>
            )}
        </div>
    )
}

export default HomePage
