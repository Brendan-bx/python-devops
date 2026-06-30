# DevOps Monitoring Dashboard

Dashboard de monitoring DevOps en temps réel : API FastAPI (métriques système, health checks) + frontend Streamlit.

## Architecture

- **API** (`api/`) — FastAPI sur le port 8000
- **Dashboard** (`dashboard/`) — Streamlit sur le port 8501

## Prérequis

- Python 3.11+
- pip

## Installation

```bash
cd Day3/Mini-Project/devops-monitor
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement local

**Terminal 1 — API :**

```bash
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Dashboard :**

```bash
streamlit run dashboard/app.py
```

- API : http://localhost:8000
- Docs : http://localhost:8000/docs
- Dashboard : http://localhost:8501

## Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `API_KEY` | Clé pour `POST /servers` et `DELETE /servers/{id}` | `dev-key` |

## Tests

```bash
pytest tests/ -v
pytest tests/ --cov=api --cov-report=term-missing
```

## Endpoints API

| Méthode | Chemin | Auth | Description |
|---------|--------|------|-------------|
| GET | `/health` | public | Liveness probe |
| GET | `/metrics` | public | Snapshot CPU / mémoire / disque |
| WS | `/ws/metrics` | public | Stream JSON toutes les secondes |
| POST | `/servers` | API key | Enregistrer un serveur |
| GET | `/servers` | public | Lister les serveurs (`?status=UP`) |
| GET | `/servers/{id}` | public | Détail d'un serveur |
| DELETE | `/servers/{id}` | API key | Supprimer un serveur |
| POST | `/servers/{id}/check` | public | Health check immédiat |
