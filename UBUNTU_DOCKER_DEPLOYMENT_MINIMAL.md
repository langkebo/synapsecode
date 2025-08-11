# Ubuntu 简化版 Matrix 服务器部署指南

## 系统要求（低配版）

### 硬件要求
- **CPU**: 1核以上
- **内存**: 2GB以上（推荐4GB）
- **存储**: 20GB以上可用空间
- **网络**: 公网IP，带宽5Mbps以上

### 软件要求
- Ubuntu 20.04 LTS 或 22.04 LTS
- Docker 20.10+
- Docker Compose 2.0+
- 域名（用于SSL证书）

### 端口要求
- **80/TCP**: HTTP（用于Let's Encrypt证书申请）
- **443/TCP**: HTTPS（Matrix客户端和联邦）
- **81/TCP**: Nginx Proxy Manager管理界面

## 快速部署

### 1. 系统准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo systemctl enable docker

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# 配置防火墙
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 81/tcp
sudo ufw reload
```

### 2. 创建项目目录

```bash
# 定义项目根目录，您可以根据需要修改此路径
PROJECT_DIR="/opt/matrix-server"

sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

mkdir -p {
    synapse/{data,config,media},
    postgres/data,
    nginx-proxy-manager/{data,letsencrypt},
    well-known/matrix
}

# 创建Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /synapse

# 复制项目代码
COPY . .

# 安装Poetry
RUN pip install poetry

# 配置Poetry
RUN poetry config virtualenvs.create false

# 安装依赖
RUN poetry install --only=main --no-dev --extras all

# 创建数据目录
RUN mkdir -p /data /media /logs

# 设置环境变量
ENV SYNAPSE_CONFIG_PATH=/data/homeserver.yaml

# 暴露端口
EXPOSE 8008

# 启动命令
CMD ["python", "-m", "synapse.app.homeserver"]
EOF
```

### 3. 创建环境变量文件

```bash
# 生成随机密码
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REGISTRATION_SECRET=$(openssl rand -base64 32)
MACAROON_SECRET_KEY=$(openssl rand -base64 32)
FORM_SECRET=$(openssl rand -base64 32)

# 创建环境变量文件
cat > .env << EOF
# 服务器配置
MATRIX_SERVER_NAME=matrix.cjystx.top
MATRIX_DOMAIN=cjystx.top
ADMIN_EMAIL=admin@cjystx.top

# 数据库配置
POSTGRES_DB=synapse
POSTGRES_USER=synapse
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# 安全密钥
REGISTRATION_SHARED_SECRET=${REGISTRATION_SECRET}
MACAROON_SECRET_KEY=${MACAROON_SECRET_KEY}
FORM_SECRET=${FORM_SECRET}

# 功能配置
ENABLE_REGISTRATION=false
MAX_UPLOAD_SIZE=50M
REPORT_STATS=no

# 好友功能配置
FRIENDS_ENABLED=true
MAX_FRIENDS_PER_USER=1000
FRIEND_REQUEST_TIMEOUT=604800
EOF

chmod 600 .env
```

### 4. 创建简化版 Docker Compose 配置

```yaml
cat > docker-compose.yml << EOF


services:
  # Nginx Proxy Manager - 反向代理和SSL管理
  nginx-proxy-manager:
    image: 'jc21/nginx-proxy-manager:latest'
    container_name: npm
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
      - '81:81'
    volumes:
      - ./nginx-proxy-manager/data:/data
      - ./nginx-proxy-manager/letsencrypt:/etc/letsencrypt
    networks:
      - matrix-network

  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    container_name: matrix-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=\${POSTGRES_DB}
      - POSTGRES_USER=\${POSTGRES_USER}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - ./postgres/data:/var/lib/postgresql/data
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  # Synapse Matrix 服务器（使用本地构建）
  synapse:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: matrix-synapse
    restart: unless-stopped
    depends_on:
      - postgres
    environment:
      - SYNAPSE_SERVER_NAME=\${MATRIX_SERVER_NAME}
      - SYNAPSE_REPORT_STATS=\${REPORT_STATS}
      - SYNAPSE_CONFIG_PATH=/data/homeserver.yaml
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=\${POSTGRES_DB}
      - POSTGRES_USER=\${POSTGRES_USER}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
      - REGISTRATION_SHARED_SECRET=\${REGISTRATION_SHARED_SECRET}
      - MACAROON_SECRET_KEY=\${MACAROON_SECRET_KEY}
      - FORM_SECRET=\${FORM_SECRET}
    volumes:
      - ./synapse/data:/data
      - ./synapse/media:/media
      - ./synapse/logs:/logs
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  # Well-known 服务器发现
  well-known:
    image: nginx:alpine
    container_name: matrix-well-known
    restart: unless-stopped
    volumes:
      - ./well-known:/usr/share/nginx/html
      - ./well-known.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - matrix-network

