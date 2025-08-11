#!/bin/bash
# Matrix Synapse 简化版部署脚本

set -e

echo "=========================================="
echo "  Matrix Synapse 简化版部署脚本"
echo "  避免Poetry配置问题"
echo "=========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root用户运行此脚本"
    echo "使用: sudo $0"
    exit 1
fi

# 创建配置文件
echo "📝 创建配置文件..."
if [ ! -f .env ]; then
    cat > .env << EOF
MATRIX_SERVER_NAME=$(hostname -f | sed 's/^*\\.//')
POSTGRES_USER=synapse
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=synapse
REGISTRATION_SHARED_SECRET=$(openssl rand -base64 32)
MACAROON_SECRET_KEY=$(openssl rand -base64 32)
FORM_SECRET=$(openssl rand -base64 32)
REPORT_STATS=no
ENABLE_REGISTRATION=false
FRIENDS_ENABLED=true
EOF
    echo "✅ .env文件创建完成"
fi

# 创建well-known目录
mkdir -p well-known/.well-known/matrix
cat > well-known/.well-known/matrix/server << EOF
{
    "m.server": "$(hostname -f | sed 's/^*\\.//'):8008"
}
EOF
cat > well-known/.well-known/matrix/client << EOF
{
    "m.homeserver": {
        "base_url": "https://$(hostname -f | sed 's/^*\\.//')"
    }
}
EOF
echo "✅ well-known配置完成"

# 创建简化的docker-compose
echo "🐳 创建简化版docker-compose配置..."
cat > docker-compose.simple.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: matrix-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-synapse}
      - POSTGRES_USER=${POSTGRES_USER:-synapse}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.3'

  synapse:
    build: 
      context: .
      dockerfile: Dockerfile.simple
    container_name: matrix-synapse
    restart: unless-stopped
    depends_on:
      - postgres
    environment:
      - SYNAPSE_SERVER_NAME=${MATRIX_SERVER_NAME}
      - SYNAPSE_REPORT_STATS=${REPORT_STATS:-no}
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=${POSTGRES_DB:-synapse}
      - POSTGRES_USER=${POSTGRES_USER:-synapse}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - REGISTRATION_SHARED_SECRET=${REGISTRATION_SHARED_SECRET}
      - MACAROON_SECRET_KEY=${MACAROON_SECRET_KEY}
      - FORM_SECRET=${FORM_SECRET}
      - ENABLE_REGISTRATION=${ENABLE_REGISTRATION:-false}
      - FRIENDS_ENABLED=${FRIENDS_ENABLED:-true}
    volumes:
      - synapse_data:/data
      - synapse_media:/media
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.7'

  well-known:
    image: nginx:alpine
    container_name: matrix-well-known
    restart: unless-stopped
    volumes:
      - ./well-known:/usr/share/nginx/html:ro
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 32M
          cpus: '0.05'

volumes:
  postgres_data:
    driver: local
  synapse_data:
    driver: local
  synapse_media:
    driver: local

networks:
  matrix-network:
    driver: bridge
EOF
echo "✅ 简化版docker-compose配置完成"

# 启动服务
echo "🚀 启动Matrix服务..."
docker-compose -f docker-compose.simple.yml down --remove-orphans
docker-compose -f docker-compose.simple.yml up -d --build

echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
if docker-compose -f docker-compose.simple.yml ps | grep -q "Up"; then
    echo "✅ 服务启动成功！"
else
    echo "❌ 服务启动失败"
    docker-compose -f docker-compose.simple.yml logs
    exit 1
fi

echo "=========================================="
echo "✅ Matrix服务器部署完成！"
echo ""
echo "🔧 管理命令："
echo "  查看状态: docker-compose -f docker-compose.simple.yml ps"
echo "  查看日志: docker-compose -f docker-compose.simple.yml logs -f"
echo "  停止服务: docker-compose -f docker-compose.simple.yml down"
echo "=========================================="