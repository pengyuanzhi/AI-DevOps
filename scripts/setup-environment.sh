#!/bin/bash
# AI-CICD 环境自动安装和检测脚本
# 支持 Ubuntu/Debian 和 macOS

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)

echo ""
echo "======================================"
echo "  AI-CICD 环境检测和安装"
echo "======================================"
echo ""
log_info "检测到操作系统: $OS"
echo ""

# 检查命令是否存在
check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# 安装 apt 包（Debian/Ubuntu）
install_apt_package() {
    local package=$1
    if ! dpkg -l | grep -q $package; then
        log_info "安装 $package..."
        sudo apt-get update -qq
        sudo apt-get install -y $package
    fi
}

# 安装 brew 包（macOS）
install_brew_package() {
    local package=$1
    if ! brew list $package &> /dev/null; then
        log_info "安装 $package..."
        brew install $package
    fi
}

# 1. 检查 Python
log_info "检查 Python 3.13+..."
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
        log_success "Python $PYTHON_VERSION ✓"
    else
        log_error "需要 Python 3.13+，当前版本: $PYTHON_VERSION"
        log_info "安装方法:"
        if [ "$OS" == "macos" ]; then
            echo "  brew install python@3.13"
        else
            echo "  sudo add-apt-repository ppa:deadsnakes/ppa"
            echo "  sudo apt-get update"
            echo "  sudo apt-get install python3.13 python3.13-venv python3.13-dev"
        fi
        exit 1
    fi
else
    log_error "未找到 Python 3"
    exit 1
fi

# 2. 检查 pip
log_info "检查 pip..."
if check_command pip3 || check_command pip; then
    log_success "pip ✓"
else
    log_warning "未找到 pip，正在安装..."
    python3 -m ensurepip --upgrade
fi

# 3. 检查 Docker
log_info "检查 Docker..."
if check_command docker; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    log_success "Docker $DOCKER_VERSION ✓"

    # 检查 Docker 服务
    if ! docker info &> /dev/null; then
        log_warning "Docker 服务未运行"
        log_info "启动 Docker 服务..."
        if [ "$OS" == "macos" ]; then
            open -a Docker
        else
            sudo systemctl start docker
        fi
        sleep 5
    fi
else
    log_error "未安装 Docker"
    log_info "安装方法:"
    if [ "$OS" == "macos" ]; then
        echo "  brew install --cask docker"
    else
        echo "  curl -fsSL https://get.docker.com | sh"
        echo "  sudo usermod -aG docker \$USER"
    fi
    exit 1
fi

# 4. 检查 Docker Compose
log_info "检查 Docker Compose..."
if check_command docker-compose || docker compose version &> /dev/null; then
    log_success "Docker Compose ✓"
else
    log_error "未安装 Docker Compose"
    log_info "安装方法:"
    if [ "$OS" == "macos" ]; then
        echo "  Docker Desktop 已包含 Docker Compose"
    else
        echo "  sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
        echo "  sudo chmod +x /usr/local/bin/docker-compose"
    fi
    exit 1
fi

# 5. 检查 Git
log_info "检查 Git..."
if check_command git; then
    GIT_VERSION=$(git --version | awk '{print $3}')
    log_success "Git $GIT_VERSION ✓"
else
    log_warning "未找到 Git，正在安装..."
    if [ "$OS" == "debian" ]; then
        install_apt_package git
    elif [ "$OS" == "macos" ]; then
        install_brew_package git
    fi
fi

# 6. 检查 C/C++ 构建工具（可选）
echo ""
log_info "检查 C/C++ 构建工具（可选）..."

# CMake
if check_command cmake; then
    CMAKE_VERSION=$(cmake --version | head -1 | awk '{print $3}')
    log_success "CMake $CMAKE_VERSION ✓"
else
    log_warning "未找到 CMake（C++ 项目需要）"
    MISSING_CPP_TOOLS=1
fi

# Make
if check_command make; then
    log_success "Make ✓"
else
    log_warning "未找到 Make"
    MISSING_CPP_TOOLS=1
fi

# GCC/G++
if check_command gcc && check_command g++; then
    GCC_VERSION=$(gcc --version | head -1 | awk '{print $3}')
    log_success "GCC $GCC_VERSION ✓"
else
    log_warning "未找到 GCC/G++"
    MISSING_CPP_TOOLS=1
fi

# Clang-Tidy（静态分析）
if check_command clang-tidy; then
    log_success "Clang-Tidy ✓"
else
    log_warning "未找到 Clang-Tidy（静态代码分析需要）"
    MISSING_CPP_TOOLS=1
fi

# Cppcheck（静态分析）
if check_command cppcheck; then
    log_success "Cppcheck ✓"
else
    log_warning "未找到 Cppcheck（静态代码分析需要）"
    MISSING_CPP_TOOLS=1
fi

# Valgrind（内存检测）
if check_command valgrind; then
    log_success "Valgrind ✓"
else
    log_warning "未找到 Valgrind（内存安全检测需要）"
    MISSING_CPP_TOOLS=1
fi

if [ ! -z "$MISSING_CPP_TOOLS" ]; then
    echo ""
    log_info "缺少 C/C++ 工具，安装方法:"
    if [ "$OS" == "debian" ]; then
        echo "  sudo apt-get install -y build-essential cmake clang-tidy cppcheck valgrind"
    elif [ "$OS" == "macos" ]; then
        echo "  brew install cmake llvm cppcheck valgrind"
    fi
    echo ""
    read -p "是否现在安装这些工具？[y/N]: " install_cpp
    if [[ $install_cpp =~ ^[Yy]$ ]]; then
        if [ "$OS" == "debian" ]; then
            sudo apt-get update
            sudo apt-get install -y build-essential cmake clang-tidy cppcheck valgrind
        elif [ "$OS" == "macos" ]; then
            brew install cmake llvm cppcheck valgrind
        fi
        log_success "C/C++ 工具安装完成"
    fi
fi

# 7. 安装 Python 依赖
echo ""
log_info "检查 Python 依赖..."
if [ -f "requirements.txt" ]; then
    log_info "安装 Python 依赖..."
    pip3 install -r requirements.txt --quiet
    log_success "Python 依赖安装完成 ✓"
else
    log_warning "未找到 requirements.txt"
fi

# 8. 检查环境配置
echo ""
log_info "检查环境配置..."
if [ ! -f ".env" ]; then
    log_warning ".env 文件不存在，从模板创建..."
    cp .env.example .env
    log_warning "请编辑 .env 文件配置 API 密钥"
else
    log_success ".env 文件已存在 ✓"
fi

# 9. 创建必要目录
log_info "创建必要目录..."
mkdir -p data/cache data/generated/tests logs
log_success "目录创建完成 ✓"

# 总结
echo ""
echo "======================================"
log_success "环境检测完成！"
echo "======================================"
echo ""
echo "下一步操作:"
echo "  1. 编辑 .env 文件，配置 API 密钥:"
echo "     - ANTHROPIC_API_KEY (必需)"
echo "     - GITLAB_TOKEN (可选)"
echo ""
echo "  2. 启动服务:"
echo "     ./start.sh          # Docker 模式"
echo "     或"
echo "     python3 -m src.main  # 本地模式"
echo ""
echo "  3. 运行测试:"
echo "     ./scripts/run-integration-tests.sh quick"
echo ""
echo "  4. 访问服务:"
echo "     - API 文档: http://localhost:8000/docs"
echo "     - 前端界面: http://localhost"
echo ""
