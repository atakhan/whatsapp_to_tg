.PHONY: run front back help install-back playwright-install setup-env

# Default target
help:
	@echo "Available commands:"
	@echo "  make run      - Run both frontend and backend servers"
	@echo "  make front    - Run frontend development server only"
	@echo "  make back     - Setup and run backend server only"
	@echo "  make install-back - Install backend dependencies and Playwright"

# Run frontend development server
front:
	@echo "Starting frontend development server..."
	cd frontend && npm run dev

# Run both frontend and backend
run: install-back setup-env
	@echo "Starting backend and frontend servers..."
	@echo "Starting backend on http://localhost:8000..."
	@cd backend && start /B python -m uvicorn app.main:app --reload --port 8000
	@timeout /t 2 /nobreak >nul 2>&1 || sleep 2
	@echo "Starting frontend on http://localhost:5173..."
	@echo "Both servers are running. Press Ctrl+C to stop."
	@cd frontend && npm run dev

# Setup and run backend
back: install-back setup-env
	@echo "Starting backend server..."
	cd backend && python -m uvicorn app.main:app --reload --port 8000

# Setup .env file from example if it doesn't exist
setup-env:
	@if not exist backend\.env ( \
		echo Creating backend/.env from env.example... && \
		copy env.example backend\.env && \
		echo Please edit backend/.env and add your TELEGRAM_API_ID and TELEGRAM_API_HASH \
	) else ( \
		echo backend/.env already exists \
	)

# Install backend dependencies and Playwright browsers
install-back:
	@echo "Upgrading pip..."
	cd backend && python -m pip install --upgrade pip
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing Playwright browsers..."
	cd backend && python -m playwright install chromium
	@echo "Backend setup complete!"
