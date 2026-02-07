#!/bin/bash
set -euo pipefail

echo "=== AIOps Agent Setup ==="

# Check Python version
python3 --version || { echo "Python 3 is required"; exit 1; }

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check AWS credentials
echo "Verifying AWS credentials..."
aws sts get-caller-identity > /dev/null 2>&1 || {
    echo "AWS credentials not configured. Run: aws configure"
    exit 1
}

REGION=$(aws configure get region 2>/dev/null || echo "ap-northeast-2")
export AWS_REGION="${REGION}"
echo "AWS Region: ${AWS_REGION}"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Deploy infrastructure:  bash prerequisite/deploy.sh"
echo "  2. Run locally:            python -c \"from agents.aiops_agent import create_agent; a = create_agent(); print(a('EC2 상태 확인'))\""
echo "  3. Run tests:              python -m pytest tests/ -v"
