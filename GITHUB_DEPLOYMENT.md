# GitHub 快速部署指南

## 🚀 一键上传到GitHub

### 步骤1: 运行GitHub设置脚本
```bash
./setup-github.sh
```

这个脚本会：
- 提示您输入仓库名称和描述
- 引导您在GitHub创建仓库
- 自动推送代码到GitHub

### 步骤2: 手动GitHub部署（备选方案）

如果您想手动操作：

1. **创建GitHub仓库**
   - 访问 https://github.com
   - 点击 "New repository"
   - 仓库名称：`matrix-synapse-friends`
   - 描述：`Matrix Synapse server with friends functionality`
   - 选择 Public 或 Private
   - 不要勾选 "Add a README file"（我们已经有了）
   - 点击 "Create repository"

2. **推送代码**
```bash
# 添加远程仓库（替换您的用户名）
git remote add origin https://github.com/yourusername/matrix-synapse-friends.git

# 推送代码
git push -u origin main
```

## 📦 部署到服务器

### 从GitHub克隆并部署
```bash
# 克隆项目
git clone https://github.com/yourusername/matrix-synapse-friends.git
cd matrix-synapse-friends

# 复制环境配置
cp .env.example .env

# 编辑配置文件
nano .env

# 运行部署脚本
sudo ./deploy.sh
```

### 环境配置
在 `.env` 文件中设置：
```bash
# 服务器配置
MATRIX_SERVER_NAME=yourdomain.com
MATRIX_DOMAIN=yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com

# 功能开关
ENABLE_REGISTRATION=false
FRIENDS_ENABLED=true
MAX_FRIENDS_PER_USER=1000

# 数据库配置
POSTGRES_USER=synapse
POSTGRES_PASSWORD=your_strong_password
POSTGRES_DB=synapse
```

## 🔧 验证部署

```bash
# 运行验证脚本
./verify-setup.sh

# 检查服务状态
docker-compose ps
```

## 📖 文档说明

- `README.md` - 项目概览和基本使用
- `DOCKER_PRODUCTION_DEPLOYMENT.md` - 详细的生产环境部署指南
- `UBUNTU_DOCKER_DEPLOYMENT_MINIMAL.md` - 最小化部署指南（低配服务器）
- `setup-github.sh` - GitHub仓库设置脚本

## 🎯 快速开始

1. 运行 `./setup-github.sh` 上传到GitHub
2. 在服务器上 `git clone` 您的仓库
3. 运行 `sudo ./deploy.sh` 开始部署

您的Matrix服务器将在几分钟内准备就绪！