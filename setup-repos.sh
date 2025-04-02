#!/bin/bash

# Configuration
ORG_NAME="FortifAI-Inc"
REPOS=(
    "infrastructure"
    "api-gateway"
    "microservices"
    "data-layer"
)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to create a repository
create_repo() {
    local repo_name=$1
    echo -e "${BLUE}Creating repository: ${GREEN}$repo_name${NC}"
    
    # Create directory
    mkdir -p $repo_name
    cd $repo_name
    
    # Initialize git
    git init
    
    # Create .gitignore
    cat > .gitignore << EOL
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Local development
.env
.env.local
.env.*.local

# Kubernetes
kubeconfig
*.kubeconfig

# AWS
.aws/
aws.credentials
EOL
    
    # Create README.md
    cat > README.md << EOL
# FortifAI - $repo_name

This repository is part of the FortifAI backend infrastructure.

## Overview

$(case $repo_name in
    "infrastructure")
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
   \`\`\`bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\\venv\\Scripts\\activate
   \`\`\`
3. Install dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

### Development Workflow

1. Create a feature branch:
   \`\`\`bash
   git checkout -b feature/your-feature-name
   \`\`\`
2. Make your changes
3. Run tests:
   \`\`\`bash
   pytest
   \`\`\`
4. Commit your changes:
   \`\`\`bash
   git add .
   git commit -m "feat: your feature description"
   \`\`\`
5. Push to GitHub:
   \`\`\`bash
   git push origin feature/your-feature-name
   \`\`\`
6. Create a Pull Request

## License

Proprietary - All rights reserved
EOL
    
    # Create initial commit
    git add .
    git commit -m "Initial commit"
    
    # Create repository on GitHub
    gh repo create $ORG_NAME/$repo_name --public --source=. --remote=origin
    
    # Push to GitHub
    git push -u origin main
    
    cd ..
}

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI is not installed. Please install it first:"
    echo "https://cli.github.com/manual/installation"
    exit 1
fi

# Check if user is logged in to GitHub
if ! gh auth status &> /dev/null; then
    echo "Please login to GitHub first:"
    echo "gh auth login"
    exit 1
fi

# Create each repository
for repo in "${REPOS[@]}"; do
    create_repo $repo
done

echo -e "${GREEN}All repositories have been created successfully!${NC}" 