networks:
  matrix-network:
    driver: bridge
EOF
```

### 5. 创建 Well-known 配置

```bash
# 创建 Nginx 配置
cat > well-known.conf << EOF
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/json;
    
    server {
        listen 80;
        server_name _;
        
        location /.well-known/matrix/ {
            root /usr/share/nginx/html;
            add_header Content-Type application/json;
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept, Authorization";
            
            expires 1h;
            add_header Cache-Control "public, immutable";
        }
        
        location / {
            return 404;
        }
    }
}
EOF

# 创建服务器发现文件
cat > well-known/matrix/server << EOF
{
  "m.server": "${MATRIX_SERVER_NAME}:443"
}
EOF

# 创建客户端发现文件
cat > well-known/matrix/client << EOF
{
  "m.homeserver": {
    "base_url": "https://${MATRIX_SERVER_NAME}"
  },
  "m.identity_server": {
    "base_url": "https://vector.im"
  }
}
EOF
```

### 6. 构建并启动服务

#### 从开发环境上传代码（在您的本地机器上执行）

**方法: 使用 FinalShell 或其他SFTP工具拖拽上传**

1. **打开 FinalShell 或其他SFTP客户端**：连接到您的Ubuntu服务器。
2. **导航到目标目录**：在服务器端导航到您在步骤2中创建的项目目录，例如 `/opt/matrix-server`。
3. **拖拽上传项目代码**：将您本地的 `synapsecode` 整个项目文件夹（包含 `synapse` 目录、`Dockerfile`、`docker-compose.yml`、`.env` 等所有文件和子目录）直接拖拽到服务器的 `/opt/matrix-server/` 目录下。

   **重要提示**：确保您拖拽的是整个项目文件夹的内容，而不是仅仅 `synapse` 目录。例如，如果您的本地项目路径是 `d:\project\synapse\synapsecode`，您需要将 `synapsecode` 文件夹内的所有内容（包括 `synapse` 文件夹本身、`Dockerfile`、`docker-compose.yml` 等）上传到服务器的 `/opt/matrix-server/` 目录下。最终服务器上的结构应类似：
   ```
   /opt/matrix-server/
   ├── Dockerfile
   ├── docker-compose.yml
   ├── .env
   ├── synapse/
   ├── postgres/
   ├── nginx-proxy-manager/
   └── well-known/
   ```

   请确保上传后，`Dockerfile`、`docker-compose.yml` 和 `.env` 文件直接位于 `/opt/matrix-server/` 目录下，而不是嵌套在 `synapse` 文件夹内。
```

#### 在服务器上验证文件

```bash
# 在服务器上执行
cd /opt/matrix-server

# 检查关键文件是否存在
ls -la Dockerfile
ls -la docker-compose.yml
ls -la .env
ls -la synapsecode/
ls -la synapsecode/app/homeserver.py
ls -la synapsecode/storage/

# 检查项目结构
tree -L 2
```

#### 构建并启动服务

```bash
# 构建并启动基础服务
docker-compose up -d --build postgres
sleep 20

# 启动 Nginx Proxy Manager
docker-compose up -d nginx-proxy-manager
sleep 15

# 启动 Synapse（这会触发本地构建，可能需要几分钟）
docker-compose up -d --build synapse
sleep 60

# 启动 well-known 服务
docker-compose up -d well-known

# 检查所有服务状态
docker-compose ps
```

#### 如果构建失败，查看详细日志

```bash
# 查看 Synapse 构建日志
docker-compose logs synapse

# 查看 Synapse 运行日志
docker-compose logs -f synapse

# 如果需要重新构建
docker-compose down
docker-compose build --no-cache synapse
docker-compose up -d
```

### 7. 配置 Nginx Proxy Manager

1. **访问管理界面**
   ```bash
   echo "访问: http://$(curl -s ifconfig.me):81"
   ```

2. **默认登录信息**
   - Email: `admin@example.com`
   - Password: `changeme`

