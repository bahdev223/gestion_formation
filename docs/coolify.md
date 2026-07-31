# Coolify — checklist d’operation

## Variables d’environnement minimales

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

APP_MEDIA_ROOT=/app/media
APP_STATIC_ROOT=/app/static/dist
```

## Paramètres applicatifs

- Build Pack : Dockerfile
- Base Directory : `/`
- Exposed Port : `8000`
- Domain : `https://formix.saheltech.tech`
- Health check : `/health/live/`
- Watch Paths : vide

## Volume persistant (obligatoire)

### 1) Côté stockage (media)

1. Ouvrir la resource d'application dans Coolify.
2. Onglet **Persistent Storage**.
3. Cliquer **Add Storage** puis **Directory**.
4. Renseigner :
   - **Mount path** : `/app/media`
   - **Access mode** : `rw`
   - Activer la conservation du volume (`Retain` / `Conserver`)
   - Taille : `5Gi` minimum (adapter selon vos besoins)
5. Enregistrer puis faire **Redeploy**.

### 2) (Option) logs applicatifs

6. Ajouter un second volume `Directory` si vous voulez conserver les logs :
   - **Mount path** : `/app/logs`
   - **Access mode** : `rw`

## Pourquoi c’est indispensable

`/app/media` contient les logos, couvertures, documents et exports uploadés par les
utilisateurs. Sans montage persistant, un redéploiement recrée un conteneur propre et
efface ces fichiers.

La configuration actuelle lit ce chemin via `APP_MEDIA_ROOT`, donc si votre volume est
monté ailleurs, mettez `APP_MEDIA_ROOT` en conséquence.

## Commande de déploiement

Conserver la commande par défaut du Dockerfile et surveiller le log de démarrage :

1. Migrations (si activées)
2. Seed plans (si activé)
3. Collectstatic (si activé)
4. Démarrage Gunicorn

## Monitoring de base

- Erreurs 5xx
- Temps de réponse
- Espace disque (`/app/media`)
- Connexions PostgreSQL
- Succès des alertes d’abonnement
