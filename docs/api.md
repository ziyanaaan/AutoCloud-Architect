# AutoCloud Architect - API Reference

Base URL: `http://localhost:8000/api/v1`

---

## Endpoints

### POST /analyze

Analyze requirements and get infrastructure recommendations.

**Request Body:**
```json
{
  "app_name": "my-web-app",
  "app_type": "web",
  "description": "A modern web application",
  "expected_users": 1000,
  "data_size_gb": 50,
  "performance_priority": "balanced",
  "budget_tier": "medium",
  "requires_database": true,
  "requires_load_balancer": true,
  "requires_auto_scaling": false
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "app_name": "my-web-app",
  "recommendations": {
    "compute": {
      "instance_type": "t3.medium",
      "instance_count": 2,
      "use_spot": false
    },
    "storage": {
      "s3_bucket": true,
      "storage_class": "STANDARD"
    },
    "database": {
      "db_type": "rds-mysql",
      "instance_class": "db.t3.micro",
      "multi_az": false
    },
    "networking": {
      "use_alb": true,
      "public_subnets": 2,
      "private_subnets": 2
    },
    "estimated_monthly_cost_usd": 150.00,
    "confidence_score": 0.92
  }
}
```

---

### POST /deploy

Start infrastructure deployment.

**Request Body:**
```json
{
  "job_id": "uuid-from-analyze",
  "requirements": { ... },
  "recommendations": { ... },
  "code_url": "s3://bucket/app.zip"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "app_name": "my-web-app",
  "status": {
    "state": "pending",
    "progress_percent": 0,
    "current_step": "Initializing",
    "message": "Deployment job created"
  }
}
```

---

### GET /deploy/{job_id}

Get deployment status.

**Response:**
```json
{
  "job_id": "uuid",
  "app_name": "my-web-app",
  "status": {
    "state": "completed",
    "progress_percent": 100,
    "current_step": "Deployment complete",
    "resources": [
      {
        "resource_type": "AWS::EC2::Instance",
        "resource_id": "i-1234567890",
        "status": "CREATE_COMPLETE"
      }
    ]
  },
  "endpoint_url": "http://54.123.45.67",
  "cloudwatch_dashboard_url": "..."
}
```

---

### POST /upload

Upload application code.

**Request:** `multipart/form-data` with `file` field

**Response:**
```json
{
  "upload_id": "uuid",
  "filename": "app.zip",
  "url": "s3://bucket/uploads/uuid/app.zip"
}
```

---

## WebSocket

### /ws/deploy/{job_id}

Real-time deployment updates.

**Messages:**
```json
{
  "type": "deployment_update",
  "job_id": "uuid",
  "status": { ... }
}
```

---

## Enums

**app_type:** `web`, `api`, `static`, `ml`

**performance_priority:** `low`, `balanced`, `high`

**budget_tier:** `low`, `medium`, `high`

**deployment_state:** `pending`, `analyzing`, `provisioning`, `deploying`, `verifying`, `completed`, `failed`
