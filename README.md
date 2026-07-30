# BALY'S Formation Manager

La solution comprend désormais deux interfaces strictement séparées :

- l'application métier multi-entreprise sous `/o/<slug>/` ;
- la console SaaS SahelTech sous `/platform/`.

La documentation de la console d'exploitation est disponible dans
[`docs/platform-admin.md`](docs/platform-admin.md).

Application Django de gestion d'un centre de formation : catalogue,
sessions, apprenants, inscriptions, paiements, présences, documents PDF,
ressources humaines, paie, trésorerie et comptabilité SYSCOHADA.

## Prérequis

- Python 3.12 ou supérieur
- SQLite pour le développement
- PostgreSQL prévu pour la production

## Installation locale

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements/development.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py sync_roles
python manage.py seed_formations
python manage.py seed_financial_accounts
python manage.py runserver
```

Créez un administrateur avec un mot de passe fort :

```powershell
python manage.py createsuperuser
```

## Contrôles avant livraison

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --parallel 4
```

## Rôles disponibles

- Administrateur
- Responsable formation
- Formateur
- Comptable
- Responsable RH
- Caissier

Les groupes et leurs permissions sont synchronisés par les migrations ou avec
`python manage.py sync_roles`.

## Données non versionnées

La base SQLite, les fichiers `.env`, les documents générés, les médias et les
logs sont exclus de Git. Ne publiez jamais une base contenant des données
réelles ou des mots de passe.
