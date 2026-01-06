# Frontend Dockerfile - Multi-stage build

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Note: No VITE_API_URL set - frontend auto-detects from window.location

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Production
FROM node:20-alpine AS production

WORKDIR /app

# Install a simple static file server
RUN npm install -g sirv-cli

# Copy built files from builder stage
COPY --from=builder /app/build ./build

# Default port (can be overridden)
ENV PORT=5678

# Expose port
EXPOSE 5678

# Serve the static files
CMD sh -c "sirv build --host 0.0.0.0 --port ${PORT} --single"
