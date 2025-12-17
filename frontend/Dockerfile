FROM node:20-bullseye-slim

WORKDIR /app

# Copy package files first
COPY package*.json ./

# Install dependencies (include rollup native binary for linux x64)
RUN npm install

# Copy application code (will be overridden by volume in dev, but needed for build)
COPY . .

# Expose port
EXPOSE 5173

# Install deps at runtime (for bind-mount dev workflow) and start Vite
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]