3. **配置代理主机**

   **Matrix服务器代理:**
   - Domain Names: `matrix.cjystx.top`
   - Scheme: `http`
   - Forward Hostname/IP: `matrix-synapse`
   - Forward Port: `8008`
   - Enable SSL: 申请Let's Encrypt证书
   - Enable Websocket Support: ✓
   - Block Common Exploits: ✓

   **Well-known服务代理:**
   - Domain Names: `cjystx.top`
   - Scheme: `http`
   - Forward Hostname/IP: `matrix-well-known`
   - Forward Port: `80`
   - Enable SSL: 申请Let's Encrypt证书

4. **SSL证书配置**
   - 在SSL证书选项中选择"申请Let's Encrypt证书"
   - 同意服务条款
   - 使用邮箱: `admin@cjystx.top`
   - 等待证书签发（通常需要1-2分钟）

5. **验证配置**
   - 访问 `https://matrix.cjystx.top` 应该显示JSON响应
   - 访问 `https://cjystx.top/.well-known/matrix/server` 应该显示服务器配置

### 8. 生成 Synapse 配置

```bash
# 生成初始配置
docker-compose exec synapse python -m synapse.app.homeserver \
  --server-name=${MATRIX_SERVER_NAME} \
  --config-path=/data/homeserver.yaml \
  --generate-config \
  --report-stats=${REPORT_STATS}

# 创建优化的配置文件
docker-compose exec synapse tee /data/homeserver.yaml > /dev/null << EOF
# 基础配置
server_name: "${MATRIX_SERVER_NAME}"
pid_file: /data/homeserver.pid
web_client_location: https://app.element.io/
public_baseurl: https://${MATRIX_SERVER_NAME}/

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

# 数据库配置
database:
  name: psycopg2
  args:
    user: \${POSTGRES_USER}
    password: "\${POSTGRES_PASSWORD}"
    database: \${POSTGRES_DB}
    host: postgres
    port: 5432
    cp_min: 2
    cp_max: 5
    keepalives_idle: 10
    keepalives_interval: 5
    keepalives_count: 3

# 事件持久化配置
event_persistence:
  background_updates: true

# 缓存配置
caches:
  global_factor: 1.0

# 日志配置
log_config: "/data/\${MATRIX_SERVER_NAME}.log.config"

# 媒体存储
media_store_path: "/data/media"
max_upload_size: "\${MAX_UPLOAD_SIZE}"
media_retention:
  local_media_lifetime: 30d
  remote_media_lifetime: 30d

# 注册配置
enable_registration: \${ENABLE_REGISTRATION}
registration_shared_secret: "\${REGISTRATION_SHARED_SECRET}"

# 密钥配置
macaroon_secret_key: "\${MACAROON_SECRET_KEY}"
form_secret: "\${FORM_SECRET}"

# 好友功能配置（我们项目的特色功能）
friends:
  enabled: \${FRIENDS_ENABLED}
  max_friends_per_user: \${MAX_FRIENDS_PER_USER}
  friend_request_timeout: \${FRIEND_REQUEST_TIMEOUT}
  allow_cross_domain_friends: true

# 隐私配置
enable_presence: true
allow_device_name_lookup: true

# 联邦配置
federation_domain_whitelist: []

# 统计配置
report_stats: \${REPORT_STATS}

# URL预览配置
url_preview_enabled: false
EOF

# 重启 Synapse 应用配置
docker-compose restart synapse
```

### 9. 创建管理员用户

```bash
# 创建管理员用户
docker-compose exec synapse register_new_matrix_user \
  -c /data/homeserver.yaml \
  -a \
  http://localhost:8008
```

### 10. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 测试 Matrix API
curl -f https://matrix.cjystx.top/_matrix/client/versions

# 测试 well-known 发现
curl -f https://cjystx.top/.well-known/matrix/server
curl -f https://cjystx.top/.well-known/matrix/client

# 检查日志
docker-compose logs --tail=50 synapse

# 测试服务器连接
curl -s https://matrix.cjystx.top/_matrix/federation/v1/version
```

### 9. 创建管理员用户

```bash
# 创建管理员用户
docker-compose exec synapse register_new_matrix_user \
  -c /data/homeserver.yaml \
  -a \
  http://localhost:8008

