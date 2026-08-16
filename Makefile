.PHONY: install run dev test lint clean

# Установка зависимостей через uv
install:
	uv sync

# Запуск приложения в продакшн режиме (uvicorn)
run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Запуск в режиме разработки с автоперезагрузкой (reload)
dev:
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Запуск тестов (pytest)
test:
	uv run pytest

# Проверка кода линтером (ruff)
lint:
	uv run ruff check .

# Очистка кэша
clean:
	rm -rf .venv
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
