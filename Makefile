.PHONY: up down test lint migrate seed clean

# ── Docker ──
up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart backend

# ── 后端 ──
lint:
	cd backend && ruff check app/ tests/

format:
	cd backend && ruff format app/ tests/

test:
	cd backend && pytest tests/ -v --cov=app --cov-report=term

test-model:
	cd backend && pytest tests/test_models/ -v

test-api:
	cd backend && pytest tests/test_api/ -v

migrate:
	docker compose exec backend alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"

seed:
	docker compose exec backend python seed.py

# ── 前端 ──
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

# ── 清理 ──
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
