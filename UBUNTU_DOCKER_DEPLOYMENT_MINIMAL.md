# Ubuntu 简化版 Matrix 服务器部署指南

## 系统要求（极简版）

### 最低硬件要求
- **CPU**: 1核 vCPU
- **内存**: 1.5GB RAM（最低要求）
- **存储**: 15GB SSD空间
- **网络**: 公网IP，带宽2Mbps以上

### 推荐硬件要求
- **CPU**: 2核 vCPU
- **内存**: 2GB RAM
- **存储**: 25GB SSD空间
- **网络**: 公网IP，带宽5Mbps以上

### 软件要求
- Ubuntu 20.04 LTS 或 22.04 LTS (64位)
- Docker 20.10+
- Docker Compose 2.0+
- 域名（用于SSL证书，可选但推荐）

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
# 定义项目根目录
PROJECT_DIR="/opt/matrix-server"

sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# 创建必要的目录结构
mkdir -p {
    synapse/{data,media,logs},
    postgres/data,
    well-known/matrix
}

# 创建轻量化Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

# 安装最小必需的系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置工作目录
WORKDIR /synapse

# 安装Poetry
RUN pip install poetry==1.6.1

# 配置Poetry
RUN poetry config virtualenvs.create false

# 复制依赖文件
COPY pyproject.toml poetry.lock* ./

# 安装生产依赖（跳过开发依赖）
RUN poetry install --only=main --no-dev --no-interaction --no-ansi

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /data /media /logs

# 设置环境变量以减少内存使用
ENV SYNAPSE_CONFIG_PATH=/data/homeserver.yaml \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=1

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

# 创建环境变量文件（针对低配服务器优化）
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
MAX_UPLOAD_SIZE=10M
REPORT_STATS=no

# 好友功能配置
FRIENDS_ENABLED=true
MAX_FRIENDS_PER_USER=200
FRIEND_REQUEST_TIMEOUT=604800

# 性能优化配置（低配服务器）
SYNAPSE_CACHE_FACTOR=0.5
SYNAPSE_EVENT_CACHE_SIZE=2000
MAX_UPLOAD_SIZE=10M
EOF

chmod 600 .env
```

### 4. 创建轻量化 Docker Compose 配置

```yaml
cat > docker-compose.yml << EOF
version: '3.8'

services:
  # PostgreSQL 数据库（轻量化配置）
  postgres:
    image: postgres:15-alpine
    container_name: matrix-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=\${POSTGRES_DB}
      - POSTGRES_USER=\${POSTGRES_USER}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
      - POSTGRES_HOST_AUTH_METHOD=trust
    volumes:
      - ./postgres/data:/var/lib/postgresql/data
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.3'
        reservations:
          memory: 256M
          cpus: '0.1'

  # Synapse Matrix 服务器（低配优化）
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
      - SYNAPSE_CACHE_FACTOR=\${SYNAPSE_CACHE_FACTOR}
      - SYNAPSE_EVENT_CACHE_SIZE=\${SYNAPSE_EVENT_CACHE_SIZE}
    volumes:
      - ./synapse/data:/data
      - ./synapse/media:/media
      - ./synapse/logs:/logs
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.8'
        reservations:
          memory: 512M
          cpus: '0.3'

  # Well-known 服务器发现（轻量化）
  well-known:
    image: nginx:alpine
    container_name: matrix-well-known
    restart: unless-stopped
    volumes:
      - ./well-known:/usr/share/nginx/html
      - ./well-known.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'

networks:
  matrix-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
