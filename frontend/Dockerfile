FROM node:20-alpine

WORKDIR /app

# Copy package files first
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code (will be overridden by volume in dev, but needed for build)
COPY . .

# Expose port
EXPOSE 5173

# Run dev server with host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
