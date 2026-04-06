# AutoCloud Architect — Project Documentation

> **An Intelligent AWS Infrastructure Recommendation and Automated Deployment System**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Proposed Solution](#3-proposed-solution)
4. [System Architecture](#4-system-architecture)
5. [Technology Stack](#5-technology-stack)
6. [AWS Services Used](#6-aws-services-used)
7. [Project Structure](#7-project-structure)
8. [Module-wise Description](#8-module-wise-description)
9. [Application Workflow](#9-application-workflow)
10. [API Reference](#10-api-reference)
11. [Machine Learning Model](#11-machine-learning-model)
12. [Infrastructure as Code](#12-infrastructure-as-code)
13. [Setup & Installation](#13-setup--installation)
14. [Screenshots & Demo](#14-screenshots--demo)
15. [Security Considerations](#15-security-considerations)
16. [Future Scope](#16-future-scope)
17. [Conclusion](#17-conclusion)

---

## 1. Project Overview

**AutoCloud Architect** is a full-stack, AI-powered web application that simplifies AWS cloud infrastructure provisioning. Users input their application requirements through an intuitive web interface, the system leverages an **Amazon SageMaker** machine learning model to analyze those requirements and recommend an optimal AWS architecture, and then **automatically provisions** the entire infrastructure on AWS using **CloudFormation** — all with a single click.

The system eliminates the need for deep AWS expertise by translating high-level application needs (expected users, budget, performance tier, etc.) into production-ready cloud infrastructure.

---

## 2. Problem Statement

Setting up cloud infrastructure on AWS is a complex and time-consuming process that requires:

- In-depth knowledge of 200+ AWS services
- Manual selection of compute instances, database engines, networking configurations, and storage options
- Writing and debugging CloudFormation/Terraform templates
- Cost estimation and optimization expertise
- Post-deployment monitoring setup

**Small teams, startups, and developers without dedicated DevOps engineers** often struggle with these tasks, leading to:

- Over-provisioned (expensive) or under-provisioned (slow) infrastructure
- Security misconfigurations
- Lengthy setup times that delay product launches

---

## 3. Proposed Solution

AutoCloud Architect addresses these challenges by providing:

| Feature | Description |
|---------|-------------|
| **Intuitive Requirements Form** | Users describe their app (type, users, budget, features) — no AWS knowledge needed |
| **ML-Powered Recommendations** | A SageMaker-hosted RandomForest model predicts the optimal instance types, database, and networking configuration |
| **Automated Provisioning** | One-click deployment generates and executes CloudFormation templates to create all AWS resources |
| **Real-time Progress Tracking** | WebSocket-based live updates show deployment status as resources are created |
| **Application Deployment** | Automatically clones code from GitHub, installs dependencies, and serves the app via Nginx |
| **Health Monitoring** | CloudWatch dashboards and alarms are auto-created for deployed infrastructure |
| **Cost Estimation** | Monthly cost estimates are provided before deployment |

---

## 4. System Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                            USER (Browser)                                     │
│                        React + Vite Dashboard                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐  ┌────────────┐  │
│  │ Requirements │  │ Recommendations  │  │  Deployment   │  │  Results   │  │
│  │    Form      │  │     View         │  │   Progress    │  │ Dashboard  │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬───────┘  └─────┬──────┘  │
└─────────┼──────────────────┼─────────────────────┼────────────────┼──────────┘
          │ REST API         │                     │ WebSocket      │
          ▼                  ▼                     ▼                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI + Python)                             │
│                                                                               │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐  ┌────────────┐  │
│  │  API Routes  │  │ SageMaker Service│  │  Provisioning │  │ Monitoring │  │
│  │  /analyze    │  │  ML Inference    │  │   Service     │  │  Service   │  │
│  │  /deploy     │  │  Rule Engine     │  │  CloudForm.   │  │ CloudWatch │  │
│  │  /upload     │  │                  │  │  EC2 Mgmt     │  │ Alarms     │  │
│  └──────────────┘  └──────────────────┘  └───────────────┘  └────────────┘  │
│                                                                               │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐                   │
│  │   Schemas    │  │ Deployment Svc   │  │  WebSocket    │                   │
│  │  (Pydantic)  │  │ SSM / UserData   │  │   Handler     │                   │
│  └──────────────┘  └──────────────────┘  └───────────────┘                   │
└──────────────────────────────┬────────────────────────────────────────────────┘
                               │ boto3
               ┌───────────────┼───────────────────┐
               ▼               ▼                   ▼
       ┌──────────────┐ ┌──────────────┐  ┌──────────────┐
       │  Amazon      │ │    AWS       │  │  Amazon      │
       │  SageMaker   │ │ CloudForm.   │  │  CloudWatch  │
       │  (ML Model)  │ │ (IaC Engine) │  │ (Monitoring) │
       └──────────────┘ └──────┬───────┘  └──────────────┘
                               │
            ┌──────────────────┼──────────────────────┐
            ▼                  ▼                      ▼
    ┌──────────────┐  ┌──────────────┐       ┌──────────────┐
    │  Amazon VPC  │  │  Amazon EC2  │       │  Amazon S3   │
    │  Subnets     │  │  Instances   │       │  Buckets     │
    │  IGW / NAT   │  │  + Nginx     │       └──────────────┘
    │  Route Table │  └──────────────┘
    └──────────────┘         │
                     ┌───────┴────────┐
                     ▼                ▼
             ┌──────────────┐ ┌──────────────┐
             │  Amazon      │ │  Amazon      │
             │  DynamoDB    │ │    RDS       │
             └──────────────┘ └──────────────┘
```

---

## 5. Technology Stack

### Frontend

| Technology | Purpose |
|-----------|---------|
| **React 18** | UI component library for building the interactive dashboard |
| **Vite 5** | Next-generation frontend build tool for fast development and HMR |
| **React Router v6** | Client-side routing for navigation between pages |
| **CSS3** (Custom) | Fully custom styling with CSS variables, gradients, and animations |
| **WebSocket API** | Real-time deployment progress updates |

### Backend

| Technology | Purpose |
|-----------|---------|
| **Python 3.10+** | Primary backend programming language |
| **FastAPI** | High-performance async web framework for REST APIs |
| **Pydantic v2** | Request/response validation and serialization |
| **Uvicorn** | ASGI server for running the FastAPI application |
| **boto3** | AWS SDK for Python — interfaces with all AWS services |
| **WebSockets** | Real-time bidirectional communication for deployment updates |
| **httpx** | Async HTTP client for health checks |

### Machine Learning

| Technology | Purpose |
|-----------|---------|
| **Amazon SageMaker** | Managed ML platform for model training and hosting |
| **scikit-learn** | RandomForest classifier for multi-output predictions |
| **pandas / NumPy** | Data preprocessing and feature engineering |
| **pickle** | Model serialization and deserialization |

### Infrastructure & DevOps

| Technology | Purpose |
|-----------|---------|
| **AWS CloudFormation** | Infrastructure as Code (IaC) for automated resource provisioning |
| **Docker** | Containerization for consistent development environments |
| **Docker Compose** | Multi-container orchestration (frontend + backend) |
| **Nginx** | Reverse proxy and static file serving on deployed EC2 instances |

---

## 6. AWS Services Used

| AWS Service | Role in the Project |
|------------|---------------------|
| **Amazon SageMaker** | Hosts the trained ML model as a real-time inference endpoint. Receives application requirements and returns infrastructure recommendations (instance type, database type, networking config). |
| **AWS CloudFormation** | Generates and executes infrastructure templates. Creates VPC, subnets, security groups, EC2 instances, S3 buckets, DynamoDB tables, RDS databases, and ALBs — all from a single template. |
| **Amazon EC2** | Compute instances where user applications are deployed. Configured with UserData scripts that auto-install dependencies, clone repos, and start the application. |
| **Amazon VPC** | Virtual private cloud with custom CIDR block (10.0.0.0/16), public subnets across multiple AZs, Internet Gateway, and route tables for network isolation and internet access. |
| **Amazon S3** | Object storage for application artifacts, deployment bundles, and general-purpose file storage. Configured with public access block for security. |
| **Amazon DynamoDB** | NoSQL database option for applications requiring a database — provisioned in pay-per-request (on-demand) mode for cost efficiency. |
| **Amazon RDS (MySQL/PostgreSQL)** | Managed relational database service for applications needing SQL databases. Supports Multi-AZ deployments for high availability. |
| **Elastic Load Balancing (ALB)** | Application Load Balancer distributes incoming HTTP traffic across EC2 instances. Configured with target groups and health checks. |
| **Amazon CloudWatch** | Monitoring service — automatically creates dashboards showing CPU utilization and network traffic, plus alarms for high CPU (>80%) and status check failures. |
| **AWS IAM** | Identity and Access Management — defines least-privilege roles and policies for EC2 instances and service access. |
| **AWS Systems Manager (SSM)** | Used for remote instance management and command execution without requiring SSH keys. |

---

## 7. Project Structure

```
AutoCloud Architect/
│
├── frontend/                          # React Frontend Application
│   ├── src/
│   │   ├── App.jsx                    # Root component with routing
│   │   ├── main.jsx                   # React entry point
│   │   ├── components/
│   │   │   ├── RequirementsForm.jsx   # User input form (app type, users, budget, etc.)
│   │   │   ├── RecommendationsView.jsx # Displays ML-generated recommendations
│   │   │   ├── DeploymentProgress.jsx # Real-time deployment progress tracker
│   │   │   └── ResultsDashboard.jsx   # Final deployment results & endpoints
│   │   ├── pages/
│   │   │   ├── HomePage.jsx           # Main landing page
│   │   │   └── DeploymentPage.jsx     # Deployment tracking page
│   │   ├── services/
│   │   │   └── api.js                 # API client (fetch + WebSocket)
│   │   ├── hooks/
│   │   │   └── useDeployment.js       # Custom hook for deployment state
│   │   └── styles/                    # CSS stylesheets
│   ├── index.html                     # HTML entry point
│   ├── package.json                   # NPM dependencies
│   ├── vite.config.js                 # Vite configuration
│   └── Dockerfile                     # Frontend Docker image
│
├── backend/                           # FastAPI Backend Application
│   ├── app/
│   │   ├── main.py                    # FastAPI app initialization, CORS, routers
│   │   ├── config.py                  # Environment-based settings (Pydantic Settings)
│   │   ├── api/
│   │   │   ├── routes.py             # REST API endpoints (/analyze, /deploy, /upload)
│   │   │   └── websocket.py          # WebSocket connection manager
│   │   ├── schemas/
│   │   │   ├── requirements.py       # Input validation (RequirementsInput)
│   │   │   └── deployment.py         # Output models (Recommendations, DeploymentJob)
│   │   ├── services/
│   │   │   ├── sagemaker_service.py  # SageMaker endpoint invocation + rule engine
│   │   │   ├── provisioning_service.py # CloudFormation template generation & stack mgmt
│   │   │   ├── deployment_service.py # Application deployment to EC2 via SSM
│   │   │   └── monitoring_service.py # CloudWatch dashboard & alarm creation
│   │   └── core/
│   │       └── exceptions.py         # Custom exception classes
│   ├── requirements.txt               # Python dependencies
│   └── Dockerfile                     # Backend Docker image
│
├── sagemaker/                         # Machine Learning Components
│   ├── training/
│   │   ├── train.py                   # Model training script (RandomForest)
│   │   └── requirements.txt          # Training dependencies (sklearn, pandas)
│   ├── inference/
│   │   └── inference.py              # SageMaker inference handler (model_fn, predict_fn)
│   ├── dataset/
│   │   └── training_data.csv         # Training dataset (21 samples, 12 features)
│   └── deploy_endpoint.py            # Script to deploy model to SageMaker endpoint
│
├── infrastructure/                    # CloudFormation Templates
│   └── cloudformation/
│       ├── master.yaml               # Root stack (nested stacks orchestrator)
│       ├── vpc.yaml                  # VPC, subnets, IGW, route tables
│       ├── compute.yaml              # EC2 instances, security groups, ALB
│       ├── storage.yaml              # S3 buckets, DynamoDB tables
│       └── iam.yaml                  # IAM roles and policies
│
├── docs/                              # Documentation
│   ├── architecture.md               # Architecture design document
│   ├── api.md                        # API reference
│   └── setup.md                      # Setup guide
│
├── docker-compose.yml                 # Multi-service Docker orchestration
├── .env.example                       # Environment variable template
├── .gitignore                         # Git ignore rules
└── README.md                          # Project README
```

---

## 8. Module-wise Description

### 8.1 Frontend Module

The frontend is a **React 18** single-page application built with **Vite**.

| Component | File | Description |
|-----------|------|-------------|
| **RequirementsForm** | `RequirementsForm.jsx` | Multi-section form that collects application name, type (Web/API/Static/ML), expected users, data size, performance priority, budget tier, and optional features (database, load balancer, auto scaling). Also supports application code upload via ZIP file or Git repository URL. |
| **RecommendationsView** | `RecommendationsView.jsx` | Renders the ML-generated recommendations in a visually organized layout showing compute, storage, database, and networking suggestions with estimated monthly cost and model confidence score. |
| **DeploymentProgress** | `DeploymentProgress.jsx` | Real-time deployment tracker that connects via WebSocket to display live progress (Analyzing → Provisioning → Deploying → Verifying → Complete). Shows each provisioned AWS resource and its status. |
| **ResultsDashboard** | `ResultsDashboard.jsx` | Final deployment summary showing the live application endpoint URL, CloudWatch dashboard link, provisioned resources, and deployment metadata. |
| **API Service** | `api.js` | Centralized API client module with functions for `analyzeRequirements()`, `startDeployment()`, `getDeploymentStatus()`, `uploadCode()`, and WebSocket creation. |
| **useDeployment Hook** | `useDeployment.js` | React custom hook that manages deployment state, polling, and WebSocket connection lifecycle. |

### 8.2 Backend Module

The backend is a **FastAPI** server organized into clean layers:

| Layer | Files | Description |
|-------|-------|-------------|
| **API Routes** | `routes.py`, `websocket.py` | Defines REST endpoints (`POST /analyze`, `POST /deploy`, `GET /deploy/{id}`, `POST /upload`, `GET /deployments`) and WebSocket endpoint (`/ws/deploy/{id}`) for real-time updates. |
| **Schemas** | `requirements.py`, `deployment.py` | Pydantic models for strict request validation. `RequirementsInput` validates app type, user count, budget, etc. `RecommendationOutput` structures the ML model's response. `DeploymentJob` tracks the full lifecycle. |
| **SageMaker Service** | `sagemaker_service.py` | Dual-mode service: invokes a real SageMaker endpoint when configured, or falls back to a built-in rule-based recommendation engine for development. Handles instance type selection, database selection, cost estimation. |
| **Provisioning Service** | `provisioning_service.py` | The core infrastructure engine. Dynamically generates CloudFormation JSON templates with VPC, subnets, Internet Gateway, route tables, EC2 instances, security groups, S3, DynamoDB/RDS, and ALB. Embeds a full UserData bootstrap script that installs dependencies, clones repos, builds apps, and configures Nginx. |
| **Deployment Service** | `deployment_service.py` | Handles post-provisioning tasks: SSM-based command execution, application deployment, auto-detection of project type (Node.js, Python, static), and health checks. |
| **Monitoring Service** | `monitoring_service.py` | Creates CloudWatch dashboards (CPU, network metrics) and metric alarms (high CPU, status check failures) for deployed instances. |
| **Config** | `config.py` | Centralized configuration using `pydantic-settings`. Loads from `.env` file with automatic discovery. Supports real AWS mode and mock mode. |

### 8.3 SageMaker (ML) Module

| Component | File | Description |
|-----------|------|-------------|
| **Training Script** | `train.py` | Trains a **multi-output RandomForest classifier** using scikit-learn. Encodes categorical features (app type, performance, budget) with LabelEncoder. Trains 4 separate classifiers: compute type, database type, ALB usage, and auto scaling. Follows SageMaker's training contract (`SM_MODEL_DIR`, `SM_CHANNEL_TRAIN`). |
| **Inference Script** | `inference.py` | Implements SageMaker's inference interface: `model_fn()` loads model + encoders, `input_fn()` parses JSON, `predict_fn()` generates recommendations, `output_fn()` serializes response. Outputs instance type, database, ALB, ASG, cost estimate, and confidence score. |
| **Training Dataset** | `training_data.csv` | Curated dataset of 21 training samples covering 4 app types (web, api, static, ml), various user scales (50 – 100,000), and 3 budget tiers. Features: `app_type`, `expected_users`, `data_size_gb`, `performance`, `budget`. Labels: `compute_type`, `db_type`, `use_alb`, `use_asg`. |
| **Endpoint Deployer** | `deploy_endpoint.py` | Automates the SageMaker deployment pipeline: creates model archive (.tar.gz), uploads to S3, deploys as a real-time endpoint using `SKLearnModel`, and runs test inference. |

### 8.4 Infrastructure Module

Pre-built **CloudFormation YAML templates** for reference and nested-stack deployments:

| Template | Resources Created |
|----------|-------------------|
| `master.yaml` | Root stack orchestrating all nested stacks |
| `vpc.yaml` | VPC (10.0.0.0/16), 2 public subnets, Internet Gateway, route tables |
| `compute.yaml` | EC2 instance, security group, optional ALB with target group |
| `storage.yaml` | S3 bucket (private), optional DynamoDB table |
| `iam.yaml` | IAM role for EC2 instances, instance profile |

---

## 9. Application Workflow

The complete end-to-end workflow consists of the following steps:

```
   User opens browser              User fills requirements form
        │                                    │
        ▼                                    ▼
   ┌─────────┐                       ┌──────────────┐
   │ HomePage │  ──────────────────▶  │ Requirements │
   └─────────┘                       │    Form      │
                                     └──────┬───────┘
                                            │ Submit
                                            ▼
                                  POST /api/v1/analyze
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │ SageMaker Service │
                                  │  (ML Inference)   │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ Recommendations   │
                                  │    View           │
                                  │ (User Reviews &   │
                                  │  Approves)        │
                                  └────────┬─────────┘
                                           │ Deploy
                                           ▼
                                  POST /api/v1/deploy
                                           │
                             ┌─────────────┼──────────────┐
                             ▼             ▼              ▼
                     Generate CF    Create Stack    Wait & Monitor
                      Template     (CloudFormation)  (WebSocket)
                             │             │              │
                             ▼             ▼              ▼
                     ┌─────────────────────────────────────────┐
                     │        AWS Resources Created:           │
                     │  VPC → Subnets → IGW → Route Tables    │
                     │  Security Group → EC2 Instance          │
                     │  S3 Bucket → DynamoDB / RDS             │
                     │  ALB → Target Group → Listener          │
                     └────────────────┬────────────────────────┘
                                      │
                                      ▼
                           App Deployed on EC2
                      (Git clone → npm install → Nginx)
                                      │
                                      ▼
                           CloudWatch Dashboard
                            & Alarms Created
                                      │
                                      ▼
                           Health Check Verified
                                      │
                                      ▼
                         ┌────────────────────┐
                         │  Results Dashboard │
                         │  • Live Endpoint   │
                         │  • Dashboard URL   │
                         │  • Resource List   │
                         └────────────────────┘
```

### Step-by-Step Flow:

1. **User Input** — The user fills out the requirements form specifying app name, type, expected users, data storage needs, performance priority, budget tier, and optional features.

2. **Analysis** — The form data is sent to `POST /api/v1/analyze`. The backend invokes the SageMaker endpoint (or local rule engine) to generate infrastructure recommendations.

3. **Review Recommendations** — The user reviews the recommended EC2 instance type, database configuration, networking setup, and estimated monthly cost.

4. **Deploy** — The user clicks "Deploy" which triggers `POST /api/v1/deploy`. The backend runs the deployment pipeline as a background task.

5. **Provisioning** — The backend dynamically generates a CloudFormation template and creates a stack. Resources are created in the correct dependency order (VPC → Subnets → Security Groups → EC2 → S3 → DB → ALB).

6. **Application Deployment** — The EC2 instance's UserData script automatically:
   - Installs system packages (git, nginx, node.js, python)
   - Clones the user's GitHub repository (if provided)
   - Detects the project type (Node.js/Python/Static)
   - Installs dependencies and builds the project
   - Configures Nginx as a reverse proxy
   - Starts the application

7. **Monitoring Setup** — CloudWatch dashboard and alarms are created for the EC2 instance.

8. **Health Check** — The system verifies the deployed application is responding.

9. **Completion** — The user receives the live endpoint URL, CloudWatch dashboard link, and a summary of all provisioned resources.

---

## 10. API Reference

**Base URL:** `http://localhost:8000/api/v1`

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Analyze requirements and get ML-powered infrastructure recommendations |
| `POST` | `/deploy` | Initiate deployment pipeline (provisions infrastructure + deploys app) |
| `GET` | `/deploy/{job_id}` | Get current deployment status |
| `GET` | `/deploy/{job_id}/logs` | Get deployment logs |
| `GET` | `/deployments` | List all deployment jobs |
| `POST` | `/upload` | Upload application code (ZIP) to S3 |

### WebSocket Endpoint

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| `WS` | `/ws/deploy/{job_id}` | Real-time deployment status updates |

### Key Data Models

**RequirementsInput** (POST /analyze request body):
```json
{
  "app_name": "my-web-app",
  "app_type": "web | api | static | ml",
  "description": "A modern web application",
  "expected_users": 1000,
  "data_size_gb": 50,
  "performance_priority": "low | balanced | high",
  "budget_tier": "low | medium | high",
  "requires_database": true,
  "requires_load_balancer": false,
  "requires_auto_scaling": false,
  "repo_url": "https://github.com/username/repo"
}
```

**RecommendationOutput** (returned by /analyze):
```json
{
  "compute": { "instance_type": "t3.medium", "instance_count": 2, "use_spot": false },
  "storage": { "s3_bucket": true, "storage_class": "STANDARD" },
  "database": { "db_type": "rds-mysql", "instance_class": "db.t3.micro", "multi_az": false },
  "networking": { "use_alb": true, "use_nat": true, "public_subnets": 2, "private_subnets": 2 },
  "use_auto_scaling": true,
  "estimated_monthly_cost_usd": 150.00,
  "confidence_score": 0.92
}
```

**DeploymentState** transitions:
```
pending → analyzing → provisioning → deploying → verifying → completed
                                                            → failed
```

---

## 11. Machine Learning Model

### Model Type
**Multi-Output Random Forest Classifier** — four independent RandomForest models are trained, each predicting a different aspect of the infrastructure:

| Classifier | Output | Possible Values |
|-----------|--------|-----------------|
| Compute Classifier | EC2 Instance Type | `t3.micro`, `t3.small`, `t3.medium`, `t3.large`, `m5.large`, `m5.xlarge`, `m5.2xlarge` |
| Database Classifier | Database Type | `dynamodb`, `rds-mysql`, `rds-postgres`, `none` |
| ALB Classifier | Use Load Balancer | `0` (no), `1` (yes) |
| ASG Classifier | Use Auto Scaling | `0` (no), `1` (yes) |

### Features (Input)

| Feature | Type | Preprocessing |
|---------|------|---------------|
| `app_type` | Categorical | LabelEncoder → integer |
| `expected_users` | Numeric | Log transformation (log1p) |
| `data_size_gb` | Numeric | Log transformation (log1p) |
| `performance` | Categorical | LabelEncoder → integer |
| `budget` | Categorical | LabelEncoder → integer |

### Training Process

1. Load CSV dataset (21 samples across web, API, static, ML app types)
2. Encode categorical variables using `LabelEncoder`
3. Apply log transform to skewed numerical features
4. Split data (80% train, 20% test)
5. Train 4 independent `RandomForestClassifier(n_estimators=50)` models
6. Evaluate accuracy and save metrics
7. Serialize models + encoders with `pickle`

### SageMaker Integration

- **Training**: Script follows SageMaker's training contract (`SM_MODEL_DIR`, `SM_CHANNEL_TRAIN`)
- **Inference**: Implements the standard SageMaker inference functions (`model_fn`, `input_fn`, `predict_fn`, `output_fn`)
- **Deployment**: Uses `SKLearnModel` from the SageMaker SDK to deploy as a real-time endpoint on `ml.t2.medium`
- **Fallback**: If SageMaker endpoint is unavailable, the backend uses a built-in rule-based engine with the same recommendation logic

---

## 12. Infrastructure as Code

### Dynamic CloudFormation Template Generation

The `ProvisioningService` dynamically generates CloudFormation templates based on the ML recommendations. Each template includes:

#### VPC Layer
- VPC with CIDR `10.0.0.0/16`
- 2 public subnets in different Availability Zones
- Internet Gateway with VPC attachment
- Public Route Table with `0.0.0.0/0 → IGW` route
- Subnet-Route Table associations

#### Compute Layer
- EC2 instance with recommended instance type
- Security Group (ports 22, 80, 443, 3000, 8000)
- Full UserData bootstrap script (install packages, deploy app, configure Nginx)
- Optional SSH key pair injection

#### Storage Layer
- S3 bucket with public access blocked
- Storage class based on budget tier (STANDARD / STANDARD_IA)

#### Database Layer (conditional)
- **DynamoDB**: On-demand table with single hash key
- **RDS MySQL/PostgreSQL**: Managed instance with DB subnet group, dedicated security group, optional Multi-AZ

#### Networking Layer (conditional)
- Application Load Balancer (internet-facing)
- Target Group with health checks
- HTTP Listener on port 80

---

## 13. Setup & Installation

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+
- **AWS CLI** configured with credentials (for real deployments)
- **Docker** (optional, for containerized setup)

### Option 1: Local Development

```bash
# 1. Clone the repository
git clone https://github.com/your-username/autocloud-architect.git
cd autocloud-architect

# 2. Configure environment
cp .env.example .env
# Edit .env with your AWS credentials

# 3. Backend setup
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

# Start backend (Terminal 1)
uvicorn app.main:app --reload --port 8000

# 4. Frontend setup (Terminal 2)
cd frontend
npm install
npm run dev
```

**Access the dashboard:** http://localhost:5173

### Option 2: Docker Compose

```bash
# Start both services
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_ACCESS_KEY_ID` | For real deployments | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | For real deployments | AWS IAM secret key |
| `AWS_DEFAULT_REGION` | No (default: us-east-1) | AWS region |
| `SAGEMAKER_ENDPOINT_NAME` | For ML mode | SageMaker endpoint name |
| `S3_DEPLOYMENT_BUCKET` | For uploads | S3 bucket for code storage |
| `EC2_KEY_PAIR_NAME` | Optional | AWS key pair for SSH access |
| `EC2_SSH_PUBLIC_KEY` | Optional | SSH public key to inject into instances |

> **Note:** Without AWS credentials, the system operates in **mock mode** — recommendations use the built-in rule engine and deployments are simulated.

---

## 14. Screenshots & Demo

> _Screenshots of the running application can be added here._

### Pages

1. **Home Page** — Landing page with the requirements form
2. **Recommendations View** — ML-generated infrastructure suggestions with cost estimate
3. **Deployment Progress** — Real-time progress tracker with resource list
4. **Results Dashboard** — Live endpoint URL and monitoring links

---

## 15. Security Considerations

| Area | Implementation |
|------|----------------|
| **S3 Buckets** | Public access fully blocked (`BlockPublicAcls`, `BlockPublicPolicy`, `IgnorePublicAcls`, `RestrictPublicBuckets`) |
| **Security Groups** | Restrict inbound traffic to required ports only (80, 443, 22, 3000, 8000) |
| **IAM** | Least-privilege roles for EC2 instances — no hardcoded credentials |
| **CORS** | Configured to allow only specific origins (`localhost:5173`, `localhost:3000`) |
| **Input Validation** | Pydantic models enforce strict type checking, min/max bounds, and enum validation |
| **SSL/TLS** | Uses certifi CA bundle for secure AWS API communication |
| **Secrets** | AWS credentials loaded from environment variables, never committed to source code |

---

## 16. Future Scope

| Enhancement | Description |
|------------|-------------|
| **Multi-Cloud Support** | Extend to Azure and GCP with provider-agnostic recommendation engine |
| **Terraform Integration** | Add Terraform as an alternative IaC backend alongside CloudFormation |
| **Enhanced ML Model** | Train on a larger dataset with more features (region pricing, workload patterns, peak hours) |
| **Cost Optimization** | Integrate AWS Cost Explorer API for real-time pricing and Reserved Instance recommendations |
| **CI/CD Pipeline** | Add GitHub Actions / CodePipeline integration for continuous deployment |
| **User Authentication** | Implement OAuth2/Cognito-based user accounts with deployment history |
| **Container Support** | Add ECS/EKS/Fargate as deployment targets for containerized applications |
| **Serverless Architecture** | Support Lambda + API Gateway as a deployment option for lightweight APIs |
| **Infrastructure Drift Detection** | Monitor deployed resources and alert when they deviate from the original template |
| **Rollback Capability** | One-click rollback to previous deployment versions using CloudFormation stack updates |
| **Custom Domain & SSL** | Integrate Route 53 and ACM for automatic custom domain and HTTPS setup |
| **Collaborative Workspaces** | Multi-user support with role-based access control for team deployments |
| **Performance Benchmarking** | Post-deployment load testing and performance scoring |
| **Mobile Responsive Dashboard** | Optimize the frontend for mobile and tablet devices |

---

## 17. Conclusion

**AutoCloud Architect** demonstrates the practical application of machine learning in cloud infrastructure management. By combining a **React** frontend, **FastAPI** backend, **Amazon SageMaker** ML inference, and **AWS CloudFormation** automated provisioning, the system delivers an end-to-end solution that:

- **Reduces cloud setup time** from hours/days to minutes
- **Eliminates the need for deep AWS expertise** by translating simple requirements into production infrastructure
- **Provides cost transparency** with pre-deployment cost estimates
- **Ensures best practices** through ML-driven architecture selection and secure default configurations
- **Enables real-time visibility** into the deployment process via WebSocket updates

The project showcases proficiency in full-stack development, cloud architecture, machine learning integration, infrastructure automation, and modern DevOps practices — making it a comprehensive demonstration of building intelligent, cloud-native applications.

---

> **Project:** AutoCloud Architect  
> **Version:** 1.0.0  
> **License:** MIT  
