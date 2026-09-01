# 构建阶段
FROM node:22.22-alpine@sha256:e58326d0d441090181ac150dc2078d3e2cf6a0d42e809aebba3ef5880935ffdd AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# ICP 备案号（可选）：构建时注入，非空时页面底部展示并链接 beian.miit.gov.cn
ARG VITE_ICP_NUMBER
ENV VITE_ICP_NUMBER=${VITE_ICP_NUMBER:-}
# AITDE 开关（可选覆盖）：留空 = 运行时跟随后端 GET /api/v2/health（推荐）。
# 仅在需要强制开/关时设为 true/false；显式 false 会覆盖后端开关。
# 历史缺陷：该 ARG 缺失导致前端恒为关闭，V4.0 全部 Mission 路由在生产不可达。
ARG VITE_AITDE_V3_ENABLED
ENV VITE_AITDE_V3_ENABLED=${VITE_AITDE_V3_ENABLED:-}
RUN npm run build

# 运行阶段：Nginx 托管静态站点 + 反代 /api
FROM nginx:alpine@sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
