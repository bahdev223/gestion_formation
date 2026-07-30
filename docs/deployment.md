# Déploiement

La version actuelle reste en environnement de développement SQLite. Avant une
mise en production :

1. créer un environnement Python isolé et installer
   `requirements/production.txt` ;
2. configurer les variables de `.env.example` avec un secret aléatoire ;
3. utiliser PostgreSQL et exécuter les migrations ;
4. exécuter `python manage.py sync_roles` ;
5. charger le plan comptable et les données initiales nécessaires ;
6. collecter les fichiers statiques ;
7. servir l'application derrière HTTPS ;
8. activer une sauvegarde quotidienne de la base et du dossier `media` ;
9. tester une restauration avant l'ouverture aux utilisateurs ;
10. exécuter la suite complète de tests sur la version déployée.

## Domaine officiel

L'application est publiée sur `https://formix.saheltech.tech`.

La production doit utiliser les variables suivantes :

```env
DJANGO_ALLOWED_HOSTS=formix.saheltech.tech
DJANGO_CSRF_TRUSTED_ORIGINS=https://formix.saheltech.tech
```

Le DNS du sous-domaine doit pointer vers le serveur d'hébergement. Le reverse
proxy doit terminer HTTPS, transmettre l'en-tête `X-Forwarded-Proto` et
rediriger le trafic HTTP vers HTTPS.

## Déploiement avec Coolify

1. Créer une ressource depuis le dépôt Git et sélectionner **Dockerfile**.
2. Utiliser `Dockerfile` comme chemin de construction et exposer le port `8000`.
3. Lier une base PostgreSQL puis renseigner les variables `DB_NAME`, `DB_USER`,
   `DB_PASSWORD`, `DB_HOST` et `DB_PORT`.
4. Générer une longue valeur aléatoire pour `DJANGO_SECRET_KEY`.
5. Renseigner les variables du domaine indiquées ci-dessus.
6. Définir le domaine Coolify sur `https://formix.saheltech.tech`.
7. Monter un volume persistant sur `/app/media`.
8. Utiliser `/health/` comme chemin de contrôle de santé.

### Connexion PostgreSQL dans Coolify

L’application accepte en priorité une URL PostgreSQL complète :

```env
DATABASE_URL=postgresql://utilisateur:mot-de-passe@hote-interne:5432/base
```

Dans Coolify, créez une ressource PostgreSQL dans le même projet et utilisez le
sélecteur de variables pour exposer son URL interne à l’application sous le nom
`DATABASE_URL`. Ne copiez pas l’URL publique de la base si les deux ressources
partagent le même réseau Coolify.

Si `DATABASE_URL` n’est pas utilisée, les quatre variables `DB_NAME`, `DB_USER`,
`DB_PASSWORD` et `DB_HOST` deviennent obligatoires. Le conteneur s’arrête
maintenant avec un diagnostic court et explicite lorsqu’une de ces valeurs
manque, au lieu de redémarrer avec un `KeyError`.

Variables recommandées :

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=une-longue-valeur-aleatoire-et-secrete
DJANGO_ALLOWED_HOSTS=formix.saheltech.tech
DJANGO_CSRF_TRUSTED_ORIGINS=https://formix.saheltech.tech
DJANGO_SECURE_HSTS_SECONDS=31536000
DATABASE_URL=postgresql://formix:mot-de-passe@postgres:5432/formix
DB_NAME=formix
DB_USER=formix
DB_PASSWORD=un-mot-de-passe-fort
DB_HOST=nom-interne-du-service-postgresql
DB_PORT=5432
PORT=8000
WEB_CONCURRENCY=3
GUNICORN_TIMEOUT=120
RUN_MIGRATIONS=true
COLLECT_STATIC=true
PUBLIC_APP_URL=https://formix.saheltech.tech
EMAIL_HOST=smtp.votre-fournisseur.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=Formix <noreply@saheltech.tech>
```

Le script de démarrage applique les migrations et collecte les fichiers
statiques avant de lancer Gunicorn. Le volume `/app/media` est indispensable
pour conserver les logos, couvertures et documents téléversés entre deux
déploiements.

Créer également une tâche planifiée Coolify quotidienne avec la commande :

```sh
python manage.py notify_expiring_subscriptions
```

Elle prévient les propriétaires à 7, 3 et 1 jour de l’échéance, puis le jour
de l’expiration. Chaque alerte envoyée est journalisée pour éviter les doublons.

Le compte de démonstration `admin/admin123` ne doit jamais être conservé en
production.
