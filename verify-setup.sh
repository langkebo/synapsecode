#!/bin/bash
# Matrix Server Setup Verification Script

echo "🔍 Matrix Server Setup Verification"
echo "=================================="

# Check required files
REQUIRED_FILES=(
    "pyproject.toml"
    "Dockerfile" 
    "docker-compose.yml"
    ".env.example"
    "README.md"
    "deploy.sh"
    "DOCKER_PRODUCTION_DEPLOYMENT.md"
)

echo "📋 Checking required files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
    fi
done

# Check friends functionality
echo ""
echo "👥 Checking friends functionality..."
FRIENDS_FILES=(
    "config/friends.py"
    "storage/databases/main/friends.py"
    "handlers/friends.py"
    "rest/client/friends.py"
)

for file in "${FRIENDS_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
    fi
done

# Check Docker configuration
echo ""
echo "🐳 Checking Docker configuration..."
if [[ -d "docker" ]]; then
    echo "✅ docker/ directory"
    
    DOCKER_CONFIGS=(
        "docker/postgres/postgresql.conf"
        "docker/nginx/well-known.conf"
        "docker/prometheus/prometheus.yml"
        "docker/grafana/datasources/prometheus.yml"
    )
    
    for config in "${DOCKER_CONFIGS[@]}"; do
        if [[ -f "$config" ]]; then
            echo "✅ $config"
        else
            echo "❌ $config - MISSING"
        fi
    done
else
    echo "❌ docker/ directory - MISSING"
fi

# Check development files
echo ""
echo "🛠️ Checking development files..."
DEV_FILES=(
    "docker-compose.override.yml"
    "Dockerfile.dev"
)

for file in "${DEV_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
    fi
done

# Check documentation
echo ""
echo "📚 Checking documentation..."
DOCS=(
    "README.md"
    "DOCKER_PRODUCTION_DEPLOYMENT.md"
)

for doc in "${DOCS[@]}"; do
    if [[ -f "$doc" ]]; then
        echo "✅ $doc"
    else
        echo "❌ $doc - MISSING"
    fi
done

# Check scripts
echo ""
echo "🔧 Checking scripts..."
SCRIPTS=(
    "deploy.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [[ -f "$script" ]]; then
        if [[ -x "$script" ]]; then
            echo "✅ $script (executable)"
        else
            echo "⚠️ $script (not executable)"
        fi
    else
        echo "❌ $script - MISSING"
    fi
done

# Check directories
echo ""
echo "📁 Checking directories..."
DIRS=(
    "well-known"
    "synapsecode"
    "docker"
)

for dir in "${DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "✅ $dir/"
    else
        echo "❌ $dir/ - MISSING"
    fi
done

echo ""
echo "=================================="
echo "✅ Verification complete!"
echo ""
echo "🚀 Ready to deploy with: sudo ./deploy.sh"
echo "📖 Or follow manual setup in DOCKER_PRODUCTION_DEPLOYMENT.md"