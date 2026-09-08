.PHONY: format _format
format:
	uv run $(MAKE) _format

_format:
	ruff format
	ruff check --fix

.PHONY: lint _lint
lint:
	uv run $(MAKE) _lint

_lint:
	ruff format --check --diff
	ruff check --diff --output-format concise
	ty check --output-format concise
	@echo "🙊 Code 🙈 LGTM 🙉 !"
