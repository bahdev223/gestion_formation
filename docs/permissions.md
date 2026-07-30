# Rôles et permissions

Les rôles applicatifs sont associés automatiquement aux groupes Django :

- **Administrateur** : accès complet ;
- **Responsable formation** : catalogue, apprenants, inscriptions, paiements,
  présences et documents ;
- **Formateur** : consultation pédagogique et saisie des présences ;
- **Comptable** : paiements, trésorerie, comptabilité et documents financiers ;
- **Responsable RH** : personnel et paie ;
- **Caissier** : consultation des inscriptions, encaissements, reçus et comptes.

La commande suivante recrée les groupes et réapplique les permissions :

```powershell
python manage.py sync_roles
```
