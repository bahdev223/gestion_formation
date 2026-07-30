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

Le compte de démonstration `admin/admin123` ne doit jamais être conservé en
production.
