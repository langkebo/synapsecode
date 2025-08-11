#!/bin/bash
# Matrix Server 一键部署脚本
# 支持 Ubuntu 20.04/22.04 LTS
# 包含自定义好友功能

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   log_error "此脚本需要root权限运行"
   exit 1
fi

# 设置变量
PROJECT_DIR="/opt/matrix-server"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER=$SUDO_USER
if [[ -z "$CURRENT_USER" ]]; then
    CURRENT_USER=$(logname)
fi

# 获取用户输入
read -p "请输入您的域名 (例如: example.com): " DOMAIN
read -p "请输入Matrix服务器子域名 (例如: matrix.example.com) [默认: matrix.$DOMAIN]: " MATRIX_DOMAIN
MATRIX_DOMAIN=${MATRIX_DOMAIN:-matrix.$DOMAIN}
read -p "请输入管理员邮箱地址: " ADMIN_EMAIL

# 验证输入
if [[ -z "$DOMAIN" || -z "$MATRIX_DOMAIN" || -z "$ADMIN_EMAIL" ]]; then
    log_error "域名和管理员邮箱不能为空"
    exit 1
fi

log_info "开始部署 Matrix 服务器..."
log_info "主域名: $DOMAIN"
log_info "Matrix服务器: $MATRIX_DOMAIN"
log_info "管理员邮箱: $ADMIN_EMAIL"

# 1. 系统更新
log_info "更新系统..."
apt update && apt upgrade -y

# 2. 安装基础软件
log_info "安装基础软件..."
apt install -y curl wget git jq unzip

# 3. 安装Docker
log_info "安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
    rm get-docker.sh
    usermod -aG docker $CURRENT_USER
fi

# 4. 安装Docker Compose
log_info "安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
fi

# 5. 配置防火墙
log_info "配置防火墙..."
ufw --force enable << EOF
y
EOF
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 81/tcp
ufw --force enable

# 6. 创建项目目录
log_info "创建项目目录..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 创建子目录
mkdir -p {
    well-known/matrix,
    docker/{postgres,nginx,grafana,prometheus,synapse},
    backups
}

