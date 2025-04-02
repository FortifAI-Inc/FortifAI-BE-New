# FortifAI Backend

This is the backend infrastructure for the FortifAI application, built on Amazon EKS with a microservices architecture.

## Architecture Overview

The backend is organized into three main layers:

1. **API Gateway Layer**
   - External REST API interface
   - Request routing and authentication
   - Rate limiting and request validation

2. **Microservices Layer**
   - Domain-specific services
   - Business logic implementation
   - Service-to-service communication

3. **Data Layer**
   - Internal data access services
   - S3 integration for Parquet files
   - Data transformation and caching

## Project Structure

```
.
├── api-gateway/           # API Gateway service
├── microservices/        # Domain-specific microservices
│   ├── service-a/       # Example microservice
│   └── service-b/       # Example microservice
├── data-layer/          # Data access services
├── infrastructure/      # Kubernetes and AWS infrastructure
│   ├── eks/            # EKS cluster configuration
│   ├── networking/     # Network policies and service mesh
│   └── monitoring/     # Monitoring and logging setup
└── shared/             # Shared libraries and utilities
```

## Prerequisites

- AWS CLI configured with appropriate credentials
- kubectl installed and configured
- Docker installed
- Helm 3.x installed
- Terraform installed (for infrastructure deployment)

## Getting Started

1. Clone the repository
2. Set up AWS credentials
3. Deploy infrastructure:
   ```bash
   cd infrastructure
   terraform init
   terraform apply
   ```
4. Deploy services:
   ```bash
   kubectl apply -f k8s/
   ```

## Development

Each service can be developed and deployed independently. See individual service directories for specific development instructions.

## Monitoring and Logging

- Prometheus and Grafana for metrics
- ELK Stack for logging
- AWS CloudWatch integration

## Security

- Network policies to isolate layers
- Service mesh for secure communication
- AWS IAM roles and policies
- Secrets management via AWS Secrets Manager

## License

Proprietary - All rights reserved 