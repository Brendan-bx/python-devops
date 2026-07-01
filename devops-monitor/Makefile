.PHONY: up down logs test lint dev

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f

test:
	pytest tests/ -v --cov=api --cov-fail-under=75

lint:
	flake8 api/ dashboard/ tests/

dev:
	@echo "Lancez l'API et le dashboard dans deux terminaux :"
	@echo "  API_KEY=dev-key uvicorn api.main:app --reload --port 8000"
	@echo "  API_BASE_URL=http://localhost:8000 API_KEY=dev-key streamlit run dashboard/app.py --server.port 8501"
