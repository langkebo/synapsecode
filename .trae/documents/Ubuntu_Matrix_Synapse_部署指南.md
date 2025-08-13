# Ubuntu Matrix Synapse 详细部署指南

## 目录
1. [系统要求和准备工作](#1-系统要求和准备工作)
2. [一键部署方法](#2-一键部署方法)
3. [手动部署方法](#3-手动部署方法)
4. [配置优化说明](#4-配置优化说明)
5. [故障排查](#5-故障排查)
6. [性能监控](#6-性能监控)
7. [安全建议](#7-安全建议)
8. [备份恢复](#8-备份恢复)
9. [升级指南](#9-升级指南)

---

## 1. 系统要求和准备工作

### 1.1 硬件要求
- **最低配置**: 1 vCPU / 2 GB RAM / 40G 硬盘
- **推荐配置**: 2 vCPU / 4 GB RAM / 80G 硬盘
- **网络**: 稳定的互联网连接

### 1.2 系统要求
- Ubuntu 20.04/22.04/24.04 LTS (amd64)
- 已解析的域名 (例如: matrix.example.com)
- 具有 sudo 权限的用户账号
- 开放端口: 80, 443, 8008, 8080

### 1.3 预备工作

#### 1.3.1 更新系统
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim htop
```

#### 1.3.2 配置防火墙
```bash
# 安装 ufw
sudo apt install -y ufw

# 配置基本规则
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8008/tcp
sudo ufw allow 8080/tcp

# 启用防火墙
sudo ufw --force enable
sudo ufw status
```

#### 1.3.3 配置域名解析
确保域名已正确解析到服务器IP:
```bash
# 检查域名解析
nslookup matrix.example.com
dig matrix.example.com
```

#### 1.3.4 设置时区
```bash
sudo timedatectl set-timezone Asia/Shanghai
timedatectl status
```

---

## 2. 一键部署方法

### 2.1 下载项目
```bash
# 切换到 /opt 目录
cd /opt

# 克隆项目 (替换为实际的仓库地址)
sudo git clone <your-repo-url> synapsecode
cd synapsecode

# 设置权限
sudo chown -R $USER:$USER /opt/synapsecode
```

### 2.2 运行一键部署脚本
```bash
# 给脚本执行权限
chmod +x deploy-simple.sh

# 运行部署脚本
sudo ./deploy-simple.sh
```

### 2.3 部署过程说明
脚本会自动完成以下操作:
1. 检查并安装 Docker 和 Docker Compose
2. 生成环境配置文件 (.env)
3. 创建优化的 homeserver.yaml 配置
4. 构建 Matrix Synapse 镜像
5. 启动 PostgreSQL 数据库
6. 启动 Matrix Synapse 服务
7. 配置 well-known 服务

### 2.4 验证部署
```bash
# 检查容器状态
sudo docker compose -f docker-compose.simple.yml ps

# 检查服务健康状态
curl -s http://127.0.0.1:8008/_matrix/client/versions | jq .

# 检查 well-known 配置
curl -s http://127.0.0.1:8080/.well-known/matrix/server | jq .
```

---

## 3. 手动部署方法

### 3.1 安装 Docker
```bash
# 卸载旧版本
sudo apt remove -y docker docker-engine docker.io containerd runc

# 安装依赖
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动并启用 Docker
sudo systemctl enable docker
sudo systemctl start docker

# 将用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
docker compose version
```

### 3.2 创建项目目录结构
```bash
mkdir -p /opt/synapsecode/{data,media,uploads,logs,well-known}
cd /opt/synapsecode
```

### 3.3 创建环境配置文件
```bash
cat > .env << 'EOF'
# Matrix Synapse 配置
SERVER_NAME=matrix.example.com
REPORT_STATS=no
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_USER=synapse
POSTGRES_DB=synapse
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# 性能优化 (1CPU/2GB RAM)
PYTHONOPTIMIZE=1
PYTHONDONTWRITEBYTECODE=1
EOF
```

### 3.4 创建 Dockerfile.simple
```bash
cat > Dockerfile.simple << 'EOF'
# 超简化版 Dockerfile for Matrix Synapse - 使用官方 PyPI 包
FROM python:3.9-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SYNAPSE_CONFIG_PATH=/data/homeserver.yaml

# 安装系统依赖 - 运行时依赖（尽量精简）
RUN apt-get update && apt-get install -y \
    libpq5 \
    libffi8 \
    libssl3 \
    libjpeg62-turbo \
    libxml2 \
    libxslt1.1 \
    zlib1g \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r synapse && useradd -r -g synapse --create-home synapse

# 设置工作目录
WORKDIR /app

# 直接安装官方 Matrix Synapse 包 (不使用本地源码)
RUN pip install --no-cache-dir \
    'matrix-synapse[all]' \
    psycopg2-binary

# 创建必要目录并设置权限
RUN mkdir -p /data /media /uploads /logs && \
    chown -R synapse:synapse /data /media /uploads /logs /app

# 切换到非root用户
USER synapse

# 暴露端口
EXPOSE 8008

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8008/_matrix/client/versions || exit 1

# 默认命令
CMD ["python", "-m", "synapse.app.homeserver", "--config-path", "/data/homeserver.yaml"]
EOF
```

### 3.5 创建 homeserver.yaml 配置文件
```bash
cat > data/homeserver.yaml << 'EOF'
# Matrix Synapse 配置文件 - 针对 1CPU/2GB RAM 优化
server_name: "matrix.example.com"
pid_file: /data/homeserver.pid
web_client_location: https://app.element.io/
public_baseurl: https://matrix.example.com/

# 监听配置
listeners:
  - port: 8008
    tls: false
    type: http
    x_forwarded: true
    bind_addresses: ['0.0.0.0']
    resources:
      - names: [client, federation]
        compress: false

# 数据库配置 - 针对低配服务器优化
database:
  name: psycopg2
  args:
    user: synapse
    password: your_secure_password_here
    database: synapse
    host: postgres
    port: 5432
    cp_min: 1          # 最小连接数 (低配优化)
    cp_max: 2          # 最大连接数 (低配优化)

# 日志配置
log_config: "/data/log.config"

# 媒体存储
media_store_path: "/media"
uploads_path: "/uploads"
max_upload_size: 8M    # 降低上传限制以节省内存

# 缓存配置 - 针对 2GB RAM 优化
caches:
  global_factor: 0.2   # 降低缓存因子以节省内存
  event_cache_size: 500 # 降低事件缓存大小

# 注册配置 - 支持无验证注册，但限制频率
enable_registration: true
enable_registration_without_verification: true
registration_requires_token: false

# 注册速率限制 - 10分钟间隔
rc_registration:
  per_second: 0.0017   # 约每10分钟1次 (1/600)
  burst_count: 1

# 消息速率限制 - 降低以减少CPU负载
rc_message:
  per_second: 0.5      # 降低消息频率
  burst_count: 10      # 降低突发消息数

# 登录速率限制
rc_login:
  address:
    per_second: 0.17
    burst_count: 3
  account:
    per_second: 0.17
    burst_count: 3
  failed_attempts:
    per_second: 0.17
    burst_count: 3

# 禁用不必要的功能以节省资源
enable_metrics: false
enable_media_repo: true
allow_guest_access: false
allow_public_rooms_over_federation: false
allow_public_rooms_without_auth: false

# 安全配置
use_presence: false    # 禁用在线状态以节省资源
suppress_key_server_warning: true

# 统计报告
report_stats: false

# 签名密钥
signing_key_path: "/data/signing.key"
trusted_key_servers:
  - server_name: "matrix.org"
EOF
```

### 3.6 创建日志配置文件
```bash
cat > data/log.config << 'EOF'
version: 1

formatters:
  precise:
    format: '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(request)s - %(message)s'

handlers:
  file:
    class: logging.handlers.TimedRotatingFileHandler
    formatter: precise
    filename: /logs/homeserver.log
    when: midnight
    backupCount: 3
    encoding: utf8

  console:
    class: logging.StreamHandler
    formatter: precise

loggers:
    synapse.storage.SQL:
        level: WARN

root:
    level: WARN
    handlers: [file, console]

disable_existing_loggers: false
EOF
```

### 3.7 创建 well-known 配置
```bash
mkdir -p well-known/.well-known/matrix

cat > well-known/.well-known/matrix/server << 'EOF'
{
  "m.server": "matrix.example.com:443"
}
EOF

cat > well-known/.well-known/matrix/client << 'EOF'
{
  "m.homeserver": {
    "base_url": "https://matrix.example.com"
  },
  "m.identity_server": {
    "base_url": "https://vector.im"
  }
}
EOF
```

### 3.8 创建 docker-compose.simple.yml
```bash
cat > docker-compose.simple.yml << 'EOF'
services:
  postgres:
    image: postgres:13-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: synapse
      POSTGRES_PASSWORD: your_secure_password_here
      POSTGRES_DB: synapse
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
      # 数据库性能优化 (1CPU/2GB RAM)
      POSTGRES_SHARED_BUFFERS: "256MB"
      POSTGRES_EFFECTIVE_CACHE_SIZE: "1GB"
      POSTGRES_WORK_MEM: "4MB"
      POSTGRES_MAINTENANCE_WORK_MEM: "64MB"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U synapse"]
      interval: 60s    # 降低检查频率
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 384M   # 降低内存限制
          cpus: '0.3'    # 降低CPU限制
        reservations:
          memory: 256M
          cpus: '0.2'

  synapse:
    build:
      context: .
      dockerfile: Dockerfile.simple
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "127.0.0.1:8008:8008"
    volumes:
      - ./data:/data
      - ./media:/media
      - ./uploads:/uploads
      - ./logs:/logs
    environment:
      PYTHONOPTIMIZE: 1
      PYTHONDONTWRITEBYTECODE: 1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8008/_matrix/client/versions"]
      interval: 60s    # 降低检查频率
      timeout: 15s
      retries: 3
      start_period: 120s
    deploy:
      resources:
        limits:
          memory: 1280M  # 降低内存限制
          cpus: '0.6'    # 降低CPU限制
        reservations:
          memory: 1024M
          cpus: '0.4'

  well-known:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "0.0.0.0:8080:80"
    volumes:
      - ./well-known:/usr/share/nginx/html:ro
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/.well-known/matrix/server"]
      interval: 60s    # 降低检查频率
      timeout: 5s
      retries: 3
      start_period: 10s
    deploy:
      resources:
        limits:
          memory: 32M
          cpus: '0.05'
        reservations:
          memory: 16M
          cpus: '0.02'

volumes:
  postgres_data:
EOF
```

### 3.9 构建和启动服务
```bash
# 构建镜像
docker compose -f docker-compose.simple.yml build --no-cache

# 启动服务
docker compose -f docker-compose.simple.yml up -d

# 查看状态
docker compose -f docker-compose.simple.yml ps
```

### 3.10 生成签名密钥
```bash
# 生成 Synapse 签名密钥
docker compose -f docker-compose.simple.yml exec synapse \
  python -m synapse.app.homeserver \
  --config-path /data/homeserver.yaml \
  --generate-keys
```

---

## 4. 配置优化说明

### 4.1 针对 1CPU/2GB RAM 的优化

#### 4.1.1 内存优化
- **缓存配置**: `global_factor: 0.2` (降低缓存使用)
- **事件缓存**: `event_cache_size: 500` (减少事件缓存)
- **数据库连接池**: `cp_max: 2` (限制数据库连接数)
- **容器内存限制**: Synapse 1.28GB, PostgreSQL 384MB

#### 4.1.2 CPU优化
- **Python优化**: 启用 `PYTHONOPTIMIZE=1`
- **字节码缓存**: 禁用 `PYTHONDONTWRITEBYTECODE=1`
- **在线状态**: 禁用 `use_presence: false`
- **指标收集**: 禁用 `enable_metrics: false`

#### 4.1.3 网络优化
- **消息速率**: 降低到 `0.5/秒`
- **上传限制**: 降低到 `8MB`
- **健康检查**: 延长间隔到 `60秒`

### 4.2 安全配置

#### 4.2.1 注册限制
```yaml
# 10分钟注册间隔
rc_registration:
  per_second: 0.0017
  burst_count: 1
```

#### 4.2.2 登录保护
```yaml
rc_login:
  address:
    per_second: 0.17
    burst_count: 3
```

### 4.3 存储优化

#### 4.3.1 日志轮转
```yaml
handlers:
  file:
    class: logging.handlers.TimedRotatingFileHandler
    when: midnight
    backupCount: 3
```

#### 4.3.2 媒体清理
```bash
# 定期清理旧媒体文件 (建议每月执行)
docker compose -f docker-compose.simple.yml exec synapse \
  python -m synapse.app.admin_cmd purge_history \
  --config-path /data/homeserver.yaml \
  --before-ts $(date -d '30 days ago' +%s)000
```

---

## 5. 故障排查

### 5.1 常见问题

#### 5.1.1 容器启动失败
```bash
# 查看容器状态
docker compose -f docker-compose.simple.yml ps

# 查看详细日志
docker compose -f docker-compose.simple.yml logs synapse
docker compose -f docker-compose.simple.yml logs postgres

# 检查资源使用
docker stats
```

#### 5.1.2 内存不足
```bash
# 检查系统内存
free -h

# 检查容器内存使用
docker stats --no-stream

# 临时增加交换空间
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 5.1.3 数据库连接问题
```bash
# 测试数据库连接
docker compose -f docker-compose.simple.yml exec postgres \
  psql -U synapse -d synapse -c "SELECT version();"

# 检查数据库日志
docker compose -f docker-compose.simple.yml logs postgres
```

#### 5.1.4 端口冲突
```bash
# 检查端口占用
sudo netstat -tlnp | grep :8008
sudo netstat -tlnp | grep :8080

# 查找占用进程
sudo lsof -i :8008
```

### 5.2 性能问题

#### 5.2.1 响应缓慢
```bash
# 检查系统负载
htop
iostat -x 1

# 检查 Synapse 性能
curl -w "@curl-format.txt" -s -o /dev/null http://127.0.0.1:8008/_matrix/client/versions
```

#### 5.2.2 内存泄漏
```bash
# 监控内存使用趋势
watch -n 5 'docker stats --no-stream | grep synapse'

# 重启服务释放内存
docker compose -f docker-compose.simple.yml restart synapse
```

### 5.3 网络问题

#### 5.3.1 联邦连接失败
```bash
# 测试联邦连接
curl -s "https://federationtester.matrix.org/api/report?server_name=matrix.example.com"

# 检查 well-known 配置
curl -s http://matrix.example.com/.well-known/matrix/server
```

#### 5.3.2 SSL证书问题
```bash
# 检查证书状态
openssl s_client -connect matrix.example.com:443 -servername matrix.example.com

# 检查证书有效期
echo | openssl s_client -connect matrix.example.com:443 2>/dev/null | openssl x509 -noout -dates
```

---

## 6. 性能监控

### 6.1 系统监控

#### 6.1.1 安装监控工具
```bash
# 安装系统监控工具
sudo apt install -y htop iotop nethogs

# 安装 Docker 监控
docker run -d --name=ctop \
  --volume /var/run/docker.sock:/var/run/docker.sock:ro \
  quay.io/vektorlab/ctop:latest
```

#### 6.1.2 创建监控脚本
```bash
cat > monitor.sh << 'EOF'
#!/bin/bash

echo "=== 系统资源使用情况 ==="
echo "CPU使用率:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

echo "内存使用情况:"
free -h

echo "磁盘使用情况:"
df -h /

echo "=== Docker 容器状态 ==="
docker compose -f docker-compose.simple.yml ps

echo "=== 容器资源使用 ==="
docker stats --no-stream

echo "=== Synapse 健康检查 ==="
curl -s http://127.0.0.1:8008/_matrix/client/versions | jq -r '.versions[-1]' || echo "健康检查失败"
EOF

chmod +x monitor.sh
```

### 6.2 日志监控

#### 6.2.1 日志分析脚本
```bash
cat > log_analysis.sh << 'EOF'
#!/bin/bash

LOG_FILE="./logs/homeserver.log"

echo "=== 最近的错误日志 ==="
tail -n 100 $LOG_FILE | grep -i error

echo "=== 最近的警告日志 ==="
tail -n 100 $LOG_FILE | grep -i warn

echo "=== 连接统计 ==="
grep "new connection" $LOG_FILE | tail -n 20

echo "=== 内存使用警告 ==="
grep -i "memory" $LOG_FILE | tail -n 10
EOF

chmod +x log_analysis.sh
```

### 6.3 自动化监控

#### 6.3.1 创建 Cron 任务
```bash
# 编辑 crontab
crontab -e

# 添加以下内容
# 每5分钟检查服务状态
*/5 * * * * /opt/synapsecode/monitor.sh >> /var/log/synapse-monitor.log 2>&1

# 每小时分析日志
0 * * * * /opt/synapsecode/log_analysis.sh >> /var/log/synapse-analysis.log 2>&1

# 每天清理旧日志
0 2 * * * find /opt/synapsecode/logs -name "*.log.*" -mtime +7 -delete
```

---

## 7. 安全建议

### 7.1 系统安全

#### 7.1.1 更新系统
```bash
# 设置自动安全更新
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# 手动更新
sudo apt update && sudo apt upgrade -y
```

#### 7.1.2 SSH 安全
```bash
# 编辑 SSH 配置
sudo vim /etc/ssh/sshd_config

# 建议配置:
# Port 2222                    # 更改默认端口
# PermitRootLogin no           # 禁止 root 登录
# PasswordAuthentication no    # 禁用密码登录
# PubkeyAuthentication yes     # 启用密钥登录

# 重启 SSH 服务
sudo systemctl restart sshd
```

#### 7.1.3 防火墙配置
```bash
# 更新防火墙规则
sudo ufw delete allow ssh
sudo ufw allow 2222/tcp  # 新的 SSH 端口
sudo ufw reload
```

### 7.2 应用安全

#### 7.2.1 定期更新密码
```bash
# 更新数据库密码
NEW_PASSWORD=$(openssl rand -base64 32)
echo "新密码: $NEW_PASSWORD"

# 更新 .env 文件
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PASSWORD/" .env

# 更新 homeserver.yaml
sed -i "s/password: .*/password: $NEW_PASSWORD/" data/homeserver.yaml

# 重启服务
docker compose -f docker-compose.simple.yml restart
```

#### 7.2.2 备份签名密钥
```bash
# 备份重要文件
mkdir -p ~/synapse-backup
cp data/signing.key ~/synapse-backup/
cp data/homeserver.yaml ~/synapse-backup/
cp .env ~/synapse-backup/

# 设置权限
chmod 600 ~/synapse-backup/*
```

### 7.3 网络安全

#### 7.3.1 SSL/TLS 配置
```bash
# 安装 Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# 创建 Nginx 配置
sudo tee /etc/nginx/sites-available/matrix.example.com << 'EOF'
server {
    listen 80;
    server_name matrix.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name matrix.example.com;

    ssl_certificate /etc/letsencrypt/live/matrix.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/matrix.example.com/privkey.pem;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    
    location / {
        proxy_pass http://127.0.0.1:8008;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        
        # 客户端最大请求大小
        client_max_body_size 50M;
    }
    
    location /.well-known/matrix/ {
        proxy_pass http://127.0.0.1:8080/.well-known/matrix/;
        proxy_set_header Host $host;
    }
}
EOF

# 启用站点
sudo ln -s /etc/nginx/sites-available/matrix.example.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 申请 SSL 证书
sudo certbot --nginx -d matrix.example.com
```

---

## 8. 备份恢复

### 8.1 备份策略

#### 8.1.1 创建备份脚本
```bash
cat > backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/synapse-backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="synapse_backup_$DATE"

# 创建备份目录
mkdir -p $BACKUP_DIR/$BACKUP_NAME

echo "开始备份 Matrix Synapse..."

# 停止服务
echo "停止服务..."
docker compose -f docker-compose.simple.yml stop

# 备份数据库
echo "备份数据库..."
docker compose -f docker-compose.simple.yml start postgres
sleep 10
docker compose -f docker-compose.simple.yml exec -T postgres \
  pg_dump -U synapse synapse > $BACKUP_DIR/$BACKUP_NAME/database.sql

# 备份配置文件
echo "备份配置文件..."
cp -r data/ $BACKUP_DIR/$BACKUP_NAME/
cp -r well-known/ $BACKUP_DIR/$BACKUP_NAME/
cp .env $BACKUP_DIR/$BACKUP_NAME/
cp docker-compose.simple.yml $BACKUP_DIR/$BACKUP_NAME/

# 备份媒体文件 (可选，文件较大)
echo "备份媒体文件..."
tar -czf $BACKUP_DIR/$BACKUP_NAME/media.tar.gz media/
tar -czf $BACKUP_DIR/$BACKUP_NAME/uploads.tar.gz uploads/

# 重启服务
echo "重启服务..."
docker compose -f docker-compose.simple.yml up -d

# 压缩备份
echo "压缩备份..."
cd $BACKUP_DIR
tar -czf $BACKUP_NAME.tar.gz $BACKUP_NAME/
rm -rf $BACKUP_NAME/

# 清理旧备份 (保留7天)
find $BACKUP_DIR -name "synapse_backup_*.tar.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
EOF

chmod +x backup.sh
```

#### 8.1.2 自动备份
```bash
# 添加到 crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /opt/synapsecode/backup.sh >> /var/log/synapse-backup.log 2>&1
```

### 8.2 恢复流程

#### 8.2.1 创建恢复脚本
```bash
cat > restore.sh << 'EOF'
#!/bin/bash

if [ -z "$1" ]; then
    echo "用法: $0 <备份文件路径>"
    echo "例如: $0 /opt/synapse-backups/synapse_backup_20231201_020000.tar.gz"
    exit 1
fi

BACKUP_FILE="$1"
RESTORE_DIR="/tmp/synapse_restore"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "开始恢复 Matrix Synapse..."
echo "备份文件: $BACKUP_FILE"

# 停止服务
echo "停止服务..."
docker compose -f docker-compose.simple.yml down

# 解压备份
echo "解压备份文件..."
rm -rf $RESTORE_DIR
mkdir -p $RESTORE_DIR
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

BACKUP_NAME=$(basename $BACKUP_FILE .tar.gz)
BACKUP_PATH="$RESTORE_DIR/$BACKUP_NAME"

# 恢复配置文件
echo "恢复配置文件..."
cp -r $BACKUP_PATH/data/ ./
cp -r $BACKUP_PATH/well-known/ ./
cp $BACKUP_PATH/.env ./
cp $BACKUP_PATH/docker-compose.simple.yml ./

# 恢复媒体文件
echo "恢复媒体文件..."
if [ -f "$BACKUP_PATH/media.tar.gz" ]; then
    tar -xzf $BACKUP_PATH/media.tar.gz
fi
if [ -f "$BACKUP_PATH/uploads.tar.gz" ]; then
    tar -xzf $BACKUP_PATH/uploads.tar.gz
fi

# 启动数据库
echo "启动数据库..."
docker compose -f docker-compose.simple.yml up -d postgres
sleep 15

# 恢复数据库
echo "恢复数据库..."
docker compose -f docker-compose.simple.yml exec -T postgres \
  psql -U synapse -d synapse < $BACKUP_PATH/database.sql

# 启动所有服务
echo "启动所有服务..."
docker compose -f docker-compose.simple.yml up -d

# 清理临时文件
rm -rf $RESTORE_DIR

echo "恢复完成!"
echo "请等待服务启动完成，然后验证功能是否正常。"
EOF

chmod +x restore.sh
```

### 8.3 远程备份

#### 8.3.1 配置远程备份
```bash
# 安装 rclone (用于云存储)
curl https://rclone.org/install.sh | sudo bash

# 配置云存储 (以阿里云OSS为例)
rclone config

# 修改备份脚本，添加远程上传
cat >> backup.sh << 'EOF'

# 上传到云存储
echo "上传到云存储..."
rclone copy $BACKUP_DIR/$BACKUP_NAME.tar.gz aliyun-oss:synapse-backups/

echo "远程备份完成"
EOF
```

---

## 9. 升级指南

### 9.1 升级准备

#### 9.1.1 升级前检查
```bash
# 检查当前版本
docker compose -f docker-compose.simple.yml exec synapse \
  python -c "import synapse; print(synapse.__version__)"

# 检查系统资源
free -h
df -h
docker stats --no-stream

# 创建升级前备份
./backup.sh
```

### 9.2 Synapse 升级

#### 9.2.1 升级 Synapse
```bash
# 停止服务
docker compose -f docker-compose.simple.yml stop synapse

# 重新构建镜像 (会拉取最新版本)
docker compose -f docker-compose.simple.yml build --no-cache synapse

# 启动服务
docker compose -f docker-compose.simple.yml up -d synapse

# 检查日志
docker compose -f docker-compose.simple.yml logs -f synapse
```

#### 9.2.2 数据库升级
```bash
# 如果需要数据库迁移
docker compose -f docker-compose.simple.yml exec synapse \
  python -m synapse.app.homeserver \
  --config-path /data/homeserver.yaml \
  --run-background-updates
```

### 9.3 系统升级

#### 9.3.1 Ubuntu 系统升级
```bash
# 升级到新的 LTS 版本
sudo apt update && sudo apt upgrade -y
sudo apt dist-upgrade -y

# 如果升级到新的主版本
sudo do-release-upgrade
```

#### 9.3.2 Docker 升级
```bash
# 升级 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# 重启 Docker 服务
sudo systemctl restart docker

# 验证升级
docker --version
docker compose version
```

### 9.4 配置升级

#### 9.4.1 服务器配置升级建议

**从 1CPU/2GB 升级到 2CPU/4GB:**
```yaml
# 更新 homeserver.yaml
caches:
  global_factor: 0.5      # 从 0.2 提升到 0.5
  event_cache_size: 2000  # 从 500 提升到 2000

database:
  args:
    cp_max: 5             # 从 2 提升到 5

max_upload_size: 50M      # 从 8M 提升到 50M

rc_message:
  per_second: 2           # 从 0.5 提升到 2
  burst_count: 50         # 从 10 提升到 50
```

**更新 docker-compose.simple.yml:**
```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 1G        # 从 384M 提升到 1G
          cpus: '0.5'       # 从 0.3 提升到 0.5

  synapse:
    deploy:
      resources:
        limits:
          memory: 2.5G      # 从 1.28G 提升到 2.5G
          cpus: '1.2'       # 从 0.6 提升到 1.2
```

#### 9.4.2 启用高级功能
```yaml
# 升级后可以启用的功能
enable_metrics: true      # 启用指标收集
use_presence: true        # 启用在线状态
allow_guest_access: true  # 允许访客访问

# 启用更多缓存
caches:
  sync_response_cache_duration: 2m
  cache_autotuning:
    max_cache_memory_usage: 1024M
```

### 9.5 升级验证

#### 9.5.1 功能验证
```bash
# 检查服务状态
docker compose -f docker-compose.simple.yml ps

# 检查 API 响应
curl -s http://127.0.0.1:8008/_matrix/client/versions | jq .

# 检查联邦功能
curl -s "https://federationtester.matrix.org/api/report?server_name=matrix.example.com"

# 检查用户登录
# (使用 Element 客户端测试登录)
```

#### 9.5.2 性能验证
```bash
# 监控资源使用
watch -n 5 'docker stats --no-stream'

# 检查响应时间
time curl -s http://127.0.0.1:8008/_matrix/client/versions > /dev/null

# 检查内存使用趋势
for i in {1..10}; do
  echo "$(date): $(docker stats --no-stream | grep synapse | awk '{print $4}')"
  sleep 60
done
```

---

## 10. 附录

### 10.1 常用命令

```bash
# 服务管理
docker compose -f docker-compose.simple.yml up -d      # 启动服务
docker compose -f docker-compose.simple.yml down       # 停止服务
docker compose -f docker-compose.simple.yml restart    # 重启服务
docker compose -f docker-compose.simple.yml ps         # 查看状态

# 日志查看
docker compose -f docker-compose.simple.yml logs -f synapse    # 查看 Synapse 日志
docker compose -f docker-compose.simple.yml logs -f postgres   # 查看数据库日志
tail -f logs/homeserver.log                                     # 查看文件日志

# 用户管理
docker compose -f docker-compose.simple.yml exec synapse \
  register_new_matrix_user -c /data/homeserver.yaml -a http://localhost:8008

# 数据库操作
docker compose -f docker-compose.simple.yml exec postgres \
  psql -U synapse -d synapse

# 清理操作
docker system prune -f                    # 清理未使用的 Docker 资源
docker volume prune -f                    # 清理未使用的卷
find logs/ -name "*.log.*" -mtime +7 -delete  # 清理旧日志
```

### 10.2 配置文件模板

#### 10.2.1 环境变量模板 (.env)
```bash
# Matrix Synapse 基础配置
SERVER_NAME=matrix.example.com
REPORT_STATS=no

# 数据库配置
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_USER=synapse
POSTGRES_DB=synapse
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# 性能优化
PYTHONOPTIMIZE=1
PYTHONDONTWRITEBYTECODE=1

# 可选配置
# SYNAPSE_LOG_LEVEL=WARNING
# SYNAPSE_CACHE_FACTOR=0.2
```

### 10.3 故障排查清单

- [ ] 检查系统资源 (CPU, 内存, 磁盘)
- [ ] 检查 Docker 服务状态
- [ ] 检查容器日志
- [ ] 检查网络连接
- [ ] 检查防火墙规则
- [ ] 检查域名解析
- [ ] 检查 SSL 证书
- [ ] 检查数据库连接
- [ ] 检查配置文件语法
- [ ] 检查文件权限

### 10.4 联系支持

如果遇到无法解决的问题，请提供以下信息:

1. 系统信息: `uname -a`
2. Docker 版本: `docker --version`
3. 容器状态: `docker compose -f docker-compose.simple.yml ps`
4. 错误日志: 最近的错误信息
5. 配置文件: homeserver.yaml 的相关部分
6. 资源使用: `free -h` 和 `df -h` 的输出

---

**部署完成后，请记得:**
1. 定期备份重要数据
2. 监控系统资源使用
3. 及时更新系统和应用
4. 定期检查安全配置
5. 关注 Matrix Synapse 官方更新

祝您部署顺利！