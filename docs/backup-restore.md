# Sauvegarde et restauration (PostgreSQL + media)

## Sauvegarde base (Coolify)

1. CrÃ©er une planification journaliÃ¨re sur la resource PostgreSQL.
2. Conserver une rÃ©tention de 7 Ã  30 jours.
3. DÃ©poser les dumps vers un stockage distants (S3/R2 recommandÃ©).

## Test de restauration (minimum)

1. CrÃ©er une base de test.
2. Restaurer le dernier dump.
3. Lancer `python manage.py migrate --check`.
4. ExÃ©cuter un login simple et une lecture organisationnelle.

## Sauvegarde des mÃ©dias

- Volume obligatoire : `/app/media` montÃ© de maniÃ¨re persistante dans Coolify.
- Script d'archivage ponctuel : copier le contenu du volume `/app/media`.
- Restaurer en remettant le volume et en validant quelques URLs mÃ©tier.

## Rappel

Une sauvegarde DB seule ne suffit pas si les documents, logos et attestions ne sont
pas restaurÃ©s.
