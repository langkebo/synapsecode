# Ubuntu 部署指南（精简版）

本指南基于精简后的项目结构，提供在 Ubuntu 20.04/22.04/24.04 上一键部署 Matrix Synapse 的标准流程。

## 1. 系统要求
- Ubuntu 20.04/22.04/24.04（amd64）
- 2 vCPU / 4 GB RAM（最低建议）
- 已解析的域名，例如：matrix.example.com
- 一个具有 sudo 权限的用户

## 2. 准备依赖
```bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release openssl jq gettext-base

# 安装 Docker
if ! command -v docker >/dev/null 2>&1; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
fi

# 确认 docker compose 命令可用
if docker compose version >/dev/null 2>&1; then
  echo "✅ docker compose 可用"
else
  echo "❌ 未找到 docker compose，请安装 docker-compose-plugin"; exit 1
fi
```

## 3. 克隆项目
```bash
# 以实际路径为准
cd /opt
sudo https://github.com/langkebo/synapsecode.git
cd synapsecode
```

## 4. 配置域名与 Nginx（可选，生产推荐）
如果你需要通过 HTTPS 对外提供服务，请先运行：
```bash
sudo ./setup-domain.sh
```
该脚本会：
- 生成 Nginx HTTP 配置 -> 使用 webroot 验证申请 Let’s Encrypt 证书 -> 回写 HTTPS 配置并重载 Nginx
- 配置 /.well-known/matrix/server 和 /.well-known/matrix/client

如果仅在本机或者内网调试，可跳过本步骤。

## 5. 生成环境并部署
```bash
sudo chmod +x deploy-simple.sh
sudo ./deploy-simple.sh
```
脚本会：
- 检查/安装依赖（Docker、Compose）
- 生成 .env、data/homeserver.yaml、well-known 配置
- 使用 Dockerfile.simple 构建镜像，启动 Postgres + Synapse + well-known 服务
- 监听端口：
  - Synapse: 127.0.0.1:8008（仅本地回环，供 Nginx 反代）
  - well-known: 0.0.0.0:8080（可访问 /.well-known/matrix/*）

## 6. 验证与常用命令
```bash
# 查看容器状态
sudo docker compose -f docker-compose.simple.yml ps

# 查看日志
sudo docker compose -f docker-compose.simple.yml logs -f synapse

# API 健康检查（本地）
curl -s http://127.0.0.1:8008/_matrix/client/versions | jq .

# well-known 检查（本机）
curl -s http://127.0.0.1:8080/.well-known/matrix/server | jq .
```

## 7. 创建管理员账号
```bash
sudo docker compose -f docker-compose.simple.yml exec synapse \
  register_new_matrix_user -c /data/homeserver.yaml -a http://localhost:8008
```

## 8. 故障排查
- 构建失败（apt exit code 100）：
  - 已使用 Dockerfile.simple 简化依赖，若仍失败，请贴出完整 apt 输出
- Synapse 启动后 8008 无响应：
  - 查看 synapse 容器日志：`sudo docker compose -f docker-compose.simple.yml logs --tail=200 synapse`

提示：如果看到 “the attribute `version` is obsolete” 的警告，说明 Compose v2 已不需要 `version:` 字段。本项目已移除该字段，无需处理。
  - 确认 Postgres 健康：`sudo docker compose -f docker-compose.simple.yml logs postgres`
- HTTPS 访问失败：
  - 先确认 127.0.0.1:8008 可用，再检查 Nginx 配置与证书是否已签发

## 9. 目录说明（精简后）
- Dockerfile.simple：精简版镜像构建文件（基于 python:3.9-slim）
- deploy-simple.sh：一键部署脚本（默认使用 Dockerfile.simple）
- setup-domain.sh：域名与证书配置脚本（生产可选）
- docker-compose.simple.yml：部署脚本自动生成的编排文件
- data/、media/、uploads/：运行时数据与媒体文件
- well-known/：供 Nginx 或容器直接服务的发现配置

完成！如需进一步自动化或生产级扩展，请告知具体需求。