# ==========================================
# 多阶段构建 - AI-CICD 前端
# ==========================================

# ==========================================
# 构建阶段 - Node.js环境
# ==========================================
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV NODE_ENV=production \
    npm_config_loglevel=warn \
    npm_config_unsafe_perm=true

# 复制package文件
COPY package*.json ./

# 安装所有依赖（包括 devDependencies，构建需要）
RUN npm ci --legacy-peer-deps && \
    npm cache clean --force

# 复制源代码
COPY . .

# 构建Vue应用（直接使用 vite build，跳过 TypeScript 检查）
RUN npx vite build

# 验证构建产物
RUN ls -la dist/ && \
    test -f dist/index.html || (echo "Build failed: dist/index.html not found" && exit 1)

# ==========================================
# 生产阶段 - Nginx环境
# ==========================================
FROM nginx:alpine AS production

# 安装curl（用于健康检查）
RUN apk add --no-cache curl

# 复制构建产物到Nginx默认目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义Nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 创建非root用户并设置权限
RUN addgroup -g 1001 -S nginx-app && \
    adduser -S -D -H -u 1001 -h /usr/share/nginx/html -s /sbin/nologin -G nginx-app -g nginx-app nginx-app && \
    chown -R nginx-app:nginx-app /usr/share/nginx/html && \
    chown -R nginx-app:nginx-app /var/cache/nginx && \
    chown -R nginx-app:nginx-app /var/log/nginx && \
    chown -R nginx-app:nginx-app /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx-app:nginx-app /var/run/nginx.pid

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# 切换到非root用户
USER nginx-app

# 启动Nginx
CMD ["nginx", "-g", "daemon off;"]
