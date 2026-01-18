#!/bin/bash

# ECR Push Script for blackkeyx/backend

set -e

AWS_ACCOUNT_ID="655506453985"
AWS_REGION="us-east-1"
ECR_REPO="blackkeyx/backend"
IMAGE_TAG="${1:-latest}"

ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "🔐 Logging into ECR..."
aws ecr get-login-password --profile blackkeyx --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URL}

echo "🔨 Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t ${ECR_REPO} .

echo "🏷️  Tagging image..."
docker tag ${ECR_REPO}:latest ${ECR_URL}/${ECR_REPO}:${IMAGE_TAG}

echo "🚀 Pushing to ECR..."
docker push ${ECR_URL}/${ECR_REPO}:${IMAGE_TAG}

echo "✅ Push complete: ${ECR_URL}/${ECR_REPO}:${IMAGE_TAG}"
