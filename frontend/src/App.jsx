import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import DeploymentPage from './pages/DeploymentPage'

function App() {
    return (
        <BrowserRouter>
            <div className="app">
                <header className="header">
                    <div className="header-content">
                        <div className="logo">
                            <span className="logo-icon">☁️</span>
                            <span className="logo-text">AutoCloud Architect</span>
                        </div>
                        <nav className="nav">
                            <a href="/" className="nav-link">Home</a>
                            <a href="/deployments" className="nav-link">Deployments</a>
                            <a href="/docs" className="nav-link">Docs</a>
                        </nav>
                    </div>
                </header>
                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<HomePage />} />
                        <Route path="/deploy/:jobId" element={<DeploymentPage />} />
                    </Routes>
                </main>
                <footer className="footer">
                    <p>© 2024 AutoCloud Architect. Powered by AWS & SageMaker.</p>
                </footer>
            </div>
        </BrowserRouter>
    )
}

export default App
