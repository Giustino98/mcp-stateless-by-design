UV := uv
UV_CACHE_DIR := $(CURDIR)/.uv-cache
UV_PYTHON_INSTALL_DIR := $(CURDIR)/.uv-python
export UV_CACHE_DIR
export UV_PYTHON_INSTALL_DIR

.PHONY: install format format-check lint typecheck test check serve demo-legacy-multiworker

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

serve:
	$(UV) run uvicorn mcp_stateless.server:app --host 127.0.0.1 --port 8000 --workers 4

demo-legacy-multiworker:
	$(UV) run python -m mcp_stateless.scenarios.legacy_multiworker
