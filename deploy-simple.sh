#!/bin/bash
# Matrix Synapse 优化版部署脚本（Ubuntu）
# 优化目标：修复配置模板变量展开、路径匹配、错误处理等问题

set -Eeuo pipefail

# 发生错误时打印位置信息
trap 'echo "❌ 脚本在第 ${LINENO} 行出错，正在退出" >&2' ERR

# 颜色输出函数
print_info() { echo -e "\033[34mℹ️  $1\033[0m"; }
print_success() { echo -e "\033[32m✅ $1\033[0m"; }
print_warning() { echo -e "\033[33m⚠️  $1\033[0m"; }
print_error() { echo -e "\033[31m❌ $1\033[0m"; }

echo "=========================================="
echo "  Matrix Synapse 优化版部署脚本（Ubuntu）"
echo "  修复配置变量展开与路径匹配问题"
echo "=========================================="
echo ""

# 必须使用root运行
if [ "${EUID}" -ne 0 ]; then
  print_error "请使用root用户运行此脚本"
  echo "使用: sudo $0"
  exit 1
fi

#-----------------------------
# 系统检查与依赖安装
#-----------------------------
print_info "检查系统环境..."

if ! command -v apt-get >/dev/null 2>&1; then
  print_warning "非Debian/Ubuntu系统，自动安装依赖被跳过。请确保已安装 docker 与 docker compose。"
else
  print_info "安装基础依赖..."
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl gnupg lsb-release openssl jq gettext-base

  # Docker安装
  if ! command -v docker >/dev/null 2>&1; then
    print_info "安装 Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo $VERSION_CODENAME) stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    if command -v systemctl >/dev/null 2>&1; then
      systemctl enable --now docker || true
    fi
    print_success "Docker 安装完成"
  else
    print_info "Docker 已安装，跳过"
  fi
fi

# 选择 docker compose 命令
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  print_error "未找到 docker compose，请安装 docker-compose-plugin 或 docker-compose"
  echo "Ubuntu 安装示例: apt-get install -y docker-compose-plugin"
  exit 1
fi

# Docker 工作可用性检测
if ! docker ps >/dev/null 2>&1; then
  print_error "Docker未正常运行，请手动启动Docker服务后重试"
  exit 1
fi
print_success "Docker 环境检查通过"

#-----------------------------
# 环境变量配置
#-----------------------------
print_info "配置环境变量..."

# 获取默认服务器名
SERVER_NAME_DEFAULT=$(hostname -f 2>/dev/null || hostname)
SERVER_NAME_DEFAULT=$(echo "$SERVER_NAME_DEFAULT" | sed 's/^*\.*//')

# 创建或检查 .env 配置
if [ ! -f .env ]; then
  print_info "创建 .env 配置文件..."
  cat > .env << EOF
# Matrix Synapse 配置
MATRIX_SERVER_NAME=${SERVER_NAME_DEFAULT}
POSTGRES_USER=synapse
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=synapse
REGISTRATION_SHARED_SECRET=$(openssl rand -base64 32)
MACAROON_SECRET_KEY=$(openssl rand -base64 32)
FORM_SECRET=$(openssl rand -base64 32)
REPORT_STATS=no
ENABLE_REGISTRATION=false
FRIENDS_ENABLED=true

# Docker 配置
SYNAPSE_CONFIG_PATH=/data/homeserver.yaml
EOF
  print_success ".env 文件创建完成"
else
  print_info "已存在 .env，保持配置不变"
fi

# 加载环境变量
set -a  # 自动导出变量
source .env
set +a

# 验证关键配置
if [ -z "${MATRIX_SERVER_NAME:-}" ]; then
  print_error "MATRIX_SERVER_NAME 未设置"
  exit 1
fi

#-----------------------------
# 生成经过变量展开的配置文件
#-----------------------------
print_info "生成 homeserver.yaml 配置..."

# 创建 data 目录
print_info "创建数据目录..."
mkdir -p data media uploads

# 设置目录权限（991:991 是容器内 synapse 用户的 UID:GID）
print_info "设置目录权限..."
chown -R 991:991 data media uploads
chmod -R 755 data media uploads