# 按照提示输入用户名和密码
# 例如：用户名 admin，密码 your-secure-password
```

### 11. 客户端连接测试

1. **使用 Element Web 客户端**
   - 访问 https://app.element.io
   - 选择"使用自定义服务器"
   - 服务器地址：`https://matrix.cjystx.top`
   - 使用刚才创建的管理员账号登录

2. **测试好友功能**
   - 登录后，尝试添加好友
   - 验证好友功能是否正常工作
   - 检查好友请求和列表功能

## 服务管理

### 基本操作

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart synapse

# 查看日志
docker-compose logs -f synapse

# 查看资源使用
docker stats
```

### 备份脚本

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/matrix-server/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T postgres pg_dump -U synapse -d synapse > $BACKUP_DIR/postgres_$DATE.sql

# 备份配置文件
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
  synapse/config/ \
  well-known/ \
  .env \
  docker-compose.yml

# 备份媒体文件
tar -czf $BACKUP_DIR/media_$DATE.tar.gz synapse/media/

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_DIR"
EOF

chmod +x backup.sh
```

### 健康检查

```bash
# 创建健康检查脚本
cat > health-check.sh << 'EOF'
#!/bin/bash

# 检查服务可用性
check_service() {
    if ! curl -f -s $1 > /dev/null; then
        echo "❌ 服务不可用: $1"
        return 1
    fi
    echo "✅ 服务可用: $1"
}

echo "🔍 开始健康检查..."

# 检查服务
check_service "https://${MATRIX_SERVER_NAME}/_matrix/client/versions"
check_service "https://${MATRIX_DOMAIN}/.well-known/matrix/server"

echo "✅ 健康检查完成"
EOF

chmod +x health-check.sh

# 执行健康检查
./health-check.sh
```

## 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   docker-compose ps
   docker-compose logs synapse
   docker-compose logs postgres
   ```

2. **数据库连接问题**
   ```bash
   docker-compose exec postgres pg_isready
   ```

3. **内存不足**
   ```bash
   free -h
   docker stats
   ```

### 重置部署（谨慎操作）

```bash
# 停止服务
docker-compose down

# 备份数据
./backup.sh

# 清理数据（会删除所有数据）
sudo rm -rf postgres/data synapse/data

# 重新初始化
docker-compose up -d
```

## 性能优化建议

### 1. PostgreSQL 优化
```bash
# 创建 PostgreSQL 优化配置
docker-compose exec postgres tee /etc/postgresql/postgresql.conf > /dev/null << EOF
shared_buffers = 128MB
effective_cache_size = 512MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 8MB
default_statistics_target = 100
max_connections = 100
EOF

docker-compose restart postgres
```

### 2. Synapse 优化
```bash
# 更新 Synapse 配置中的缓存设置
docker-compose exec synapse tee -a /data/homeserver.yaml > /dev/null << EOF

# 性能优化配置
caches:
  global_factor: 1.0
  event_cache_size: 5000

stream_writers:
  events:
    writers:
      - type: directory
        path: /data/events
        max_file_size: 512MB
        max_files: 5
EOF

docker-compose restart synapse
```

### 3. 系统优化
```bash
# 创建系统优化配置
sudo tee /etc/sysctl.d/99-synapse.conf << EOF
# 增加文件描述符限制
fs.file-max = 32768

# 网络参数优化
net.core.rmem_max = 8388608
net.core.wmem_max = 8388608
net.ipv4.tcp_rmem = 4096 87380 8388608
net.ipv4.tcp_wmem = 4096 65536 8388608
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 120
EOF

sudo sysctl -p /etc/sysctl.d/99-synapse.conf
```

## 一键部署脚本

### 完整部署脚本

```bash
#!/bin/bash
# 自动部署脚本 - Matrix 服务器
# 适用域名: matrix.cjystx.top

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   log_error "此脚本需要root权限运行"
   exit 1
fi

# 设置变量
PROJECT_DIR="/opt/matrix-server"
DOMAIN="cjystx.top"
MATRIX_DOMAIN="matrix.cjystx.top"
ADMIN_EMAIL="admin@cjystx.top"

log_info "开始部署 Matrix 服务器..."
log_info "域名: $DOMAIN"
log_info "Matrix 服务器: $MATRIX_DOMAIN"
log_info "管理员邮箱: $ADMIN_EMAIL"

# 1. 系统更新
log_info "更新系统..."
apt update && apt upgrade -y

# 2. 安装Docker
log_info "安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
    rm get-docker.sh
fi

# 3. 安装Docker Compose
log_info "安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
fi

