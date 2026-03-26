# KEEN — test runner shortcuts
#
# Usage:
#   make test           Run all tests (backend + frontend)
#   make test-backend   Backend pytest only
#   make test-frontend  Frontend Vitest only

.PHONY: test test-backend test-frontend

test: test-backend test-frontend

test-backend:
	@echo "==> Backend tests"
	cd backend && python3 -m pytest tests/ -q

test-frontend:
	@echo "==> Frontend tests"
	cd frontend && npm test
