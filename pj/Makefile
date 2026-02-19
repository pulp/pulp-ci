.PHONY: format
format:
	ruff format
	ruff check --fix

.PHONY: lint
lint:
	ruff format --check --diff
	ruff check --diff
	mypy
	@echo "🙊 Code 🙈 LGTM 🙉 !"
