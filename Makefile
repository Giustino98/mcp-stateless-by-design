UV := uv
UV_CACHE_DIR := $(CURDIR)/.uv-cache
UV_PYTHON_INSTALL_DIR := $(CURDIR)/.uv-python
export UV_CACHE_DIR
export UV_PYTHON_INSTALL_DIR

.PHONY: install format format-check lint typecheck test check \
	serve-legacy-multiworker demo-legacy-multiworker \
	serve-sticky-replica-a serve-sticky-replica-b serve-sticky-proxy \
	serve-sticky-session demo-sticky-session \
	serve-modern-multiworker demo-modern-stateless

install:
	$(UV) sync --python 3.14.6

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

format-check:
	$(UV) run ruff format --check .

lint:
	$(UV) run ruff check .

typecheck:
	$(UV) run pyright

test:
	$(UV) run pytest

check: format-check lint typecheck test

serve-legacy-multiworker:
	$(UV) run uvicorn mcp_stateless.server:app --host 127.0.0.1 --port 8000 --workers 4 --no-access-log

demo-legacy-multiworker:
	$(UV) run python -m mcp_stateless.scenarios.legacy_multiworker

serve-sticky-replica-a:
	$(UV) run uvicorn mcp_stateless.server:app --host 127.0.0.1 --port 8001 --no-access-log

serve-sticky-replica-b:
	$(UV) run uvicorn mcp_stateless.server:app --host 127.0.0.1 --port 8002 --no-access-log

serve-sticky-proxy:
	$(UV) run python -m mcp_stateless.sticky_proxy

serve-sticky-session:
	$(MAKE) --no-print-directory -j3 serve-sticky-replica-a serve-sticky-replica-b serve-sticky-proxy

demo-sticky-session:
	$(UV) run python -m mcp_stateless.scenarios.sticky_session

serve-modern-multiworker:
	$(UV) run uvicorn mcp_stateless.server:app --host 127.0.0.1 --port 8020 --workers 4 --no-access-log

demo-modern-stateless:
	$(UV) run python -m mcp_stateless.scenarios.modern_stateless
