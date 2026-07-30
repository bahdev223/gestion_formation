# Formix

Formix est une plateforme SaaS multi-entreprise dédiée à la gestion des
organismes de formation. Chaque entreprise dispose d’un espace isolé, de son
identité visuelle, de ses utilisateurs et des modules autorisés par son
abonnement.

## Accès à la plateforme

- Site public et connexion : `https://formix.saheltech.tech/`
- Console d’administration SaaS : `/platform/`
- Espace d’une entreprise : `/o/<slug>/`
- Administration technique Django : `/admin/`
- Contrôle de santé : `/health/`

Les utilisateurs peuvent se connecter avec leur adresse e-mail ou leur
matricule. Après authentification, ils sont redirigés vers leur entreprise selon
leur rôle et leurs permissions.

## Fonctionnalités

- catalogue de formations, catégories, sessions et séances ;
- gestion des apprenants, inscriptions et présences ;
- paiements, reçus, attestations et documents PDF ;
- ressources humaines, départements et dossiers employés ;
- paie salariale, échéances, paiements et bulletins ;
- trésorerie, comptes financiers et rapprochements ;
- comptabilité SYSCOHADA ;
- paramètres, logo et thème personnalisables par entreprise ;
- console SaaS pour les entreprises, abonnements et modules.

## Offres commerciales

Les offres affichées aux clients sont :

- **Basic**
- **Business**
- **Enterprise**

Les codes historiques `STARTER`, `PREMIUM` et `PRO` restent internes afin de
préserver la compatibilité des abonnements existants. Les offres manquantes sont
créées automatiquement au démarrage lorsque `SEED_DEFAULT_PLANS=true`.

## Architecture

Le projet est organisé par domaines Django :

```text
accounts/          Authentification, utilisateurs, rôles et permissions
organisations/     Entreprises, membres et isolation des données
subscriptions/     Plans, abonnements, modules et limitations
platform_admin/    Console d’exploitation SaaS
formations/        Catalogue, sessions et séances
participants/      Dossiers des apprenants
inscriptions/      Inscriptions aux sessions
paiements/         Paiements liés aux formations
presences/         États de présence par séance
documents/         Reçus, listes, attestations et PDF
django_rh/         Ressources humaines
django_paie/       Paie salariale
comptes/           Comptes financiers et trésorerie
comptabilite_ohada/ Comptabilité SYSCOHADA
dashboard/         Tableaux de bord et paramètres d’entreprise
core/              Composants techniques partagés
config/            Configuration Django
```

La documentation de la console SaaS est disponible dans
[`docs/platform-admin.md`](docs/platform-admin.md).

## Stack technique

- Python 3.12+
- Django 5.2
- PostgreSQL en production
- SQLite pour le développement local
- HTMX, Alpine.js et Tailwind CSS
- WeasyPrint et ReportLab pour les PDF
- Gunicorn et WhiteNoise en production
- Docker et Coolify pour le déploiement

## Installation locale

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements/development.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_plans
python manage.py sync_roles
python manage.py seed_formations
python manage.py seed_financial_accounts
python manage.py createsuperuser
python manage.py runserver
```

L’application locale est ensuite accessible sur `http://127.0.0.1:8000/`.

## Variables de production

Les principales variables attendues par Coolify sont :

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<secret-fort>
DJANGO_ALLOWED_HOSTS=formix.saheltech.tech
DJANGO_CSRF_TRUSTED_ORIGINS=https://formix.saheltech.tech
PUBLIC_APP_URL=https://formix.saheltech.tech

DB_ENGINE=django.db.backends.postgresql
DB_HOST=<hote-postgresql-interne>
DB_PORT=5432
DB_NAME=<nom-base>
DB_USER=<utilisateur>
DB_PASSWORD=<mot-de-passe>

RUN_MIGRATIONS=true
COLLECT_STATIC=true
SEED_DEFAULT_PLANS=true
```

Les secrets réels ne doivent jamais être enregistrés dans Git.

## Déploiement Coolify

Le conteneur exécute automatiquement :

1. les migrations Django si `RUN_MIGRATIONS=true` ;
2. la création idempotente des offres si `SEED_DEFAULT_PLANS=true` ;
3. la collecte des fichiers statiques si `COLLECT_STATIC=true` ;
4. le démarrage de Gunicorn.

Après un push sur `main`, lancez un nouveau déploiement dans Coolify puis
vérifiez `/health/` et les journaux du conteneur.

## Contrôles avant livraison

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python -m ruff check .
python manage.py test --parallel 4
```

## Sécurité et données

- ne versionnez jamais `.env`, les bases SQLite, les médias ni les journaux ;
- utilisez un secret Django différent pour chaque environnement ;
- faites tourner immédiatement tout secret exposé ;
- sauvegardez régulièrement PostgreSQL et les médias persistants ;
- accordez les accès selon le principe du moindre privilège.
