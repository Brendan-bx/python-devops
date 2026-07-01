# DevOps Monitoring Dashboard

Système de monitoring temps réel en Python : API FastAPI pour les métriques système et la gestion de serveurs, dashboard Streamlit pour la visualisation live, le tout containerisé avec Docker.

## Architecture

```
devops-monitor/
├── api/              FastAPI (port 8000)
│   ├── GET  /health
│   ├── GET  /metrics
│   ├── WS   /ws/metrics
│   ├── POST /servers          (API key)
│   ├── GET  /servers
│   ├── DELETE /servers/{id}   (API key)
│   └── POST /servers/{id}/check
└── dashboard/        Streamlit (port 8501)
    ├── Onglet Métriques : KPIs + graphique live (60 s)
    └── Onglet Serveurs : tableau coloré + formulaire
```

## Prérequis

- Python 3.11
- Docker et Docker Compose
- Make (optionnel mais recommandé)

## Lancement local

```bash
git clone <url-du-repo>
cd devops-monitor
cp .env.example .env          # renseigner API_KEY
make up                       # démarre la stack Docker
make test                     # lance les tests
```

URLs locales une fois la stack démarrée :

| Service    | URL                          |
|------------|------------------------------|
| API        | http://localhost:8000        |
| Swagger    | http://localhost:8000/docs   |
| Dashboard  | http://localhost:8501        |

## Développement sans Docker

```bash
pip install -r requirements.txt
cp .env.example .env

# Terminal 1 — API
API_KEY=dev-key uvicorn api.main:app --reload --port 8000

# Terminal 2 — Dashboard
API_BASE_URL=http://localhost:8000 API_KEY=dev-key streamlit run dashboard/app.py --server.port 8501
```

## Commandes Make

| Cible   | Description                              |
|---------|------------------------------------------|
| `make up`   | `docker compose up --build -d`       |
| `make down` | `docker compose down -v`             |
| `make logs` | `docker compose logs -f`               |
| `make test` | pytest avec couverture ≥ 75 %        |
| `make lint` | flake8 sur api/, dashboard/, tests/  |
| `make dev`  | Instructions pour le dev local       |

## Variables d'environnement

| Variable       | Description                                              | Exemple                |
|----------------|----------------------------------------------------------|------------------------|
| `API_KEY`      | Clé d'authentification (`X-API-Key`)                   | `my-secret-key`        |
| `API_BASE_URL` | URL de l'API vue par le dashboard                        | `http://api:8000`      |

> Dans Docker Compose, le dashboard utilise `http://api:8000` (nom de service), jamais `localhost`.

## CI/CD

Le workflow GitHub Actions (`.github/workflows/ci-cd.yml`) exécute sur chaque push et PR :

1. **Lint** — flake8
2. **Test** — pytest avec couverture ≥ 75 %

## Sécurité

- Ne jamais committer le fichier `.env`
- La clé API est injectée via variable d'environnement
- Les routes `POST /servers` et `DELETE /servers/{id}` exigent le header `X-API-Key`
