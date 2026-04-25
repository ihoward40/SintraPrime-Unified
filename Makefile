.PHONY: help install setup deploy dev test clean health

help:
	@echo "SintraPrime-Unified Makefile Commands"
	@echo "===================================="
	@echo "setup       - Initial setup (Docker, DB, dependencies)"
	@echo "install     - Install all dependencies"
	@echo "dev         - Start development environment"
	@echo "deploy      - Deploy to Docker containers"
	@echo "test        - Run all tests"
	@echo "health      - Check service health"
	@echo "logs        - Show container logs"
	@echo "clean       - Stop and remove containers"

install:
	@echo "Installing dependencies..."
	cd core && pip install -r requirements.txt
	cd apps/sintraprime && npm install
	cd apps/ike-bot && npm install

setup:
	@echo "Setting up unified environment..."
	docker-compose build
	docker-compose up -d postgres redis
	sleep 5
	docker-compose up -d

deploy: setup
	@echo "Deploying SintraPrime-Unified..."
	docker-compose up -d
	@echo "✓ Deployment complete"
	@echo "Hive Mind API: http://localhost:8080"
	@echo "Airlock Server: http://localhost:3001"
	@echo "Grafana Dashboard: http://localhost:3000"

dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

test:
	@echo "Running test suite..."
	cd core && pytest -v
	cd apps/sintraprime && npm test
	cd apps/ike-bot && npm test
	cd tests/integration && pytest -v

health:
	@echo "Checking service health..."
	curl -s http://localhost:8080/health || echo "Hive Mind: DOWN"
	curl -s http://localhost:3001/health || echo "Airlock: DOWN"

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name node_modules -exec rm -rf {} +

.DEFAULT_GOAL := help