# 7. 复制项目文件
log_info "复制项目文件..."
if [[ -d "$SCRIPT_DIR" ]]; then
    cp -r "$SCRIPT_DIR"/* ./
    log_info "从当前目录复制项目文件"
else
    log_error "未找到项目文件，请确保在项目目录中运行此脚本"
    exit 1
fi

# 8. 生成安全密钥
log_info "生成安全密钥..."
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REGISTRATION_SECRET=$(openssl rand -base64 32)
MACAROON_SECRET_KEY=$(openssl rand -base64 32)
FORM_SECRET=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -base64 16)

# 9. 创建环境变量文件
log_info "创建环境变量文件..."
cat > .env << EOF
# Server Configuration
MATRIX_SERVER_NAME=$MATRIX_DOMAIN
MATRIX_DOMAIN=$DOMAIN
ADMIN_EMAIL=$ADMIN_EMAIL

# Security Secrets
POSTGRES_DB=synapse
POSTGRES_USER=synapse
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REGISTRATION_SHARED_SECRET=$REGISTRATION_SECRET
MACAROON_SECRET_KEY=$MACAROON_SECRET_KEY
FORM_SECRET=$FORM_SECRET

# Feature Flags
ENABLE_REGISTRATION=false
REPORT_STATS=no
FRIENDS_ENABLED=true

# Performance Settings
MAX_UPLOAD_SIZE=50M
SYNAPSE_CACHE_FACTOR=1.0
SYNAPSE_EVENT_CACHE_SIZE=10000

# Friends Feature Configuration
MAX_FRIENDS_PER_USER=1000
FRIEND_REQUEST_TIMEOUT=604800
FRIEND_RATE_LIMIT_REQUESTS_PER_HOUR=10
FRIEND_RATE_LIMIT_WINDOW=3600

# Monitoring Configuration
GRAFANA_PASSWORD=$GRAFANA_PASSWORD
ENABLE_MONITORING=false

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Backup Configuration
BACKUP_RETENTION_DAYS=7
BACKUP_COMPRESSION=true
EOF

chmod 600 .env

# 10. 创建well-known配置
log_info "创建well-known配置..."
cat > well-known/matrix/server << EOF
{
  "m.server": "$MATRIX_DOMAIN:443"
}
EOF

cat > well-known/matrix/client << EOF
{
  "m.homeserver": {
    "base_url": "https://matrix.$DOMAIN"
  },
  "m.identity_server": {
    "base_url": "https://vector.im"
  }
}
EOF

# 11. 设置权限
log_info "设置文件权限..."
chown -R $CURRENT_USER:$CURRENT_USER $PROJECT_DIR

# 12. 启动服务
log_info "启动服务..."
cd $PROJECT_DIR

# 切换到普通用户启动Docker
su - $CURRENT_USER -c "cd $PROJECT_DIR && docker-compose up -d postgres redis"

# 等待数据库就绪
log_info "等待数据库就绪..."
sleep 30

# 启动Synapse
log_info "构建并启动Synapse..."
su - $CURRENT_USER -c "cd $PROJECT_DIR && docker-compose up -d --build synapse"

# 等待Synapse启动
log_info "等待Synapse启动..."
sleep 60

# 启动其他服务
log_info "启动其他服务..."
su - $CURRENT_USER -c "cd $PROJECT_DIR && docker-compose up -d nginx-proxy-manager well-known"

# 13. 检查服务状态
log_info "检查服务状态..."
su - $CURRENT_USER -c "cd $PROJECT_DIR && docker-compose ps"

# 14. 创建健康检查脚本
log_info "创建健康检查脚本..."
cat > health-check.sh << 'EOF'
#!/bin/bash
source .env

check_service() {
    if ! curl -f -s $1 > /dev/null; then
        echo "❌ 服务不可用: $1"
        return 1
    fi
    echo "✅ 服务可用: $1"
}

echo "🔍 开始健康检查..."
check_service "https://${MATRIX_SERVER_NAME}/_matrix/client/versions"
check_service "https://${MATRIX_DOMAIN}/.well-known/matrix/server"
echo "✅ 健康检查完成"
EOF

chmod +x health-check.sh
chown $CURRENT_USER:$CURRENT_USER health-check.sh

# 15. 创建备份脚本
log_info "创建备份脚本..."
cat > backup.sh << 'EOF'
#!/bin/bash
source .env
BACKUP_DIR="/opt/matrix-server/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T postgres pg_dump -U ${POSTGRES_USER} -d ${POSTGRES_DB} > $BACKUP_DIR/postgres_$DATE.sql

# 备份配置文件
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    .env \
    docker-compose.yml \
    well-known/ \
    docker/

# 备份数据目录
tar -czf $BACKUP_DIR/data_$DATE.tar.gz \
    synapse_data/ \
    synapse_media/

# 清理旧备份
find $BACKUP_DIR -name "*.sql" -mtime +${BACKUP_RETENTION_DAYS:-7} -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +${BACKUP_RETENTION_DAYS:-7} -delete

echo "备份完成: $BACKUP_DIR"
EOF

chmod +x backup.sh
chown $CURRENT_USER:$CURRENT_USER backup.sh

# 16. 设置定时备份
log_info "设置定时备份..."
(crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/backup.sh") | crontab -

# 17. 创建系统优化脚本
log_info "创建系统优化脚本..."
cat > optimize-system.sh << 'EOF'
#!/bin/bash
# 系统优化脚本

log_info "应用系统优化..."

# 网络优化
cat > /etc/sysctl.d/99-matrix.conf << SYSCTL
# Matrix服务器优化
fs.file-max = 65536
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 120
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.tcp_syncookies = 1
net.ipv4.ip_local_port_range = 1024 65535
SYSCTL

sysctl -p /etc/sysctl.d/99-matrix.conf

# 文件描述符限制
cat > /etc/security/limits.conf << LIMITS
* soft nofile 65536
* hard nofile 65536
* soft nproc 4096
* hard nproc 8192
LIMITS

log_info "系统优化完成"
EOF

chmod +x optimize-system.sh
./optimize-system.sh

# 18. 显示部署完成信息
log_info "部署完成！"
echo ""
echo "==============================================="
echo "🎉 Matrix 服务器部署完成！"
echo "==============================================="
echo ""
echo "📋 接下来的步骤："
echo ""
echo "1. 配置 Nginx Proxy Manager:"
echo "   访问: http://$(curl -s ifconfig.me):81"
echo "   默认登录: admin@example.com / changeme"
echo ""
echo "2. 配置代理主机："
echo "   - Matrix服务器: $MATRIX_DOMAIN -> matrix-synapse:8008"
echo "   - Well-known服务: $DOMAIN -> matrix-well-known:80"
echo ""
echo "3. 申请SSL证书"
echo ""
echo "4. 生成Synapse配置:"
echo "   docker-compose exec synapse python -m synapse.app.homeserver \\"
echo "     --server-name=$MATRIX_DOMAIN --config-path=/data/homeserver.yaml \\"
echo "     --generate-config --report-stats=no"
echo ""
echo "5. 创建管理员用户:"
echo "   docker-compose exec synapse register_new_matrix_user \\"
echo "     -c /data/homeserver.yaml -a http://localhost:8008"
echo ""
echo "🔧 管理命令："
echo "   - 查看状态: docker-compose ps"
echo "   - 查看日志: docker-compose logs -f synapse"
echo "   - 重启服务: docker-compose restart synapse"
echo "   - 健康检查: ./health-check.sh"
echo "   - 备份数据: ./backup.sh"
echo ""
echo "📁 项目目录: $PROJECT_DIR"
echo "👤 项目用户: $CURRENT_USER"
echo ""
echo "⚠️  请妥善保管环境文件 .env 中的安全密钥！"
echo "==============================================="
echo ""
echo "🔗 有用的链接："
echo "   - Element Web: https://app.element.io"
echo "   - Matrix文档: https://matrix.org/docs"
echo "   - Nginx Proxy Manager文档: https://nginxproxymanager.com"
echo ""
echo "🚀 享受您的Matrix服务器吧！"
echo ""

# 询问是否立即配置Nginx Proxy Manager
read -p "是否立即配置Nginx Proxy Manager? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "请在浏览器中访问: http://$(curl -s ifconfig.me):81"
    log_info "使用 admin@example.com / changeme 登录"
    log_info "完成配置后按Enter键继续..."
    read
fi

log_info "部署脚本执行完成！"