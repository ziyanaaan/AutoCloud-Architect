# AutoCloud Architect - Setup Guide

## Prerequisites

- **Node.js** 18+ 
- **Python** 3.10+
- **AWS CLI** configured with credentials
- **Docker** (optional, for containerized deployment)

## Quick Start

### 1. Clone and Navigate

```bash
cd "AutoCloud Architect"
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

### 4. Configure Environment

```bash
# Copy template
cd ..
cp .env.example .env

# Edit .env with your settings
```

**Required environment variables:**
```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1
```

### 5. Run Development Servers

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 6. Access Dashboard

Open http://localhost:5173 in your browser.

---

## Docker Setup (Alternative)

```bash
# Build and run all services
docker-compose up --build
```

Access:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## SageMaker Setup (Optional)

For real ML recommendations instead of mock responses:

### 1. Train the Model

```bash
cd sagemaker/training
pip install -r requirements.txt
python train.py --train-data ../dataset/training_data.csv --output-dir ./model
```

### 2. Deploy Endpoint

```bash
cd ..
python deploy_endpoint.py \
  --model-path ./training/model \
  --endpoint-name autocloud-recommender \
  --role-arn arn:aws:iam::YOUR_ACCOUNT:role/SageMakerRole
```

### 3. Update Environment

Add to `.env`:
```
SAGEMAKER_ENDPOINT_NAME=autocloud-recommender
```

---

## Production Deployment

1. Build frontend: `cd frontend && npm run build`
2. Deploy backend to AWS Lambda/ECS
3. Host frontend on S3 + CloudFront
4. Configure API Gateway for backend
