#!/bin/bash
# Matrix服务器域名配置脚本

echo "🌐 Matrix服务器域名配置"
echo "========================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root用户运行此脚本"
    echo "使用: sudo $0"
    exit 1
fi

# 获取域名配置
read -p "请输入您的Matrix服务器域名 (例如: matrix.cjystx.top): " MATRIX_DOMAIN
read -p "请输入您的主域名 (例如: cjystx.top): " MAIN_DOMAIN

if [ -z "$MATRIX_DOMAIN" ] || [ -z "$MAIN_DOMAIN" ]; then
    echo "❌ 域名不能为空"
    exit 1
fi

echo ""
echo "📋 域名配置信息："
echo "   Matrix服务器: $MATRIX_DOMAIN"
echo "   主域名: $MAIN_DOMAIN"
echo ""

# 更新.env文件
echo "🔧 更新环境配置..."
if [ -f .env ]; then
    # 备份原文件
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

cat > .env << EOF
# 服务器配置
MATRIX_SERVER_NAME=${MATRIX_DOMAIN}
MATRIX_DOMAIN=${MAIN_DOMAIN}
ADMIN_EMAIL=admin@${MAIN_DOMAIN}

# 功能开关
ENABLE_REGISTRATION=false
FRIENDS_ENABLED=true
MAX_FRIENDS_PER_USER=100

# 数据库配置
POSTGRES_USER=synapse
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=synapse

# 安全密钥
REGISTRATION_SHARED_SECRET=$(openssl rand -base64 32)
MACAROON_SECRET_KEY=$(openssl rand -base64 32)
FORM_SECRET=$(openssl rand -base64 32)

# 统计报告
REPORT_STATS=no
EOF

echo "✅ .env文件更新完成"

# 更新well-known配置
echo "🌐 更新well-known配置..."
mkdir -p well-known/.well-known/matrix

cat > well-known/.well-known/matrix/server << EOF
{
    "m.server": "${MATRIX_DOMAIN}:8008"
}
EOF

cat > well-known/.well-known/matrix/client << EOF
{
    "m.homeserver": {
        "base_url": "https://${MATRIX_DOMAIN}"
    }
}
EOF

echo "✅ well-known配置完成"

# 创建 homeserver.yaml 配置
echo "⚙️ 创建 homeserver.yaml 配置..."
mkdir -p config

cat > config/homeserver.yaml << EOF
# Matrix Synapse 配置
server_name: "${MATRIX_DOMAIN}"
pid_file: /data/homeserver.pid
web_client: false
public_baseurl: "https://${MATRIX_DOMAIN}/"

# 监听配置
listeners:
  - port: 8008
    tls: false
    bind_addresses: ['0.0.0.0']
    type: http
    x_forwarded: true
    
    resources:
      - names: [client, federation]
        compress: false

# 数据库配置
database:
  name: psycopg2
  args:
    user: "\${POSTGRES_USER}"
    password: "\${POSTGRES_PASSWORD}"
    database: "\${POSTGRES_DB}"
    host: postgres
    port: 5432
    cp_min: 1
    cp_max: 2

# 日志配置
log_config: "/data/synapse.log.config"

# 媒体存储
media_store_path: "/data/media"

# 性能优化
caches:
  global_factor: 0.2
  event_cache_size: 500

# 注册配置
enable_registration: \${ENABLE_REGISTRATION}
registration_shared_secret: "\${REGISTRATION_SHARED_SECRET}"

# 好友功能
friends:
  enabled: \${FRIENDS_ENABLED}
  max_friends_per_user: \${MAX_FRIENDS_PER_USER}

# 速率限制
rc_registration:
  per_second: 0.17
  burst_count: 3

# 限制最大文件上传大小
max_upload_size: "10M"

# 媒体保留时间
media_retention:
  remote_media_lifetime: "7d"
  local_media_lifetime: "14d"
EOF

echo "✅ homeserver.yaml配置完成"

# 显示配置结果
echo ""
echo "🎯 配置完成！请确认以下信息："
echo "   Matrix服务器地址: https://${MATRIX_DOMAIN}"
echo "   服务器端口: 8008"
echo "   well-known配置: https://${MAIN_DOMAIN}/.well-known/matrix/"
echo ""
echo "📋 下一步操作："
echo "   1. 确保域名DNS解析指向服务器IP"
echo "   2. 配置反向代理和SSL证书"
echo "   3. 重新启动服务"
echo ""
echo "🚀 重新部署命令："
echo "   docker-compose -f docker-compose.minimal.yml down"
echo "   docker-compose -f docker-compose.minimal.yml up -d --build"