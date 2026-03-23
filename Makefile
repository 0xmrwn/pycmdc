# pycmdc developer interface
# Usage: make [target]

.PHONY: setup lint format fix typecheck test clean

setup:
	uv sync --dev
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .

fix:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run pyright

test:
	uv run pytest

clean:
	rm -rf .venv .ruff_cache .pytest_cache .pyright build dist *.egg-info
