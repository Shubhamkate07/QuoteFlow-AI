# ==============================================================================
# QuoteFlow AI - Frontend Dockerfile
# ==============================================================================
# Multi-stage Dockerfile:
# - Stage 1 (development): Vite dev server with hot module replacement (HMR)
# - Stage 2 (build): Compiles TypeScript and packages production bundles
# - Stage 3 (production): Ultra-fast, lightweight Nginx web server
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Development Server
# ------------------------------------------------------------------------------
FROM node:20-alpine AS development

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .

EXPOSE 5173

# Run Vite dev server bound to all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# ------------------------------------------------------------------------------
# Stage 2: Production Build
# ------------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Run production build
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 3: Production Nginx Server
# ------------------------------------------------------------------------------
FROM nginx:1.25-alpine AS production

# Copy compiled static assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with React Router & API proxy rules
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
