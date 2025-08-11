#!/bin/bash
# GitHub Repository Setup Script

echo "🚀 GitHub Repository Setup Script"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get repository name
read -p "Enter repository name (default: matrix-synapse-friends): " REPO_NAME
REPO_NAME=${REPO_NAME:-matrix-synapse-friends}

# Get repository description
read -p "Enter repository description (default: Matrix Synapse server with friends functionality): " REPO_DESC
REPO_DESC=${REPO_DESC:-Matrix Synapse server with friends functionality}

# Check if git remote exists
if git remote -v | grep -q "origin"; then
    echo -e "${YELLOW}Remote 'origin' already exists${NC}"
    git remote -v
    read -p "Do you want to continue with existing remote? (y/n): " CONTINUE
    if [[ $CONTINUE != "y" ]]; then
        echo "Exiting..."
        exit 1
    fi
else
    echo -e "${YELLOW}No remote 'origin' found${NC}"
    echo "Please create a GitHub repository manually:"
    echo ""
    echo "1. Go to https://github.com"
    echo "2. Click 'New repository'"
    echo "3. Repository name: $REPO_NAME"
    echo "4. Description: $REPO_DESC"
    echo "5. Set to Public or Private as needed"
    echo "6. Don't initialize with README (we already have one)"
    echo "7. Click 'Create repository'"
    echo ""
    read -p "Press Enter after you've created the repository..."
    
    # Get GitHub URL
    read -p "Enter your GitHub username: " GITHUB_USER
    GITHUB_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"
    
    # Add remote
    echo -e "${GREEN}Adding remote origin...${NC}"
    git remote add origin "$GITHUB_URL"
fi

# Push to GitHub
echo -e "${GREEN}Pushing code to GitHub...${NC}"
git push -u origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Successfully pushed to GitHub!${NC}"
    echo ""
    echo "📋 Repository Details:"
    echo "   Name: $REPO_NAME"
    echo "   Description: $REPO_DESC"
    echo "   URL: $GITHUB_URL"
    echo ""
    echo "🚀 Quick deployment commands:"
    echo "   Clone: git clone $GITHUB_URL"
    echo "   Deploy: cd $REPO_NAME && sudo ./deploy.sh"
    echo ""
    echo "📖 Documentation available in:"
    echo "   - README.md (general overview)"
    echo "   - DOCKER_PRODUCTION_DEPLOYMENT.md (detailed deployment)"
    echo "   - UBUNTU_DOCKER_DEPLOYMENT_MINIMAL.md (minimal deployment)"
else
    echo -e "${RED}❌ Failed to push to GitHub${NC}"
    echo "Please check your GitHub credentials and repository URL"
fi