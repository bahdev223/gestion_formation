# Coolify — checklist d'opÃ©ration

## Variables d'environnement minimales

```
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<secret-long-et-fort>
DJANGO_ALLOWED_HOSTS=formix.saheltech.tech
DJANGO_CSRF_TRUSTED_ORIGINS=https://formix.saheltech.tech
PUBLIC_APP_URL=https://formix.saheltech.tech
RUN_MIGRATIONS=true
SEED_DEFAULT_PLANS=true
COLLECT_STATIC=true
RUN_COLLECTSTATIC=true
RUN_MIGRATE=false
DB_NAME=formix
DB_USER=postgres
DB_PASSWORD=...
DB_HOST=<pg-internal-host>
DB_PORT=5432
```

## ParamÃ¨tres applicatifs

- Build Pack : Dockerfile
- Base Directory : `/`
- Exposed Port : `8000`
- Domain : `https://formix.saheltech.tech`
- Health check : `/health/live/`
- Watch Paths : vide

## Commande de dÃ©ploiement

Conserver la commande par dÃ©faut du `Dockerfile` et surveiller la sortie stdout du
conteneur :

1. migrations (si activÃ©es)
2. seed plans (si activÃ©)
3. collectstatic (si activÃ©)
4. dÃ©marrage Gunicorn

## Monitoring de base

- Erreurs 5xx
- Temps de rÃ©ponse
- Espace disque (`/app/media`)
- Connexions PostgreSQL
- RÃ©ussite des alertes d'abonnement
