# Bet261 Analytics — service FastAPI

Service de **collecte continue** et d'**analyse statistique** de la ligue virtuelle
*English League* (id 8035) de Bet261, avec **backtest de stratégies de pari**.

Architecture : un collecteur (job APScheduler) écrit dans une base **SQLite (WAL)** ;
une **API FastAPI** lit cette base et expose les analyses en JSON (doc Swagger `/docs`).

```
[collecteur APScheduler]  --écrit-->  [SQLite WAL]  <--lit--  [API FastAPI]  <--HTTP-->  toi
```

## Structure

```
app/
├── main.py                     # app FastAPI : lifespan (démarre le scheduler), CORS, handler d'erreurs
├── scheduler.py                # APScheduler BackgroundScheduler
├── logging_config.py
├── env/settings.py             # configuration (pydantic-settings)                                                                                                                                                             
├── common/
│   ├── decorator/api_endpoint.py
│   └── dependencies.py         # require_api_key
├── database/                   # engine SQLite WAL, session
├── collector/                  # FEATURE collecte
│   ├── client/bet261_client.py
│   ├── cron/collect_scheduler.py
│   ├── handler/                # parsing, filtre marchés
│   ├── models/                 # Match, Goal, Odd (ORM)
│   ├── repository/
│   └── services/               # collect_odds, collect_results
└── analytics/                  # FEATURE analyse + API
    ├── controllers/analytics_router.py
    ├── handler/stats.py        # Wilson, chi², résolution de paris
    ├── repository/             # requêtes streaming (mémoire ~constante)
    ├── schemas/
    └── services/               # match_stats, odds_stats, timing, health
```

## Installation

```bash
python -m venv venv && source venv/bin/activate   # (Windows : venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env
```

## Lancement

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Au démarrage : création des tables, puis le collecteur tourne automatiquement
(toutes les `POLL_INTERVAL_SECONDS`, 60 s par défaut). Doc interactive : **http://127.0.0.1:8000/docs**

## Configuration (.env)

| Variable | Défaut | Rôle |
|---|---|---|
| `ENVIRONMENT` | local | `local` active les logs SQL et l'écho |
| `LEAGUE_ID` | 8035 | ligue virtuelle ciblée |
| `DATABASE_URL` | sqlite:///bet261.db | base SQLite |
| `POLL_INTERVAL_SECONDS` | 60 | fréquence de collecte |
| `ALL_MARKETS` | false | `true` = 33 marchés (volumineux) |
| `ENABLE_SCHEDULER` | true | désactive le collecteur (utile en test) |
| `TZ_OFFSET` | 3 | heure locale d'affichage (Madagascar) |
| `API_KEY` | (vide) | si défini, exige l'entête `X-API-Key` |

## Endpoints (`/api/analytics`)

`/health` · `/overview` · `/results` · `/goals` · `/timing` · `/by-hour?tz_offset=3`
· `/by-team` · `/calibration` · `/backtest?min_samples=200&limit=30` · `/randomness`
· `/matches?limit=&offset=&team=&round=`

## Déploiement VPS (systemd)

```ini
# /etc/systemd/system/bet261.service
[Unit]
Description=Bet261 Analytics API
After=network.target

[Service]
WorkingDirectory=/opt/bet261-backend
ExecStart=/opt/bet261-backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
EnvironmentFile=/opt/bet261-backend/.env

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now bet261
```
Collecteur + API tournent dans le même service. Pour l'exposer sur Internet :
définir `API_KEY`, puis placer un reverse proxy nginx + HTTPS devant uvicorn.

## Notes méthodologiques

Les ligues virtuelles sont générées par RNG : ce service mesure les fréquences,
la calibration des cotes et le ROI **avec intervalles de confiance**. Une stratégie
n'est crédible que si l'IC de son ROI reste strictement positif **et** se confirme
sur une période hors-échantillon. Les décisions de pari restent les tiennes.
