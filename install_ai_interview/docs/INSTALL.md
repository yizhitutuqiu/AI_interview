# AI 面试官 - 部署指南

## 1. 准备基础环境 (Git & Miniconda)

### 1.1 安装 Git 与项目克隆
如果你还没有安装 Git，请先根据系统安装：
- **Ubuntu/Debian**: `sudo apt install git -y`
- **CentOS**: `sudo yum install git -y`
- **macOS**: `brew install git` (需先安装 Homebrew)

克隆项目到本地：
```bash
git clone <项目仓库地址>
cd ai_interview
```

### 1.2 自动化安装 Miniconda (Linux/macOS)
使用命令行快速下载并安装 Miniconda（以 Linux x86_64 为例，macOS 请替换对应的下载链接）：
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda
source $HOME/miniconda/bin/activate
conda init
```
重启终端使 conda 生效。

---

## 2. 创建环境与安装依赖

### 2.1 创建并激活 Python 环境
```bash
conda create -n ai_interview python=3.10 -y
conda activate ai_interview
```

### 2.2 安装项目依赖
确保处于 `ai_interview` 目录下，执行：
```bash
pip install -r requirements.txt
```

---

## 3. 配置运行变量

### 3.1 准备环境变量文件
```bash
cp .env.example .env
```

### 3.2 填写 API 密钥
编辑 `.env` 文件，填入你的火山引擎信息：
```env
DOUBAO_API_KEY=your_api_key_here
DOUBAO_ENDPOINT_ID=your_text_model_endpoint_id
DOUBAO_LITE_ENDPOINT_ID=your_multimodal_lite_endpoint_id
```

---

## 4. 启动服务

### 4.1 运行后端
```bash
python -m uvicorn app:app --reload
```

### 4.2 访问系统
1. 打开 Chrome 或 Edge 浏览器。
2. 访问：[http://127.0.0.1:8000](http://127.0.0.1:8000)
3. 允许浏览器请求的摄像头和麦克风权限。