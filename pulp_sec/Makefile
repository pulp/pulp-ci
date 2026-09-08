.PHONY: help
help:
	@echo "Run locally with: uv run pulp-sec"
	@echo "Install with: uv tool install ."
	@echo "Install editable with: uv tool install -e ."
	@echo "Check code with: make [format] lint test"

.PHONY: format
format:
	uv run ruff check --select I --fix
	uv run ruff format

.PHONY: lint
lint:
	uv run ruff format --check
	uv run ruff check --output-format concise
	uv run ty check --output-format concise

.PHONY: test
test:
	uv run pytest
