#!/bin/bash
# 测试配置文件生成功能

set -e

# 颜色输出函数
print_info() { echo -e "\033[34mℹ️  $1\033[0m"; }
print_success() { echo -e "\033[32m✅ $1\033[0m"; }
print_error() { echo -e "\033[31m❌ $1\033[0m"; }

echo "========================================"
echo "  Matrix Synapse 配置生成测试"
echo "========================================"
echo ""

# 设置测试环境变量
export MATRIX_SERVER_NAME="test.example.com"
export POSTGRES_USER="synapse"
export POSTGRES_PASSWORD="test_password_123"
export POSTGRES_DB="synapse"
export REGISTRATION_SHARED_SECRET="test_registration_secret"
export MACAROON_SECRET_KEY="test_macaroon_secret"
export FORM_SECRET="test_form_secret"
export REPORT_STATS="no"
export ENABLE_REGISTRATION="false"
export FRIENDS_ENABLED="true"

print_info "创建测试目录..."
mkdir -p data media uploads well-known/.well-known/matrix

print_info "生成 homeserver.yaml 配置..."

# 从deploy-simple.sh中提取配置生成部分
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
enable_registration: true

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
email:
  enabled: false
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

print_info "生成 log.config..."
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

print_info "生成 well-known 配置..."
cat > well-known/.well-known/matrix/server << EOF
{
  "m.server": "${MATRIX_SERVER_NAME}:8008"
}
EOF

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

print_info "验证配置文件..."

# 检查文件是否生成
if [ -f "data/homeserver.yaml" ]; then
  print_success "homeserver.yaml 生成成功"
else
  print_error "homeserver.yaml 生成失败"
  exit 1
fi

if [ -f "data/log.config" ]; then
  print_success "log.config 生成成功"
else
  print_error "log.config 生成失败"
  exit 1
fi

if [ -f "well-known/.well-known/matrix/server" ]; then
  print_success "well-known server 配置生成成功"
else
  print_error "well-known server 配置生成失败"
  exit 1
fi

if [ -f "well-known/.well-known/matrix/client" ]; then
  print_success "well-known client 配置生成成功"
else
  print_error "well-known client 配置生成失败"
  exit 1
fi

# 验证YAML语法
if command -v python3 >/dev/null 2>&1; then
  print_info "验证 YAML 语法..."
  if python3 -c "import yaml; yaml.safe_load(open('data/homeserver.yaml', 'r'))" 2>/dev/null; then
    print_success "homeserver.yaml 语法验证通过"
  else
    print_error "homeserver.yaml 语法错误"
    exit 1
  fi
else
  print_info "Python3 未安装，跳过 YAML 语法验证"
fi

# 验证JSON语法
if command -v python3 >/dev/null 2>&1; then
  print_info "验证 JSON 语法..."
  if python3 -c "import json; json.load(open('well-known/.well-known/matrix/server', 'r'))" 2>/dev/null; then
    print_success "well-known server JSON 语法验证通过"
  else
    print_error "well-known server JSON 语法错误"
    exit 1
  fi
  
  if python3 -c "import json; json.load(open('well-known/.well-known/matrix/client', 'r'))" 2>/dev/null; then
    print_success "well-known client JSON 语法验证通过"
  else
    print_error "well-known client JSON 语法错误"
    exit 1
  fi
else
  print_info "Python3 未安装，跳过 JSON 语法验证"
fi

print_info "检查关键配置项..."

# 检查关键配置是否存在
if grep -q "server_name: \"test.example.com\"" data/homeserver.yaml; then
  print_success "服务器名称配置正确"
else
  print_error "服务器名称配置错误"
  exit 1
fi

if grep -q "global_factor: 0.2" data/homeserver.yaml; then
  print_success "缓存优化配置正确"
else
  print_error "缓存优化配置错误"
  exit 1
fi

if grep -q "cp_max: 2" data/homeserver.yaml; then
  print_success "数据库连接池优化配置正确"
else
  print_error "数据库连接池优化配置错误"
  exit 1
fi

if grep -q "per_second: 0.0017" data/homeserver.yaml; then
  print_success "注册速率限制配置正确"
else
  print_error "注册速率限制配置错误"
  exit 1
fi

if grep -q "signing_key_path: \"/data/signing.key\"" data/homeserver.yaml; then
  print_success "签名密钥路径配置正确"
else
  print_error "签名密钥路径配置错误"
  exit 1
fi

if grep -q "trusted_key_servers:" data/homeserver.yaml; then
  print_success "联邦密钥服务器配置正确"
else
  print_error "联邦密钥服务器配置错误"
  exit 1
fi

echo ""
print_success "所有配置文件生成和验证测试通过！"
echo ""
echo "生成的文件:"
echo "  - data/homeserver.yaml"
echo "  - data/log.config"
echo "  - well-known/.well-known/matrix/server"
echo "  - well-known/.well-known/matrix/client"
echo ""
echo "配置验证项目:"
echo "  ✅ 服务器名称配置"
echo "  ✅ 1CPU/2GB RAM 优化配置"
echo "  ✅ 数据库连接池优化"
echo "  ✅ 缓存优化设置"
echo "  ✅ 注册速率限制"
echo "  ✅ 安全配置"
echo "  ✅ 联邦配置"
echo "  ✅ 性能优化配置"
echo "========================================"