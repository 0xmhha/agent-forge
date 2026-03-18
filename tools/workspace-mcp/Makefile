# workspace-mcp — MCP server management
# Usage: make <target>

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ── Server ───────────────────────────────────────

.PHONY: server
server: ## MCP 서버 실행
	uv run agent-forge-server

.PHONY: debug
debug: ## DEBUG 레벨로 MCP 서버 실행
	LOG_LEVEL=DEBUG uv run agent-forge-server

.PHONY: setup
setup: ## OAuth 설정 UI (최초 1회)
	uv run agent-forge-setup

# ── Development ──────────────────────────────────

.PHONY: install
install: ## 의존성 설치
	uv sync

.PHONY: test
test: ## 전체 테스트
	uv run python -m pytest -q

.PHONY: test-v
test-v: ## 테스트 (상세 출력)
	uv run python -m pytest -v

.PHONY: lint
lint: ## 코드 린트
	uv run ruff check src/ tests/

.PHONY: fix
fix: ## 린트 자동 수정
	uv run ruff check --fix src/ tests/

# ── Monitoring ───────────────────────────────────

.PHONY: log
log: ## 최신 로그 보기 (tail -f)
	@mkdir -p logs
	@touch logs/workspace-mcp.log
	tail -f logs/workspace-mcp.log

.PHONY: log-all
log-all: ## 전체 로그 보기
	@cat logs/workspace-mcp.log 2>/dev/null || echo "No log file yet. Run 'make server' first."

.PHONY: status
status: ## 서버 상태 확인 (토큰, 배치 설정, 리뷰 큐)
	@echo "=== Token Status ==="
	@ls -la ~/.agent-forge/tokens/ 2>/dev/null || echo "  No tokens found"
	@echo ""
	@echo "=== Batch Config ==="
	@cat ~/.agent-forge/batch-config.json 2>/dev/null || echo "  Using defaults (enabled, 10min interval)"
	@echo ""
	@echo "=== Review Queue ==="
	@echo "  pending: $$(ls data/reviews/pending/*.md 2>/dev/null | wc -l | tr -d ' ') files"
	@echo "  todo:    $$(ls data/reviews/todo/*.md 2>/dev/null | wc -l | tr -d ' ') files"
	@echo "  done:    $$(ls data/reviews/done/*.md 2>/dev/null | wc -l | tr -d ' ') files"
	@echo ""
	@echo "=== Triggers ==="
	@echo "  pending:   $$(ls data/triggers/pending/*.json 2>/dev/null | wc -l | tr -d ' ') files"
	@echo "  processed: $$(ls data/triggers/processed/*.json 2>/dev/null | wc -l | tr -d ' ') files"

# ── Cleanup ──────────────────────────────────────

.PHONY: clean
clean: ## 캐시/로그 정리
	rm -rf .pytest_cache __pycache__ src/**/__pycache__ logs/*.log

# ── Help ─────────────────────────────────────────

.PHONY: help
help: ## 사용 가능한 명령 목록
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
