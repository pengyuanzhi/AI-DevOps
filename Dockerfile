# ==========================================
# 多阶段构建 - AI-CICD 后端
# ==========================================

# ==========================================
# 构建阶段 - 安装依赖
# ==========================================
FROM python:3.13-slim AS builder

WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到独立目录
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ==========================================
# 生产阶段 - 最小化镜像
# ==========================================
FROM python:3.13-slim AS production

WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/install/lib/python3.13/site-packages:${PYTHONPATH}"

# 安装运行时依赖（包括 C/C++ 工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基础工具
    curl \
    git \
    # PostgreSQL 客户端库
    libpq5 \
    # C/C++ 构建工具（如果需要构建 C++ 项目）
    gcc \
    g++ \
    make \
    cmake \
    # 静态分析工具
    clang-tidy \
    cppcheck \
    # 内存检测工具
    valgrind \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制依赖
COPY --from=builder /install /install

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/data/cache /app/data/generated/tests /app/logs

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 切换到非root用户
USER appuser

# 启动命令（生产环境使用 gunicorn）
CMD ["gunicorn", "src.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
