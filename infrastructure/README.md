# FortifAI - infrastructure

This repository is part of the FortifAI backend infrastructure.

## Overview


        echo "Contains all infrastructure code (Terraform, Kubernetes manifests) for the FortifAI platform."
        ;;
    "api-gateway")
        echo "API Gateway service that handles external request routing and authentication."
        ;;
    "microservices")
        echo "Collection of domain-specific microservices for the FortifAI platform."
        ;;
    "data-layer")
        echo "Data access layer that handles S3 interactions and data transformations."
        ;;
esac)

## Development

### Prerequisites

- Python 3.11+
- Docker
- AWS CLI
- kubectl
- Terraform (for infrastructure)

### Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Run tests:
   ```bash
   pytest
   ```
4. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```
5. Push to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```
6. Create a Pull Request

## License

Proprietary - All rights reserved
