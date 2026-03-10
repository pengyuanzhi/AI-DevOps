# ==========================================
# 构建阶段 - Node.js环境
# ==========================================
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖（使用npm ci以确保一致性）
RUN npm ci --only=production && \
    npm cache clean --force

# 复制源代码
COPY . .

# 构建Vue应用
RUN npm run build

# ==========================================
# 生产阶段 - Nginx环境
# ==========================================
FROM nginx:alpine

# 安装curl（用于健康检查）
RUN apk add --no-cache curl

# 复制构建产物到Nginx默认目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义Nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 创建非root用户
RUN addgroup -g 1001 -S nginx-app && \
    adduser -S -D -H -u 1001 -h /usr/share/nginx/html -s /sbin/nologin -G nginx-app -g nginx-app nginx-app && \
    chown -R nginx-app:nginx-app /usr/share/nginx/html && \
    chown -R nginx-app:nginx-app /var/cache/nginx && \
    chown -R nginx-app:nginx-app /var/log/nginx && \
    chown -R nginx-app:nginx-app /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx-app:nginx-app /var/run/nginx.pid

# 切换到非root用户
USER nginx-app

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 启动Nginx
CMD ["nginx", "-g", "daemon off;"]
