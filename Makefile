.PHONY: help run front back build stop logs clean setup-env

COMPOSE ?= docker compose
ENV_FILE ?= backend/.env
ENV_EXAMPLE ?= env.example

# Default target
help:
	@echo "Available commands:"
	@echo "  make run    - Build and start backend+frontend (docker compose up)"
	@echo "  make front  - Start frontend service (and dependencies) in Docker"
	@echo "  make back   - Start backend service in Docker"
	@echo "  make build  - Build Docker images"
	@echo "  make stop   - Stop containers"
	@echo "  make logs   - Tail combined logs"
	@echo "  make clean  - Stop containers and remove volumes"

# Ensure backend/.env exists
setup-env:
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "Creating $(ENV_FILE) from $(ENV_EXAMPLE)..."; \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "Edit $(ENV_FILE) to set TELEGRAM_API_ID and TELEGRAM_API_HASH."; \
	else \
		echo "$(ENV_FILE) already exists."; \
	fi

# Build and run everything
run: setup-env
	$(COMPOSE) up --build

# Run only frontend service (will start backend if needed)
front: setup-env
	$(COMPOSE) up --build frontend

# Run only backend service
back: setup-env
	$(COMPOSE) up --build backend

# Build images without running
build: setup-env
	$(COMPOSE) build

# Stop containers (keeps volumes)
stop:
	$(COMPOSE) down

# Tail logs
logs:
	$(COMPOSE) logs -f

# Stop and remove containers and named volumes
clean:
	$(COMPOSE) down -v
