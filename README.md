# BALY'S FORMATION MANAGER

Application de gestion de formations, inscriptions, paiements et présences.

## Stack technique

- Django 5.1
- HTMX + Alpine.js
- Tailwind CSS
- SQLite (développement) / PostgreSQL (production)
- WeasyPrint (PDF)

## Démarrage rapide

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/development.txt
python manage.py migrate
python manage.py runserver
```