# 生成 homeserver.yaml（使用实际值替换模板变量）
cat > data/homeserver.yaml << EOF
# Matrix Synapse 配置文件（自动生成）
# 服务器: ${MATRIX_SERVER_NAME}

server_name: "${MATRIX_SERVER_NAME}"
pid_file: /data/homeserver.pid
web_client: false
public_baseurl: "https://${MATRIX_SERVER_NAME}/"

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

# 数据库配置 - 为 1vCPU/2GB RAM 服务器优化
database:
  name: psycopg2
  args:
    user: "${POSTGRES_USER}"
    password: "${POSTGRES_PASSWORD}"
    database: "${POSTGRES_DB}"
    host: postgres
    port: 5432
    cp_min: 1              # 最小连接数（低配服务器）
    cp_max: 2              # 最大连接数（原3，升级服务器后可调为5-10）
    connect_timeout: 10

# 日志配置
log_config: "/data/log.config"

# 媒体存储
media_store_path: "/data/media"
uploads_path: "/data/uploads"

# 性能优化 - 为 1vCPU/2GB RAM 服务器优化
caches:
  global_factor: 0.2      # 降低缓存以节省内存（原0.3，升级服务器后可调为0.5-1.0）
  event_cache_size: 500   # 降低事件缓存（原1000，升级服务器后可调为2000-5000）

# 注册配置
# 旧配置（保留作为升级服务器后的参考）：
# enable_registration: ${ENABLE_REGISTRATION}
# registration_shared_secret: "${REGISTRATION_SHARED_SECRET}"
# 说明：以上为原有配置，依赖共享密钥的注册流程。
# -----------------------------------------------
# 当前配置：开启无验证注册，且限制注册间隔为10分钟
enable_registration: true
# 禁用三方验证（如邮件/验证码），保持开放注册
# 注意：生产环境下建议开启验证或使用邀请制

# 注册速率限制（10分钟内最多1次）
rc_registration:
  per_second: 0.0017   # ≈ 每10分钟 1 次 (1/600)
  burst_count: 1       # 不允许突发多次注册

# 好友功能
friends:
  enabled: ${FRIENDS_ENABLED}
  max_friends_per_user: 100
  rate_limiting:
    max_requests_per_hour: 10
    rate_limit_window: 3600

# 速率限制
# rc_registration 已在上方设置为每10分钟1次
rc_login:
  per_second: 0.2
  burst_count: 5

rc_message:
  per_second: 0.5   # 降低消息速率以降低CPU负载（升级后可调回1）
  burst_count: 10   # 降低突发量（升级后可调回20）

# 媒体配置（低配优化）
max_upload_size: "8M"   # 降低上传大小限制（升级后可调为 20M/50M）
media_retention:
  remote_media_lifetime: "7d"
  local_media_lifetime: "30d"

# 统计配置
report_stats: ${REPORT_STATS}

# 安全配置
macaroon_secret_key: "${MACAROON_SECRET_KEY}"
form_secret: "${FORM_SECRET}"
signing_key_path: "/data/signing.key"
suppress_key_server_warning: true

# 联邦密钥服务器
trusted_key_servers:
  - server_name: "matrix.org"

# 隐私设置
allow_public_rooms_over_federation: false
allow_public_rooms_without_auth: false

# 禁用不必要功能以节省资源
push:
  enabled: false
# 完全禁用 email 功能 - 不设置 email 配置块以避免 notif_from 要求
# email:
#   enabled: false
server_notices:
  enabled: false
redis:
  enabled: false

# 性能优化配置
use_presence: false    # 禁用在线状态以节省资源
enable_metrics: false  # 禁用指标收集
allow_guest_access: false
enable_media_repo: true
EOF

# 生成日志配置
cat > data/log.config << EOF
version: 1

formatters:
  precise:
    format: '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(request)s - %(message)s'

filters:
  context:
    (): synapse.logging.context.LoggingContextFilter
    request: ""

