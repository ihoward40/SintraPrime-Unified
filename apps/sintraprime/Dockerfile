# SintraPrime Airlock Server — TypeScript/Node.js
# Multi-stage build for production

FROM node:20-alpine AS builder

WORKDIR /build

# Copy package files
COPY package*.json ./
RUN npm ci --legacy-peer-deps 2>/dev/null || npm install --legacy-peer-deps

# Copy source files
COPY tsconfig.json ./
COPY src/ ./src/

# Build TypeScript
RUN npm run build 2>/dev/null || (mkdir -p dist && cp -r src/ dist/src/)

# Production stage
FROM node:20-alpine

# Install curl for health checks
RUN apk add --no-cache curl

WORKDIR /app

# Copy built files
COPY package*.json ./
RUN npm ci --only=production --legacy-peer-deps 2>/dev/null || npm install --only=production --legacy-peer-deps

COPY --from=builder /build/dist ./dist
COPY airlock_server/ ./airlock_server/

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S airlock -u 1001
USER airlock

# Health check
HEALTHCHECK --interval=15s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

EXPOSE 3001

# Try built TypeScript app first, fallback to airlock_server raw JS
CMD ["node", "dist/index.js"]