# 4. 配置防火墙
log_info "配置防火墙..."
uff enable << EOF
y
EOF
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 81/tcp
ufw --force enable

# 5. 创建项目目录
log_info "创建项目目录..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

mkdir -p {
    synapse/{data,config,media},
    postgres/data,
    nginx-proxy-manager/{data,letsencrypt},
    well-known/matrix
}

# 6. 生成随机密码
log_info "生成安全密钥..."
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REGISTRATION_SECRET=$(openssl rand -base64 32)
MACAROON_SECRET_KEY=$(openssl rand -base64 32)
FORM_SECRET=$(openssl rand -base64 32)

# 7. 创建环境变量文件
log_info "创建环境变量文件..."
cat > .env << EOF
# 服务器配置
MATRIX_SERVER_NAME=$MATRIX_DOMAIN
MATRIX_DOMAIN=$DOMAIN
ADMIN_EMAIL=$ADMIN_EMAIL

# 数据库配置
POSTGRES_DB=synapse
POSTGRES_USER=synapse
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# 安全密钥
REGISTRATION_SHARED_SECRET=$REGISTRATION_SECRET
MACAROON_SECRET_KEY=$MACAROON_SECRET_KEY
FORM_SECRET=$FORM_SECRET

# 功能配置
ENABLE_REGISTRATION=false
MAX_UPLOAD_SIZE=50M
REPORT_STATS=no

# 好友功能配置
FRIENDS_ENABLED=true
MAX_FRIENDS_PER_USER=1000
FRIEND_REQUEST_TIMEOUT=604800
EOF

chmod 600 .env

# 8. 创建Dockerfile
log_info "创建Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /synapse

# 复制项目代码
COPY . .

# 安装Poetry
RUN pip install poetry

# 配置Poetry
RUN poetry config virtualenvs.create false

# 安装依赖
RUN poetry install --only=main --no-dev --extras all

# 创建数据目录
RUN mkdir -p /data /media /logs

# 设置环境变量
ENV SYNAPSE_CONFIG_PATH=/data/homeserver.yaml

# 暴露端口
EXPOSE 8008

# 启动命令
CMD ["python", "-m", "synapse.app.homeserver"]
EOF

# 9. 创建docker-compose.yml
log_info "创建Docker Compose配置..."
cat > docker-compose.yml << EOF
version: '3.8'

services:
  nginx-proxy-manager:
    image: 'jc21/nginx-proxy-manager:latest'
    container_name: npm
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
      - '81:81'
    volumes:
      - ./nginx-proxy-manager/data:/data
      - ./nginx-proxy-manager/letsencrypt:/etc/letsencrypt
    networks:
      - matrix-network

  postgres:
    image: postgres:15-alpine
    container_name: matrix-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=\\${POSTGRES_DB}
      - POSTGRES_USER=\\${POSTGRES_USER}
      - POSTGRES_PASSWORD=\\${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - ./postgres/data:/var/lib/postgresql/data
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  synapse:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: matrix-synapse
    restart: unless-stopped
    depends_on:
      - postgres
    environment:
      - SYNAPSE_SERVER_NAME=\\${MATRIX_SERVER_NAME}
      - SYNAPSE_REPORT_STATS=\\${REPORT_STATS}
      - SYNAPSE_CONFIG_PATH=/data/homeserver.yaml
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=\\${POSTGRES_DB}
      - POSTGRES_USER=\\${POSTGRES_USER}
      - POSTGRES_PASSWORD=\\${POSTGRES_PASSWORD}
      - REGISTRATION_SHARED_SECRET=\\${REGISTRATION_SHARED_SECRET}
      - MACAROON_SECRET_KEY=\\${MACAROON_SECRET_KEY}
      - FORM_SECRET=\\${FORM_SECRET}
    volumes:
      - ./synapse/data:/data
      - ./synapse/media:/media
      - ./synapse/logs:/logs
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  well-known:
    image: nginx:alpine
    container_name: matrix-well-known
    restart: unless-stopped
    volumes:
      - ./well-known:/usr/share/nginx/html
      - ./well-known.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - matrix-network

networks:
  matrix-network:
    driver: bridge
EOF

# 10. 创建well-known配置
log_info "创建well-known配置..."
cat > well-known.conf << EOF
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/json;
    
    server {
        listen 80;
        server_name _;
        
        location /.well-known/matrix/ {
            root /usr/share/nginx/html;
            add_header Content-Type application/json;
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept, Authorization";
            
            expires 1h;
            add_header Cache-Control "public, immutable";
        }
        
        location / {
            return 404;
        }
    }
}
EOF