handlers:
  file:
    class: logging.handlers.TimedRotatingFileHandler
    formatter: precise
    filename: /data/synapse.log
    when: midnight
    backupCount: 3
    filters: [context]
  console:
    class: logging.StreamHandler
    formatter: precise
    filters: [context]

loggers:
  synapse.storage.SQL:
    level: WARN

root:
  level: INFO
  handlers: [file, console]

disable_existing_loggers: false
EOF

print_success "配置文件生成完成"

#-----------------------------
# 创建 well-known 配置
#-----------------------------
print_info "创建 well-known 配置..."

mkdir -p well-known/.well-known/matrix

# 服务器发现配置（注意端口）
cat > well-known/.well-known/matrix/server << EOF
{
  "m.server": "${MATRIX_SERVER_NAME}:8008"
}
EOF

# 客户端发现配置
cat > well-known/.well-known/matrix/client << EOF
{
  "m.homeserver": {
    "base_url": "https://${MATRIX_SERVER_NAME}"
  },
  "m.identity_server": {
    "base_url": "https://vector.im"
  }
}
EOF

print_success "well-known 配置完成"

#-----------------------------
# 生成 docker-compose 配置
#-----------------------------
print_info "生成 docker-compose.simple.yml..."

cat > docker-compose.simple.yml << 'EOF'
# Docker Compose 配置 - 为 1vCPU/2GB RAM 服务器优化
# 升级服务器后可调整资源限制

services:
  postgres:
    image: postgres:15-alpine
    container_name: matrix-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-synapse}
      - POSTGRES_USER=${POSTGRES_USER:-synapse}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
      # 为低配服务器优化的数据库设置
      - POSTGRES_SHARED_BUFFERS=128MB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=512MB
      - POSTGRES_WORK_MEM=4MB
      - POSTGRES_MAINTENANCE_WORK_MEM=64MB
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - matrix-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-synapse}"]
      interval: 30s  # 降低检查频率
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          # 低配服务器资源分配 (当前: 1vCPU/2GB)
          memory: 400M
          cpus: '0.25'
        # 升级服务器后可调整为:
        # limits:
        #   memory: 1G
        #   cpus: '0.5'

  synapse:
    build:
      context: .
      dockerfile: Dockerfile.simple
    container_name: matrix-synapse
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - SYNAPSE_CONFIG_PATH=/data/homeserver.yaml
      # 优化 Python 内存使用
      - PYTHONOPTIMIZE=1
      - PYTHONDONTWRITEBYTECODE=1
    volumes:
      - ./data:/data
      - ./media:/data/media
      - ./uploads:/data/uploads
    ports:
      - "127.0.0.1:8008:8008"  # 只绑定本地地址，通过Nginx代理访问
    networks:
      - matrix-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8008/_matrix/client/versions"]
      interval: 60s  # 降低检查频率节省资源
      timeout: 15s
      retries: 3
      start_period: 120s  # 给低配服务器更多启动时间
    deploy:
      resources:
        limits:
          # 低配服务器资源分配 (当前: 1vCPU/2GB)
          memory: 1.2G  # 给synapse分配大部分内存
          cpus: '0.7'
        # 升级服务器后可调整为:
        # limits:
        #   memory: 2G
        #   cpus: '1.5'

  well-known:
    image: nginx:alpine
    container_name: matrix-well-known
    restart: unless-stopped
    volumes:
      - ./well-known:/usr/share/nginx/html:ro
    ports:
      - "8080:80"
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          # 低配服务器资源分配
          memory: 24M
          cpus: '0.05'
        # 升级服务器后可调整为:
        # limits:
        #   memory: 64M
        #   cpus: '0.1'

volumes:
  postgres_data:
    driver: local

networks:
  matrix-network:
    driver: bridge
EOF

print_success "docker-compose.simple.yml 生成完成"

#-----------------------------
# 验证配置文件
#-----------------------------
print_info "验证配置文件语法..."

# 检查 YAML 语法
if command -v python3 >/dev/null 2>&1; then
  python3 -c "import yaml; yaml.safe_load(open('data/homeserver.yaml', 'r'))" 2>/dev/null || {
    print_error "homeserver.yaml 语法错误"
    exit 1
  }
  print_success "配置文件语法验证通过"
