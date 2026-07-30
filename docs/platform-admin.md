# Console SahelTech Platform Admin

La console `/platform/` administre la plateforme SaaS. Elle est séparée des
espaces clients `/o/<slug>/`.

## Accès

Un superutilisateur dispose automatiquement du contrôle complet. Les autres
membres de l'équipe SahelTech doivent avoir `is_staff=True` et un
`PlatformStaffProfile` actif.

Rôles disponibles :

- `SUPER_ADMIN` : contrôle complet ;
- `SUPPORT` : organisations, tickets et connexion déléguée ;
- `FINANCE` : plans, abonnements et facturation ;
- `OPS` : monitoring, maintenance et sauvegardes ;
- `DEVELOPPEUR` : diagnostics et feature flags ;
- `LECTURE` : consultation des données autorisées.

## Modules

- tableau de bord SaaS : clients, essais, MRR, ARR, churn et incidents ;
- organisations : quotas, membres, statut, plan et actions administratives ;
- abonnements et facturation : paiements, factures et coupons ;
- support : tickets, priorités, responsables, échanges et notes internes ;
- audit global : connexions, actions sensibles, IP et entreprises ;
- monitoring : CPU, RAM, disque, base, erreurs et tâches ;
- feature flags : activation globale, progressive ou ciblée ;
- maintenance : fenêtres planifiées, blocage des inscriptions et annonces ;
- sauvegardes : archive ZIP logique par entreprise et téléchargement ;
- statistiques : croissance des clients et revenus par plan.

## Initialisation

```bash
python manage.py migrate
python manage.py seed_platform_admin
```

La commande associe le superutilisateur `admin` au rôle `SUPER_ADMIN` lorsqu'il
existe et crée les feature flags de départ.

## Sécurité

Les administrateurs d'entreprise n'ont pas accès à `/platform/`. Une connexion
déléguée vers une entreprise est journalisée et affiche une bannière permanente
permettant de revenir à la console SahelTech.