# 11. 创建well-known文件
cat > well-known/matrix/server << EOF
{
  "m.server": "$MATRIX_DOMAIN:443"
}
EOF

cat > well-known/matrix/client << EOF
{
  "m.homeserver": {
    "base_url": "https://$MATRIX_DOMAIN"
  },
  "m.identity_server": {
    "base_url": "https://vector.im"
  }
}
EOF

# 12. 等待用户上传项目代码
log_warn "请按照上述步骤，使用 FinalShell 或其他SFTP工具将项目代码上传到服务器。"
log_warn "上传完成后，请按Enter键继续..."
read -p ""

# 13. 验证文件
log_info "验证项目文件..."
if [ ! -f "synapse/app/homeserver.py" ]; then
    log_error "项目文件不存在，请确保已正确上传项目代码"
    exit 1
fi

# 14. 启动服务
log_info "启动服务..."
docker-compose up -d --build postgres
sleep 20

docker-compose up -d nginx-proxy-manager
sleep 15

docker-compose up -d --build synapse
sleep 60

docker-compose up -d well-known

# 15. 检查服务状态
log_info "检查服务状态..."
docker-compose ps

# 16. 显示配置信息
log_info "部署完成！"
log_info "请按照以下步骤完成配置："
log_info "1. 访问 Nginx Proxy Manager: http://$(curl -s ifconfig.me):81"
log_info "2. 默认登录: admin@example.com / changeme"
log_info "3. 配置代理主机："
log_info "   - Matrix服务器: $MATRIX_DOMAIN -> matrix-synapse:8008"
log_info "   - Well-known服务: $DOMAIN -> matrix-well-known:80"
log_info "4. 申请SSL证书"
log_info "5. 生成Synapse配置: docker-compose exec synapse python -m synapse.app.homeserver --server-name=$MATRIX_DOMAIN --config-path=/data/homeserver.yaml --generate-config --report-stats=no"
log_info "6. 创建管理员用户: docker-compose exec synapse register_new_matrix_user -c /data/homeserver.yaml -a http://localhost:8008"

log_info "部署脚本执行完成！"
```

### 使用一键部署脚本

```bash
# 1. 下载部署脚本
wget https://your-server.com/deploy-matrix.sh
chmod +x deploy-matrix.sh

# 2. 运行部署脚本
sudo ./deploy-matrix.sh

# 3. 上传项目代码
# 请使用 FinalShell 或其他SFTP工具，将您本地的整个项目文件夹（例如 `d:\project\synapse\synapsecode` 内的所有内容）拖拽上传到服务器的 `/opt/matrix-server/` 目录下。

# 4. 按照脚本提示完成剩余配置
```

## 总结

这个简化版的部署指南专门为低配服务器设计，具有以下特点：

### 主要特性

1. **最低系统要求**: 1核2GB内存，20GB存储
2. **精简架构**: 只包含核心组件（NPM + PostgreSQL + Synapse）
3. **使用项目代码**: 直接使用我们项目的Synapse代码，不是官方镜像
4. **包含好友功能**: 支持我们项目特有的好友管理功能
5. **资源优化**: 限制了各容器的资源使用，适合低配服务器
6. **简化配置**: 移除了复杂的监控和缓存组件

### 项目特色

- **好友管理**: 完整的好友添加、删除、请求功能
- **跨域支持**: 支持跨域好友关系
- **自定义配置**: 基于我们项目的优化配置

### 部署流程

1. **复制代码**: 将项目代码复制到服务器
2. **本地构建**: 使用Dockerfile构建本地镜像
3. **配置启动**: 生成配置文件并启动服务
4. **代理配置**: 通过Nginx Proxy Manager配置SSL

适合个人使用或小型团队的Matrix服务器部署，特别是需要好友功能的场景。

---

**注意事项:**

1. **代码同步**: 每次项目代码更新后，需要重新上传相关文件并重新构建镜像
2. **定期备份**: 备份数据库、配置文件和媒体文件
3. **资源监控**: 监控服务器资源使用情况
4. **性能调优**: 根据实际使用情况调整资源限制
5. **安全更新**: 保持系统和依赖的安全更新
6. **扩展考虑**: 如果用户增多，建议升级服务器配置或添加缓存组件