# Web UI — React + Vite → nginx
# 构建上下文为 test-platform 根目录（见 docker-compose.yml: context: .），
# 因此所有 COPY 路径以 web-ui/ 和 docker/ 为前缀。
FROM node:20-alpine AS builder

WORKDIR /app
COPY web-ui/package.json web-ui/package-lock.json* ./
RUN npm install

COPY web-ui/ .
RUN npm run build

# --- nginx ---
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