EOF
```

### 5. 创建 Nginx 反向代理配置（简化版）

```bash
# 创建 Nginx 反向代理配置
cat > nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # 基本配置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Matrix 服务器代理
    server {
        listen 80;
        server_name ${MATRIX_SERVER_NAME};
        
        # 重定向到 HTTPS（如果有SSL证书）
        # return 301 https://\$server_name\$request_uri;
        
        # 或者直接代理到 HTTP（开发/测试环境）
        location / {
            proxy_pass http://synapse:8008;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # WebSocket 支持
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
    
    # Well-known 服务器发现
    server {
        listen 80;
        server_name ${MATRIX_DOMAIN};
        
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

# 创建 Nginx 服务配置
cat > docker-compose.override.yml << EOF
version: '3.8'

services:
  # 添加 Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: matrix-nginx
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./well-known:/usr/share/nginx/html:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - synapse
      - well-known
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.2'
EOF

### 6. 创建 Well-known 配置

```bash
# 创建 well-known 配置
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

### 7. 构建并启动服务（简化版）

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

#### 构建并启动服务（简化版）

```bash
# 使用合并配置启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d --build

# 等待服务启动
sleep 60

# 检查服务状态
docker-compose -f docker-compose.yml -f docker-compose.override.yml ps
```

#### 如果构建失败，查看详细日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.yml -f docker-compose.override.yml logs

# 查看特定服务日志
docker-compose -f docker-compose.yml -f docker-compose.override.yml logs -f synapse
docker-compose -f docker-compose.yml -f docker-compose.override.yml logs -f postgres

# 如果需要重新构建
docker-compose -f docker-compose.yml -f docker-compose.override.yml down
docker-compose -f docker-compose.yml -f docker-compose.override.yml build --no-cache
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

### 8. 配置 SSL 证书（可选）

如果需要 HTTPS 支持，可以使用 Let's Encrypt 证书：

```bash
# 安装 certbot
sudo apt install certbot -y

# 申请证书
sudo certbot certonly --standalone -d ${MATRIX_SERVER_NAME} -d ${MATRIX_DOMAIN}

# 创建 SSL 目录
mkdir -p ./ssl

# 复制证书
sudo cp /etc/letsencrypt/live/${MATRIX_SERVER_NAME}/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/${MATRIX_SERVER_NAME}/privkey.pem ./ssl/
sudo chown -R $USER:$USER ./ssl

# 更新 Nginx 配置以支持 HTTPS
cat > nginx-ssl.conf << EOF
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # 基本配置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # HTTPS 服务器
    server {
        listen 443 ssl http2;
        server_name ${MATRIX_SERVER_NAME};
        
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        
        location / {
            proxy_pass http://synapse:8008;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
    
    # HTTP 重定向到 HTTPS
    server {
        listen 80;
        server_name ${MATRIX_SERVER_NAME};
        return 301 https://\$server_name\$request_uri;
    }
    
    # Well-known 服务器发现
    server {
        listen 80;
        server_name ${MATRIX_DOMAIN};
        
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

# 重启 Nginx 服务
docker-compose -f docker-compose.yml -f docker-compose.override.yml restart nginx
```

### 9. 生成 Synapse 配置

```bash
# 生成初始配置
docker-compose exec synapse python -m synapse.app.homeserver \
  --server-name=${MATRIX_SERVER_NAME} \
  --config-path=/data/homeserver.yaml \
  --generate-config \
  --report-stats=${REPORT_STATS}

# 创建低配优化配置文件
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

# 数据库配置（低配优化）
database:
  name: psycopg2
  args:
    user: \${POSTGRES_USER}
    password: "\${POSTGRES_PASSWORD}"
    database: \${POSTGRES_DB}
    host: postgres
    port: 5432
    cp_min: 1
    cp_max: 3
    keepalives_idle: 10
    keepalives_interval: 5
    keepalives_count: 3

# 事件持久化配置（低配优化）
event_persistence:
  background_updates: true
  persistence_targets: 
    - target: "database"
      delay_before: 500

# 缓存配置（低配优化）
caches:
  global_factor: 0.5
  event_cache_size: 2000
  cache_factor: 0.5

# 日志配置（简化）
log_config: "/data/\${MATRIX_SERVER_NAME}.log.config"

# 媒体存储（低配优化）
media_store_path: "/data/media"
max_upload_size: "\${MAX_UPLOAD_SIZE}"
media_retention:
  local_media_lifetime: 7d
  remote_media_lifetime: 3d

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

# 隐私配置（简化以减少资源使用）
enable_presence: true
allow_device_name_lookup: false

# 联邦配置
federation_domain_whitelist: []

# 统计配置
report_stats: \${REPORT_STATS}

# URL预览配置
url_preview_enabled: false

# 性能优化配置
stream_writers:
  events:
    writers:
      - type: directory
        path: /data/events
        max_file_size: 256MB
        max_files: 3

# 禁用非必要功能
enable_metrics: false
enable_registration_captcha: false
enable_3pid_lookup: false
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
docker-compose -f docker-compose.yml -f docker-compose.override.yml ps

# 测试 Matrix API（HTTP）
curl -f http://$(curl -s ifconfig.me)/_matrix/client/versions

# 测试 well-known 发现
curl -f http://${MATRIX_DOMAIN}/.well-known/matrix/server
curl -f http://${MATRIX_DOMAIN}/.well-known/matrix/client

# 检查日志
docker-compose -f docker-compose.yml -f docker-compose.override.yml logs --tail=50 synapse

# 测试服务器连接
curl -s http://$(curl -s ifconfig.me)/_matrix/federation/v1/version
```

### 11. 创建管理员用户

```bash
# 创建管理员用户
docker-compose exec synapse register_new_matrix_user \
  -c /data/homeserver.yaml \
  -a \
  http://localhost:8008

# 按照提示输入用户名和密码
# 例如：用户名 admin，密码 your-secure-password
```

### 12. 客户端连接测试

1. **使用 Element Web 客户端**
   - 访问 https://app.element.io
   - 选择"使用自定义服务器"
   - 服务器地址：`http://$(curl -s ifconfig.me)` (HTTP) 或 `https://${MATRIX_SERVER_NAME}` (HTTPS)
   - 使用刚才创建的管理员账号登录

2. **测试好友功能**
   - 登录后，尝试添加好友
   - 验证好友功能是否正常工作
   - 检查好友请求和列表功能

## 服务管理

### 基本操作（简化版）

```bash
# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.override.yml down

# 重启服务
docker-compose -f docker-compose.yml -f docker-compose.override.yml restart synapse

# 查看日志
docker-compose -f docker-compose.yml -f docker-compose.override.yml logs -f synapse

# 查看资源使用
docker stats

# 查看实时资源使用
docker stats --no-stream
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
docker-compose -f docker-compose.yml -f docker-compose.override.yml exec -T postgres pg_dump -U ${POSTGRES_USER} -d ${POSTGRES_DB} > $BACKUP_DIR/postgres_$DATE.sql

# 备份配置文件
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
  .env \
  docker-compose.yml \
  docker-compose.override.yml \
  nginx.conf \
  well-known/

# 备份数据目录
tar -czf $BACKUP_DIR/data_$DATE.tar.gz \
  synapse/data/ \
  synapse/media/

# 清理旧备份（保留5天，节省空间）
find $BACKUP_DIR -name "*.sql" -mtime +5 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +5 -delete

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

# 检查服务（HTTP）
check_service "http://$(curl -s ifconfig.me)/_matrix/client/versions"
check_service "http://${MATRIX_DOMAIN}/.well-known/matrix/server"

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
   docker-compose -f docker-compose.yml -f docker-compose.override.yml ps
   docker-compose -f docker-compose.yml -f docker-compose.override.yml logs synapse
   docker-compose -f docker-compose.yml -f docker-compose.override.yml logs postgres
   docker-compose -f docker-compose.yml -f docker-compose.override.yml logs nginx
   ```

2. **数据库连接问题**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.override.yml exec postgres pg_isready
   ```

3. **内存不足**
   ```bash
   free -h
   docker stats --no-stream
   # 如果内存不足，可以调整docker-compose.override.yml中的资源限制
   ```

4. **端口占用问题**
   ```bash
   # 检查端口占用
   sudo netstat -tulpn | grep :80
   sudo netstat -tulpn | grep :443
   # 停止占用端口的服务
   sudo systemctl stop nginx
   sudo systemctl stop apache2
   ```

### 重置部署（谨慎操作）

```bash
# 停止服务
docker-compose -f docker-compose.yml -f docker-compose.override.yml down

# 备份数据
./backup.sh

# 清理数据（会删除所有数据，谨慎操作）
sudo rm -rf postgres/data synapse/data synapse/media

# 清理Docker镜像和容器
docker system prune -a -f

# 重新初始化
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
```

## 性能优化建议（低配服务器专用）

### 1. 系统级优化
```bash
# 创建系统优化配置
sudo tee /etc/sysctl.d/99-matrix-minimal.conf << EOF
# 低配服务器优化配置
fs.file-max = 16384
net.core.rmem_max = 4194304
net.core.wmem_max = 4194304
net.ipv4.tcp_rmem = 4096 87380 4194304
net.ipv4.tcp_wmem = 4096 32768 4194304
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 60
net.ipv4.ip_local_port_range = 1024 32768
vm.swappiness = 10
vm.vfs_cache_pressure = 50
EOF

sudo sysctl -p /etc/sysctl.d/99-matrix-minimal.conf
```

### 2. Docker 资源限制优化
```bash
# 创建优化后的 docker-compose.override.yml
cat > docker-compose.override.optimized.yml << EOF
version: '3.8'

services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 384M
          cpus: '0.2'
        reservations:
          memory: 128M
          cpus: '0.1'
    environment:
      - POSTGRES_SHARED_BUFFERS=64MB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=256MB
      - POSTGRES_MAINTENANCE_WORK_MEM=32MB

  synapse:
    deploy:
      resources:
        limits:
          memory: 768M
          cpus: '0.6'
        reservations:
          memory: 384M
          cpus: '0.2'
    environment:
      - SYNAPSE_CACHE_FACTOR=0.3
      - SYNAPSE_EVENT_CACHE_SIZE=1000

  nginx:
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'

  well-known:
    deploy:
      resources:
        limits:
          memory: 32M
          cpus: '0.05'
EOF
```

### 3. PostgreSQL 配置优化
```bash
# 创建 PostgreSQL 优化配置
cat > postgres/postgresql.conf << EOF
# 低配服务器 PostgreSQL 配置
shared_buffers = 64MB
effective_cache_size = 256MB
maintenance_work_mem = 32MB
checkpoint_completion_target = 0.9
wal_buffers = 4MB
default_statistics_target = 50
max_connections = 50
work_mem = 2MB
random_page_cost = 2.0
effective_io_concurrency = 1
EOF

# 重启 PostgreSQL
docker-compose -f docker-compose.yml -f docker-compose.override.yml restart postgres
```

### 4. Synapse 配置优化
```bash
# 创建更激进的 Synapse 优化配置
docker-compose -f docker-compose.yml -f docker-compose.override.yml exec synapse tee -a /data/homeserver.yaml > /dev/null << EOF

# 极简优化配置
caches:
  global_factor: 0.3
  event_cache_size: 1000
  cache_factor: 0.3

database:
  args:
    cp_min: 1
    cp_max: 2

stream_writers:
  events:
    writers:
      - type: directory
        path: /data/events
        max_file_size: 128MB
        max_files: 2

# 禁用更多功能以节省资源
enable_metrics: false
enable_registration_captcha: false
enable_3pid_lookup: false
suppress_key_server: true
EOF

# 重启 Synapse
docker-compose -f docker-compose.yml -f docker-compose.override.yml restart synapse
```

### 5. 监控和日志优化
```bash
# 创建监控脚本
cat > monitor.sh << 'EOF'
#!/bin/bash
# 简单的资源监控脚本

while true; do
    echo "=== $(date) ==="
    echo "内存使用:"
    free -h
    echo "Docker 容器状态:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    echo "Synapse 日志最后5行:"
    docker-compose logs --tail=5 synapse
    echo "=================="
    sleep 300
done
EOF

chmod +x monitor.sh

# 运行监控（在另一个终端）
./monitor.sh
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

## 简化版一键部署脚本

### 极简部署脚本（适合1.5GB内存服务器）

```bash
#!/bin/bash
# 简化版 Matrix 服务器一键部署脚本
# 专为低配服务器设计（1.5GB内存+）

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

log_info "开始部署简化版 Matrix 服务器..."
log_info "域名: $DOMAIN"
log_info "Matrix 服务器: $MATRIX_DOMAIN"
log_info "管理员邮箱: $ADMIN_EMAIL"

# 1. 系统更新和优化
log_info "更新系统并优化..."
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
ufw --force enable << EOF
y
EOF
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 5. 创建项目目录
log_info "创建项目目录..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

mkdir -p {
    synapse/{data,media,logs},
    postgres/data,
    well-known/matrix,
    ssl
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
MAX_UPLOAD_SIZE=10M
REPORT_STATS=no

# 好友功能配置
FRIENDS_ENABLED=true
MAX_FRIENDS_PER_USER=200
FRIEND_REQUEST_TIMEOUT=604800

# 性能优化配置（极简）
SYNAPSE_CACHE_FACTOR=0.3
SYNAPSE_EVENT_CACHE_SIZE=1000
EOF

chmod 600 .env

# 8. 创建 Dockerfile
log_info "创建 Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

# 安装最小必需的系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置工作目录
WORKDIR /synapse

# 安装Poetry
RUN pip install poetry==1.6.1

# 配置Poetry
RUN poetry config virtualenvs.create false

# 复制依赖文件
COPY pyproject.toml poetry.lock* ./

# 安装生产依赖
RUN poetry install --only=main --no-dev --no-interaction --no-ansi

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /data /media /logs

# 设置环境变量
ENV SYNAPSE_CONFIG_PATH=/data/homeserver.yaml \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=1

# 暴露端口
EXPOSE 8008

# 启动命令
CMD ["python", "-m", "synapse.app.homeserver"]
EOF

# 9. 创建 docker-compose.yml
log_info "创建 Docker Compose 配置..."
cat > docker-compose.yml << EOF
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: matrix-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=\${POSTGRES_DB}
      - POSTGRES_USER=\${POSTGRES_USER}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
      - POSTGRES_HOST_AUTH_METHOD=trust
    volumes:
      - ./postgres/data:/var/lib/postgresql/data
      - ./postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 384M
          cpus: '0.2'

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
      - SYNAPSE_CACHE_FACTOR=\${SYNAPSE_CACHE_FACTOR}
      - SYNAPSE_EVENT_CACHE_SIZE=\${SYNAPSE_EVENT_CACHE_SIZE}
    volumes:
      - ./synapse/data:/data
      - ./synapse/media:/media
      - ./synapse/logs:/logs
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 768M
          cpus: '0.6'

  well-known:
    image: nginx:alpine
    container_name: matrix-well-known
    restart: unless-stopped
    volumes:
      - ./well-known:/usr/share/nginx/html
      - ./well-known.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - matrix-network
    deploy:
      resources:
        limits:
          memory: 32M
          cpus: '0.05'

networks:
  matrix-network:
    driver: bridge
EOF

# 10. 创建 well-known 配置
log_info "创建 well-known 配置..."
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

# 11. 创建 PostgreSQL 配置
log_info "创建 PostgreSQL 配置..."
cat > postgres/postgresql.conf << EOF
# 低配服务器 PostgreSQL 配置
shared_buffers = 64MB
effective_cache_size = 256MB
maintenance_work_mem = 32MB
checkpoint_completion_target = 0.9
wal_buffers = 4MB
default_statistics_target = 50
max_connections = 50
work_mem = 2MB
random_page_cost = 2.0
effective_io_concurrency = 1
EOF

# 12. 系统优化
log_info "应用系统优化..."
cat > /etc/sysctl.d/99-matrix-minimal.conf << EOF
# 低配服务器优化配置
fs.file-max = 16384
net.core.rmem_max = 4194304
net.core.wmem_max = 4194304
net.ipv4.tcp_rmem = 4096 87380 4194304
net.ipv4.tcp_wmem = 4096 32768 4194304
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 60
net.ipv4.ip_local_port_range = 1024 32768
vm.swappiness = 10
vm.vfs_cache_pressure = 50
EOF

sysctl -p /etc/sysctl.d/99-matrix-minimal.conf

# 13. 等待用户上传项目代码
log_warn "请使用 SFTP 工具将项目代码上传到 $PROJECT_DIR"
log_warn "上传完成后，请按 Enter 键继续..."
read -p ""

# 14. 验证项目文件
log_info "验证项目文件..."
if [ ! -f "synapse/app/homeserver.py" ]; then
    log_error "项目文件不存在，请确保已正确上传项目代码"
    exit 1
fi

# 15. 启动服务
log_info "启动服务..."
docker-compose up -d --build

# 等待服务启动
log_info "等待服务启动..."
sleep 60

# 16. 检查服务状态
log_info "检查服务状态..."
docker-compose ps

# 17. 生成 Synapse 配置
log_info "生成 Synapse 配置..."
docker-compose exec synapse python -m synapse.app.homeserver \
  --server-name=$MATRIX_DOMAIN \
  --config-path=/data/homeserver.yaml \
  --generate-config \
  --report-stats=no

# 18. 创建优化配置
log_info "创建优化配置..."
docker-compose exec synapse tee /data/homeserver.yaml > /dev/null << EOF
server_name: "$MATRIX_DOMAIN"
pid_file: /data/homeserver.pid
web_client_location: https://app.element.io/
public_baseurl: https://$MATRIX_DOMAIN/

listeners:
  - port: 8008
    tls: false
    type: http
    x_forwarded: true
    bind_addresses: ['0.0.0.0']
    resources:
      - names: [client, federation]
        compress: false

database:
  name: psycopg2
  args:
    user: \${POSTGRES_USER}
    password: "\${POSTGRES_PASSWORD}"
    database: \${POSTGRES_DB}
    host: postgres
    port: 5432
    cp_min: 1
    cp_max: 2

event_persistence:
  background_updates: true
  persistence_targets: 
    - target: "database"
      delay_before: 500

caches:
  global_factor: 0.3
  event_cache_size: 1000

log_config: "/data/\${MATRIX_SERVER_NAME}.log.config"

media_store_path: "/data/media"
max_upload_size: "10M"
media_retention:
  local_media_lifetime: 7d
  remote_media_lifetime: 3d

enable_registration: \${ENABLE_REGISTRATION}
registration_shared_secret: "\${REGISTRATION_SHARED_SECRET}"

macaroon_secret_key: "\${MACAROON_SECRET_KEY}"
form_secret: "\${FORM_SECRET}"

friends:
  enabled: \${FRIENDS_ENABLED}
  max_friends_per_user: \${MAX_FRIENDS_PER_USER}
  friend_request_timeout: \${FRIEND_REQUEST_TIMEOUT}
  allow_cross_domain_friends: true

enable_presence: true
allow_device_name_lookup: false

federation_domain_whitelist: []
report_stats: \${REPORT_STATS}
url_preview_enabled: false

stream_writers:
  events:
    writers:
      - type: directory
        path: /data/events
        max_file_size: 128MB
        max_files: 2

enable_metrics: false
enable_registration_captcha: false
enable_3pid_lookup: false
suppress_key_server: true
EOF

# 19. 重启 Synapse
log_info "重启 Synapse..."
docker-compose restart synapse

# 20. 显示完成信息
log_info "部署完成！"
echo ""
echo "==============================================="
echo "🎉 简化版 Matrix 服务器部署完成！"
echo "==============================================="
echo ""
echo "📋 接下来的步骤："
echo ""
echo "1. 访问服务器: http://$(curl -s ifconfig.me)"
echo "2. 创建管理员用户:"
echo "   docker-compose exec synapse register_new_matrix_user -c /data/homeserver.yaml -a http://localhost:8008"
echo ""
echo "3. 使用 Element Web 客户端连接:"
echo "   - 访问: https://app.element.io"
echo "   - 服务器地址: http://$(curl -s ifconfig.me)"
echo "   - 使用刚创建的管理员账号登录"
echo ""
echo "🔧 管理命令："
echo "   - 查看状态: docker-compose ps"
echo "   - 查看日志: docker-compose logs -f synapse"
echo "   - 重启服务: docker-compose restart synapse"
echo ""
echo "📁 项目目录: $PROJECT_DIR"
echo ""
echo "⚠️  注意事项："
echo "   - 服务器配置为极简模式，适合1-2个用户"
echo "   - 定期检查内存使用情况"
echo "   - 建议定期备份数据"
echo "==============================================="
echo ""

log_info "部署脚本执行完成！"
```

## 总结

这个优化版本的简化部署指南专门为低配服务器设计，具有以下特点：

### 🎯 主要优化特性

1. **极低系统要求**: 1.5GB内存+1核CPU，15GB存储
2. **精简架构**: 移除了Nginx Proxy Manager，使用轻量级Nginx
3. **资源优化**: 严格限制各组件资源使用
4. **性能调优**: 针对低配服务器的专门优化配置
5. **一键部署**: 提供完整的自动化部署脚本

### 📊 资源使用预估

- **PostgreSQL**: 384MB内存，0.2核CPU
- **Synapse**: 768MB内存，0.6核CPU  
- **Nginx**: 128MB内存，0.2核CPU
- **Well-known**: 32MB内存，0.05核CPU
- **总计**: 约1.3GB内存，1核CPU

### 🚀 部署方式

1. **手动部署**: 按照文档步骤逐步部署
2. **一键部署**: 使用提供的简化版一键部署脚本
3. **分阶段部署**: 先部署基础版本，后续根据需要添加功能

### 📝 项目特色

- **好友功能**: 完整的好友管理系统
- **跨域支持**: 支持跨域好友关系
- **低配优化**: 专门针对资源受限环境优化
- **易于维护**: 简化的架构和配置

### 🎯 适用场景

- **个人服务器**: 1-2个用户的小型Matrix服务器
- **测试环境**: 开发和测试用途
- **学习用途**: 学习Matrix协议和Synapse
- **小型团队**: 5人以下的小团队

---

**⚠️ 重要提醒:**

1. **性能限制**: 此配置为极简模式，仅适合少量用户
2. **扩展建议**: 用户增多时建议升级服务器配置
3. **定期监控**: 建议定期监控资源使用情况
4. **备份重要**: 定期备份数据和配置文件
5. **安全更新**: 保持系统和依赖的安全更新

这个优化版本能够在1.5GB内存的服务器上稳定运行，为低配环境提供了一个可用的Matrix服务器解决方案。