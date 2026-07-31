# Architecture de Formix

Ce document décrit les règles structurelles et de sécurité à respecter dans
Formix. Toute nouvelle vue, API, commande ou service métier doit préserver
l’isolation entre les entreprises.

## Séparation plateforme et espaces clients

Formix possède deux périmètres distincts :

- `/platform/` : console SaaS réservée aux opérateurs de la plateforme ;
- `/o/<organisation_slug>/` : espace métier isolé d’une entreprise.

Le slug présent dans l’URL détermine le tenant courant. Une donnée envoyée par
le navigateur, un champ caché ou un identifiant fourni dans une requête ne doit
jamais servir directement à choisir l’organisation.

## Résolution du tenant

`organisations.middleware.OrganisationMiddleware` résout l’organisation à
partir de `organisation_slug` et la place sur la requête. Il vérifie également
que l’utilisateur connecté est membre actif de cette organisation.

Le code métier doit utiliser :

```python
from organisations.utils import require_request_organisation

organisation = require_request_organisation(request)
```

Cette fonction échoue explicitement si aucun tenant valide n’est disponible.
Une absence de tenant ne doit jamais produire un queryset global.

## Modèles appartenant à une organisation

Les données métier héritent de `core.models.OrganisationOwnedModel`. Elles
portent une clé étrangère `organisation` indexée.

Exemples :

- formations, sessions et séances ;
- participants et inscriptions ;
- paiements et présences ;
- employés, départements et postes ;
- exercices, écritures et configurations comptables.

Le champ reste temporairement nullable pour permettre l’audit des anciennes
bases. Aucune nouvelle donnée métier ne doit toutefois être créée sans
organisation. Avant de passer la colonne à `NOT NULL`, exécuter :

```powershell
python manage.py audit_tenant_integrity
```

Sur une ancienne base réellement mono-entreprise, la réparation contrôlée est :

```powershell
python manage.py audit_tenant_integrity --fix-single-tenant
```

La commande refuse de choisir arbitrairement une entreprise lorsque plusieurs
organisations existent.

## Vues HTML

Les vues génériques utilisent `core.mixins.OrganisationScopedMixin`.

Ce mixin :

- filtre le queryset sur l’organisation courante ;
- affecte l’organisation avant la sauvegarde ;
- transmet l’organisation aux formulaires ;
- produit les redirections avec l’URL du tenant.

Une vue métier ne doit jamais remplacer ce comportement par
`Model.objects.all()`.

## API REST

Les ViewSets métier utilisent
`core.mixins.OrganisationScopedViewSetMixin`.

Ce mixin :

- filtre automatiquement le queryset ;
- impose l’organisation lors de la création ;
- résout les identifiants fournis par le client avec `scoped_object()` ;
- lève une erreur de configuration si aucun chemin vers l’organisation
  n’existe.

Exemple :

```python
compte = self.scoped_object(Compte, request.data.get("compte_id"))
```

Il est interdit d’utiliser `Model.objects.get(pk=request.data["id"])` pour une
donnée métier.

## Référentiels globaux

`CompteComptable` et `JournalComptable` représentent les référentiels standards
SYSCOHADA partagés par la plateforme. Ils sont exposés en lecture seule aux
clients.

Les opérations qui utilisent ces référentiels restent propres à une
organisation :

- écritures ;
- exercices ;
- soldes ;
- immobilisations ;
- états financiers.

Le chargement du plan comptable utilise `update_or_create()` et ne supprime
jamais globalement les comptes. Une entreprise ne peut donc pas détruire ou
modifier le référentiel partagé depuis son API.

## Ressources humaines et paie

Les employés sont toujours résolus avec leur organisation. Les échéances de
paie utilisent le slug de l’organisation dans `entreprise_id`.

`StatistiquesPaieService` exige explicitement cet identifiant. Il n’existe pas
de mode de statistiques globales implicite.

Les bulletins et paiements sont filtrés par la relation :

```python
echeance__entreprise_id=organisation.slug
```

## Abonnements, modules et quotas

`subscriptions.services.FeatureService` décide si un module est disponible
pour une organisation.

`subscriptions.services.QuotaService` mesure :

- les membres actifs ;
- les participants ;
- les formations actives ;
- les fichiers réellement stockés.

Les contrôles de quotas doivent être exécutés avant toute création ou
activation. L’affichage d’une jauge ne remplace pas le contrôle serveur.

Les fichiers comptabilisés incluent notamment :

- logos et éléments de signature ;
- photos des participants ;
- images de formations ;
- documents des participants ;
- attestations et documents générés.

## Rôles de plateforme

La console `/platform/` est réservée aux superutilisateurs et aux utilisateurs
explicitement autorisés par les permissions de plateforme. Ces rôles gèrent :

- entreprises ;
- plans et abonnements ;
- paiements hors ligne ;
- activation ou suspension ;
- support, audits et sauvegardes.

Un rôle plateforme ne remplace pas une adhésion à une organisation pour
accéder à ses écrans métier.

## Rôles d’organisation

`MembreOrganisation` relie un utilisateur à une entreprise avec un rôle :

- propriétaire ;
- administrateur ;
- responsable formation ;
- formateur ;
- comptable ;
- lecture seule.

Les permissions Django contrôlent l’action et l’adhésion contrôle le périmètre.
Les deux vérifications sont obligatoires.

## Impersonation

Une connexion déléguée doit :

- être réservée à un opérateur plateforme autorisé ;
- avoir une durée limitée ;
- conserver l’identité de l’opérateur original ;
- être journalisée dans `PlatformAuditEvent` ;
- afficher clairement que la session est déléguée ;
- permettre une sortie immédiate ;
- ne jamais contourner l’isolation du tenant sélectionné.

## Règles de développement

Avant toute livraison :

```powershell
python manage.py audit_tenant_integrity
python manage.py check
python manage.py makemigrations --check --dry-run
python -m ruff check .
python manage.py test --parallel 4
```

Les tests doivent systématiquement créer deux organisations et vérifier qu’un
utilisateur de la première ne peut ni lire, ni modifier, ni référencer les
données de la seconde.

## Exécutions de déploiement

- GET /health/live/ : endpoint de liveness (processus actif).
- GET /health/ready/ : endpoint de readiness (DB + stockage media).
- python manage.py test_email <email> : test SMTP avant exploitation.


Le point d\u0027accès /admin/ est limité aux superutilisateurs via AdminPathSecurityMiddleware. Les comptes avec is_superuser=False reçoivent une réponse 403.

