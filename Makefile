.PHONY: help install install-dev lint format typecheck test test-cov \
        migrate migrate-create docker-up docker-down docker-logs clean

# ── Help ────────────────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Installation ─────────────────────────────────────────────────────────────
install: ## Install production dependencies via uv
	uv sync --no-dev

install-dev: ## Install all dependencies including dev tools
	uv sync
	uv run pre-commit install

# ── Code Quality ─────────────────────────────────────────────────────────────
lint: ## Run ruff linter
	uv run ruff check src tests

format: ## Run ruff formatter
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck: ## Run mypy type checker
	uv run mypy src

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run tests
	export ENV_FILE=test.env && uv run pytest tests/

test-unit: ## Run only unit tests
	export ENV_FILE=test.env && uv run pytest tests/unit/

test-integration: ## Run only integration tests (requires running services)
	export ENV_FILE=test.env && uv run pytest tests/integration/

test-cov: ## Run tests with coverage report
	export ENV_FILE=test.env && uv run pytest --cov=payment_service --cov-report=html tests/

# ── Database ──────────────────────────────────────────────────────────────────
migrate: ## Apply all pending migrations
	uv run alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create name="add_index")
	uv run alembic revision --autogenerate -m "$(name)"

migrate-down: ## Rollback one migration
	uv run alembic downgrade -1

migrate-history: ## Show migration history
	uv run alembic history --verbose

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up: ## Start all services
	docker compose up -d

docker-build: ## Build and start all services
	docker compose up -d --build

docker-down: ## Stop all services
	docker compose down

docker-down-v: ## Stop all services and remove volumes
	docker compose down -v

docker-logs: ## Follow logs from all services
	docker compose logs -f

docker-logs-api: ## Follow API service logs
	docker compose logs -f api

docker-logs-worker: ## Follow consumer worker logs
	docker compose logs -f worker

# ── Development ───────────────────────────────────────────────────────────────
dev-api: ## Run API server locally (requires .env)
	uv run uvicorn payment_service.main:app --reload --host 0.0.0.0 --port 8000

dev-worker: ## Run consumer worker locally (requires .env)
	uv run python -m payment_service.workers.consumer

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove build artifacts and cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete
