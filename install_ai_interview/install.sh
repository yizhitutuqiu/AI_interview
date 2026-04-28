#!/bin/bash

# AI 面试官 - 自动化部署脚本
# 适用平台: Linux (Ubuntu/Debian, CentOS) / macOS

set -e # 发生错误时立刻退出

echo "=========================================="
echo "      AI 面试官 - 环境一键安装脚本      "
echo "=========================================="
echo ""

# 1. 检查并安装 Git
if ! command -v git &> /dev/null; then
    echo "未检测到 git，正在尝试自动安装..."
    if [ "$(uname)" == "Darwin" ]; then
        if ! command -v brew &> /dev/null; then
            echo "未检测到 Homebrew，正在尝试自动安装 Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
                echo "错误: Homebrew 自动安装失败。"
                echo "请手动运行: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\" 然后重试。"
                exit 1
            }
            # 确保 brew 命令在当前会话可用 (针对 Apple Silicon)
            if [ -x "/opt/homebrew/bin/brew" ]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            fi
        fi
        brew install git
    elif [ -f /etc/debian_version ]; then
        sudo apt update && sudo apt install git -y
    elif [ -f /etc/redhat-release ]; then
        sudo yum install git -y
    else
        echo "错误: 无法识别当前操作系统类型，请手动安装 git。"
        exit 1
    fi
    echo "Git 安装完成！"
else
    echo "Git 已安装: $(git --version)"
fi

echo ""

# 2. 克隆项目代码
REPO_URL="https://github.com/yourusername/ai_interview.git"  # 请替换为真实的仓库地址
PROJECT_DIR="ai_interview"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "正在从 GitHub 下载项目代码..."
    git clone "$REPO_URL"
    cd "$PROJECT_DIR"
else
    echo "项目目录已存在，正在尝试更新代码..."
    cd "$PROJECT_DIR"
    git pull || true
fi

echo ""

# 3. 检查并安装 Miniconda
CONDA_DIR="$HOME/miniconda"
if ! command -v conda &> /dev/null && [ ! -d "$CONDA_DIR" ]; then
    echo "未检测到 conda，正在自动下载并安装 Miniconda..."
    
    OS_TYPE="$(uname)"
    ARCH="$(uname -m)"
    
    if [ "$OS_TYPE" == "Linux" ]; then
        if [ "$ARCH" == "x86_64" ]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        elif [ "$ARCH" == "aarch64" ]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"
        else
            echo "不支持的 Linux 架构: $ARCH"
            exit 1
        fi
    elif [ "$OS_TYPE" == "Darwin" ]; then
        if [ "$ARCH" == "x86_64" ]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        elif [ "$ARCH" == "arm64" ]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
        else
            echo "不支持的 macOS 架构: $ARCH"
            exit 1
        fi
    else
        echo "不支持的操作系统: $OS_TYPE"
        exit 1
    fi

    # 下载并静默安装
    wget "$MINICONDA_URL" -O miniconda.sh || curl -O miniconda.sh "$MINICONDA_URL"
    bash miniconda.sh -b -p "$CONDA_DIR"
    rm miniconda.sh
    
    echo "Miniconda 安装完成！"
    
    # 激活 conda 基础环境以便后续命令使用
    source "$CONDA_DIR/bin/activate"
    conda init
else
    echo "Conda 环境已存在。"
    # 尝试加载当前已存在的 conda 命令
    if command -v conda &> /dev/null; then
        source $(conda info --base)/bin/activate
    elif [ -d "$CONDA_DIR" ]; then
        source "$CONDA_DIR/bin/activate"
    fi
fi

echo ""

# 3. 创建并激活 conda 虚拟环境
ENV_NAME="ai_interview"
echo "正在检查 Python 虚拟环境 ($ENV_NAME)..."

if ! conda info --envs | grep -q "^$ENV_NAME"; then
    echo "正在创建 conda 虚拟环境: $ENV_NAME (Python 3.10)..."
    conda create -n $ENV_NAME python=3.10 -y
else
    echo "虚拟环境 $ENV_NAME 已存在。"
fi

# 激活环境
echo "激活环境 $ENV_NAME..."
source activate $ENV_NAME

echo ""

# 4. 安装项目依赖
echo "正在安装 Python 依赖 (requirements.txt)..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "警告: 未找到 requirements.txt 文件！"
fi

echo ""

# 5. 配置运行变量
echo "正在准备环境变量配置文件..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ".env 文件已从 .env.example 复制。"
    else
        echo "警告: 未找到 .env.example 文件！"
    fi
else
    echo ".env 文件已存在，跳过复制。"
fi

echo ""
echo "=========================================="
echo "部署脚本执行完毕！"
echo "=========================================="
echo ""
echo "接下来的步骤："
echo "1. 请编辑项目目录下的 .env 文件，填入你的火山引擎 API 密钥及 Endpoint ID。"
echo "2. 若要启动服务，请执行以下命令："
echo "   conda activate ai_interview"
echo "   python -m uvicorn app:app --reload"
echo "3. 启动后，在浏览器访问 http://127.0.0.1:8000"
echo ""