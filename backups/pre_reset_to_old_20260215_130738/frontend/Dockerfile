# Multi-stage build for Vigil frontend

# Stage 1: Build stage (Debian-based to avoid rollup/musl issues)
FROM node:20 as builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
COPY vite.config.js ./

# Install dependencies
RUN npm ci
# Force install platform-native binaries to match the lockfile (Debian/glibc build)
RUN npm install @swc/core-linux-x64-gnu@1.15.8 @rollup/rollup-linux-x64-gnu@4.55.1 --no-save

# Copy source code
COPY src ./src
COPY public ./public
COPY index.html ./

# Build application
ARG VITE_API_URL=http://localhost:5000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Production server
FROM nginx:alpine

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built application from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
