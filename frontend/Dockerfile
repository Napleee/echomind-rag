# EchoMind 前端镜像：Node 构建 → Nginx 托管（多阶段，产物镜像不含 node_modules）
# 国内构建默认走 npmmirror，可用 --build-arg 覆盖

# ---- 构建阶段 ----
FROM node:20-alpine AS build
WORKDIR /app
ARG NPM_REGISTRY=https://registry.npmmirror.com

# 先装依赖（仅 lock 文件变化才重装，利用层缓存）
COPY package.json package-lock.json ./
RUN npm config set registry ${NPM_REGISTRY} && npm ci

# 再拷源码构建
COPY . .
RUN npm run build

# ---- 运行阶段 ----
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
