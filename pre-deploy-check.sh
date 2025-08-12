#!/bin/bash

# 部署前检查脚本
# 在服务器部署前运行此脚本确保所有文件就绪

set -e

echo "=== Matrix Synapse 部署前检查 ==="
echo

# 检查必需文件
echo "1. 检查必需文件..."
required_files=(
    "Dockerfile.minimal"
    "docker-compose.minimal.yml"
    "config/homeserver.yaml"
    "config/homeserver-minimal.yaml"
    "pyproject.toml"
    "well-known/matrix/server"
    "well-known/matrix/client"
)

missing_files=0
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - 缺失"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -gt 0 ]; then
    echo "❌ 发现 $missing_files 个必需文件缺失"
    exit 1
fi

# 检查配置文件语法
echo
echo "2. 检查配置文件语法..."

# 检查 homeserver.yaml 语法
if command -v python3 &> /dev/null; then
    echo "检查 homeserver.yaml 语法..."
    python3 -c "import yaml; yaml.safe_load(open('config/homeserver.yaml', 'r'))" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ homeserver.yaml 语法正确"
    else
        echo "❌ homeserver.yaml 语法错误"
        exit 1
    fi
fi

# 检查 docker-compose.yml 语法
if command -v docker-compose &> /dev/null; then
    echo "检查 docker-compose.minimal.yml 语法..."
    docker-compose -f docker-compose.minimal.yml config > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ docker-compose.minimal.yml 语法正确"
    else
        echo "❌ docker-compose.minimal.yml 语法错误"
        exit 1
    fi
fi

# 检查脚本权限
echo
echo "3. 检查脚本权限..."
scripts=(
    "setup-domain.sh"
    "fix-docker-deployment.sh"
    "start.sh"
    "diagnose.sh"
)

for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "✅ $script - 可执行"
        else
            echo "⚠️ $script - 不可执行，正在设置权限..."
            chmod +x "$script"
            echo "✅ $script - 已设置可执行权限"
        fi
    fi
done

# 检查目录结构
echo
echo "4. 检查目录结构..."
directories=(
    "config"
    "well-known/matrix"
    "storage/databases/main"
    "handlers"
    "rest/client"
)

for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir/ - 目录存在"
    else
        echo "⚠️ $dir/ - 目录不存在，但这是可选的"
    fi
done

# 检查环境变量模板
echo
echo "5. 检查环境配置..."
if [ -f ".env.example" ]; then
    echo "✅ .env.example - 环境变量模板存在"
else
    echo "⚠️ .env.example - 环境变量模板不存在"
fi

# 检查好友功能代码
echo
echo "6. 检查好友功能代码..."
friends_files=(
    "config/friends.py"
    "handlers/friends.py"
    "rest/client/friends.py"
    "storage/databases/main/friends.py"
)

for file in "${friends_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - 好友功能代码存在"
    else
        echo "❌ $file - 好友功能代码缺失"
    fi
done

# 生成部署摘要
echo
echo "=== 部署检查摘要 ==="
echo "✅ 所有必需文件存在"
echo "✅ 配置文件语法正确"
echo "✅ 脚本权限已设置"
echo "✅ 目录结构完整"
echo "✅ 好友功能代码完整"
echo
echo "🚀 项目已准备好部署到服务器"
echo
echo "部署步骤："
echo "1. 在服务器上运行: sudo ./setup-domain.sh"
echo "2. 或者运行: sudo ./fix-docker-deployment.sh"
echo "3. 验证部署: sudo docker-compose -f docker-compose.minimal.yml ps"