fi

#-----------------------------
# 启动服务
#-----------------------------
print_info "启动 Matrix Synapse 服务..."

# 停止可能存在的旧服务
${COMPOSE} -f docker-compose.simple.yml down --remove-orphans >/dev/null 2>&1 || true

# 构建并启动服务
print_info "构建和启动容器（这可能需要几分钟）..."
# 先强制无缓存构建，避免使用旧的 Dockerfile 缓存
${COMPOSE} -f docker-compose.simple.yml build --no-cache synapse

# 生成签名密钥（如果不存在）
if [ ! -f "data/signing.key" ]; then
  print_info "生成 Matrix Synapse 签名密钥..."
  ${COMPOSE} -f docker-compose.simple.yml run --rm synapse \
    python -m synapse.app.homeserver \
    --config-path /data/homeserver.yaml \
    --generate-keys
  print_success "签名密钥生成完成"
else
  print_info "签名密钥已存在，跳过生成"
fi

${COMPOSE} -f docker-compose.simple.yml up -d

# 等待服务就绪
print_info "等待服务启动..."
ATTEMPTS=60
SERVICE_READY=false

while [ $ATTEMPTS -gt 0 ]; do
  if curl -fsS http://127.0.0.1:8008/_matrix/client/versions >/dev/null 2>&1; then
    SERVICE_READY=true
    break
  fi
  ATTEMPTS=$((ATTEMPTS-1))
  sleep 5
  echo "...等待中 (剩余尝试: $ATTEMPTS)"
done

if [ "$SERVICE_READY" = false ]; then
  print_error "服务未在预期时间内就绪"
  echo ""
  print_info "查看容器状态:"
  ${COMPOSE} -f docker-compose.simple.yml ps
  echo ""
  print_info "查看 Synapse 日志:"
  ${COMPOSE} -f docker-compose.simple.yml logs synapse --tail=50
  exit 1
fi

# 最终状态检查
if ${COMPOSE} -f docker-compose.simple.yml ps | grep -E "(Up|healthy)" >/dev/null; then
  print_success "Matrix Synapse 部署成功！"
else
  print_error "服务状态异常"
  ${COMPOSE} -f docker-compose.simple.yml ps
  exit 1
fi

#-----------------------------
# 部署完成信息
#-----------------------------
echo ""
echo "=========================================="
print_success "Matrix 服务器部署完成！"
echo ""
echo "🔧 管理命令："
echo "  查看状态: ${COMPOSE} -f docker-compose.simple.yml ps"
echo "  查看日志: ${COMPOSE} -f docker-compose.simple.yml logs -f synapse"
echo "  停止服务: ${COMPOSE} -f docker-compose.simple.yml down"
echo "  重启服务: ${COMPOSE} -f docker-compose.simple.yml restart"
echo ""
echo "🧪 测试命令："
echo "  API测试: curl -s http://127.0.0.1:8008/_matrix/client/versions | jq ."
echo "  健康检查: curl -f http://127.0.0.1:8008/_matrix/client/versions"
echo "  well-known: curl -s http://127.0.0.1:8080/.well-known/matrix/server"
echo ""
echo "👤 创建管理员用户："
echo "  ${COMPOSE} -f docker-compose.simple.yml exec synapse \\"
echo "    register_new_matrix_user -c /data/homeserver.yaml \\"
echo "    -a http://localhost:8008"
echo ""
echo "📌 重要提示："
echo "  - 当前服务运行在 http://127.0.0.1:8008"
echo "  - well-known 服务运行在 http://127.0.0.1:8080"
echo "  - 生产环境请配置反向代理(Nginx)并启用HTTPS"
echo "  - 配置文件位于: ./data/homeserver.yaml"
echo "  - 数据存储于: ./data/, ./media/, ./uploads/"
echo ""
echo "🔐 安全建议："
echo "  - 修改 .env 中的默认密码"
echo "  - 配置防火墙规则"
echo "  - 定期备份数据目录"
echo "=========================================="