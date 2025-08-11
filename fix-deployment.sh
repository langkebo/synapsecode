#!/bin/bash
# 临时修复脚本 - 解决well-known目录问题

echo "🔧 修复well-known目录问题..."

# 创建正确的目录结构
mkdir -p well-known/.well-known/matrix

# 创建server配置文件
cat > well-known/.well-known/matrix/server << EOF
{
    "m.server": "$(hostname -f | sed 's/^*\.//'):8008"
}
EOF

# 创建client配置文件
cat > well-known/.well-known/matrix/client << EOF
{
    "m.homeserver": {
        "base_url": "https://$(hostname -f | sed 's/^*\.//')"
    }
}
EOF

echo "✅ well-known目录修复完成"

# 继续部署
echo "🚀 继续部署Matrix服务..."
docker-compose -f docker-compose.minimal.yml down --remove-orphans
docker-compose -f docker-compose.minimal.yml up -d --build

echo "⏳ 等待服务启动..."
sleep 30

echo "📊 检查服务状态..."
docker-compose -f docker-compose.minimal.yml ps