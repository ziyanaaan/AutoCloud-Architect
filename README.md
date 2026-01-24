# AutoCloud Architect

An intelligent AWS infrastructure recommendation and automated deployment system that analyzes application requirements, uses Amazon SageMaker for recommendations, and automatically provisions AWS resources.

## 🏗️ Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   AWS Cloud     │
│   (React)       │     │   (FastAPI)     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   SageMaker     │     │  CloudFormation │
                        │   (ML Model)    │     │  (Provisioning) │
                        └─────────────────┘     └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- AWS CLI configured with credentials
- Docker (optional)

### Installation

```bash
# Backend setup
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your AWS credentials
```

### Running Locally

```bash
# Terminal 1: Start backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev
```

Access the dashboard at http://localhost:5173

## 📁 Project Structure

```
AutoCloud Architect/
├── frontend/          # React dashboard
├── backend/           # FastAPI server
├── sagemaker/         # ML model training & inference
├── infrastructure/    # CloudFormation templates
└── docs/              # Documentation
```

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | React + Vite |
| Backend | Python + FastAPI |
| ML | Amazon SageMaker |
| IaC | AWS CloudFormation |
| AWS SDK | boto3 |

## 📖 Documentation

- [Architecture Design](docs/architecture.md)
- [Setup Guide](docs/setup.md)
- [API Reference](docs/api.md)

## 🔧 Features

- **Requirements Analysis**: Input your application needs through an intuitive form
- **ML-Powered Recommendations**: SageMaker endpoint suggests optimal AWS architecture
- **Automated Provisioning**: CloudFormation deploys infrastructure automatically
- **Real-time Progress**: Track deployment status with live updates
- **Health Monitoring**: CloudWatch integration for deployed resources

## 📄 License

MIT License
