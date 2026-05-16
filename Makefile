.PHONY: start backend dashboard bot-status logs install

start:
	@echo "Starting backend and dashboard..."
	@cd backend && uvicorn app.main:app --reload --port 8000 &
	@cd dashboard && npm run dev

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dashboard:
	cd dashboard && npm run dev

bot:
	cd bot && python -m bot.main

bot-status:
	@curl -s http://localhost:8000/health | python -m json.tool

logs:
	docker compose logs -f

install:
	cd backend && pip install -r requirements.txt
	cd bot && pip install -r requirements.txt
	cd dashboard && npm install

docker-up:
	docker compose up --build

docker-down:
	docker compose down
