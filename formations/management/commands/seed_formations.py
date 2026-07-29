from decimal import Decimal

from django.core.management.base import BaseCommand

from formations.models import CategorieFormation, Formation


CATEGORIES = [
    {
        "nom": "Informatique & Bureautique",
        "description": "Compétences numériques, outils bureautiques et productivité.",
        "couleur": "#15519A",
    },
    {
        "nom": "Gestion & Entrepreneuriat",
        "description": "Pilotage d’entreprise, création d’activité et gestion de projet.",
        "couleur": "#F28B16",
    },
    {
        "nom": "Finance & Comptabilité",
        "description": "Comptabilité, trésorerie, fiscalité et contrôle financier.",
        "couleur": "#138A72",
    },
    {
        "nom": "Marketing & Communication",
        "description": "Communication professionnelle, vente et marketing digital.",
        "couleur": "#8B5CF6",
    },
    {
        "nom": "Ressources Humaines",
        "description": "Management des équipes et développement des compétences.",
        "couleur": "#DC3F31",
    },
    {
        "nom": "Développement personnel",
        "description": "Leadership, prise de parole et efficacité professionnelle.",
        "couleur": "#475467",
    },
]


FORMATIONS = [
    {
        "nom": "Maîtriser Microsoft Excel – Niveau professionnel",
        "categorie": "Informatique & Bureautique",
        "description": "Exploiter Excel pour organiser, analyser et présenter les données professionnelles.",
        "objectifs": "Créer des tableaux fiables, utiliser les fonctions essentielles et produire des tableaux de bord.",
        "programme": "Mise en forme et tableaux\nFonctions et formules\nTableaux croisés dynamiques\nGraphiques et tableaux de bord",
        "duree": 24,
        "unite_duree": Formation.UniteDuree.HEURES,
        "prix_standard": Decimal("125000"),
    },
    {
        "nom": "Pack Bureautique : Word, Excel et PowerPoint",
        "categorie": "Informatique & Bureautique",
        "description": "Parcours complet pour gagner en autonomie avec les outils Microsoft Office.",
        "objectifs": "Produire des documents, tableaux et présentations de qualité professionnelle.",
        "programme": "Word professionnel\nExcel opérationnel\nPowerPoint et présentation\nExercices pratiques",
        "duree": 5,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("175000"),
    },
    {
        "nom": "Création et gestion d’une petite entreprise",
        "categorie": "Gestion & Entrepreneuriat",
        "description": "Transformer une idée en activité structurée et économiquement viable.",
        "objectifs": "Construire un modèle économique, budgétiser le lancement et piloter l’activité.",
        "programme": "Étude de marché\nBusiness model\nPlan financier\nFormalisation\nPilotage de l’activité",
        "duree": 4,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("150000"),
    },
    {
        "nom": "Gestion de projet – Fondamentaux et outils pratiques",
        "categorie": "Gestion & Entrepreneuriat",
        "description": "Méthode opérationnelle pour planifier, exécuter et suivre un projet.",
        "objectifs": "Cadrer un projet, gérer les délais, les risques, les ressources et le reporting.",
        "programme": "Cadrage\nPlanification\nBudget et ressources\nGestion des risques\nSuivi et clôture",
        "duree": 3,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("140000"),
    },
    {
        "nom": "Comptabilité générale pour non-comptables",
        "categorie": "Finance & Comptabilité",
        "description": "Comprendre les mécanismes comptables indispensables au pilotage d’une organisation.",
        "objectifs": "Lire les états financiers et enregistrer les opérations courantes.",
        "programme": "Principes comptables\nJournal et grand livre\nBilan et compte de résultat\nTravaux pratiques",
        "duree": 5,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("190000"),
    },
    {
        "nom": "Gestion de trésorerie et maîtrise des coûts",
        "categorie": "Finance & Comptabilité",
        "description": "Anticiper les besoins de trésorerie et améliorer la rentabilité.",
        "objectifs": "Construire un plan de trésorerie, analyser les écarts et maîtriser les charges.",
        "programme": "Prévisions de trésorerie\nSuivi des encaissements\nAnalyse des coûts\nPlan d’action",
        "duree": 3,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("165000"),
    },
    {
        "nom": "Marketing digital et réseaux sociaux",
        "categorie": "Marketing & Communication",
        "description": "Développer la visibilité d’une activité avec une stratégie digitale structurée.",
        "objectifs": "Définir une ligne éditoriale, créer du contenu et mesurer les performances.",
        "programme": "Stratégie digitale\nFacebook et Instagram\nCréation de contenu\nPublicité\nIndicateurs",
        "duree": 4,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("160000"),
    },
    {
        "nom": "Techniques de vente et relation client",
        "categorie": "Marketing & Communication",
        "description": "Professionnaliser l’approche commerciale et fidéliser les clients.",
        "objectifs": "Conduire un entretien de vente, traiter les objections et conclure efficacement.",
        "programme": "Préparation commerciale\nDécouverte du besoin\nArgumentation\nObjections\nFidélisation",
        "duree": 3,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("135000"),
    },
    {
        "nom": "Gestion administrative des ressources humaines",
        "categorie": "Ressources Humaines",
        "description": "Maîtriser les processus administratifs essentiels du personnel.",
        "objectifs": "Organiser les dossiers, les contrats, les absences et le suivi administratif.",
        "programme": "Dossier salarié\nContrats\nTemps et absences\nTableaux de bord RH\nArchivage",
        "duree": 4,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("170000"),
    },
    {
        "nom": "Management d’équipe et leadership",
        "categorie": "Ressources Humaines",
        "description": "Mobiliser une équipe, déléguer efficacement et gérer les situations difficiles.",
        "objectifs": "Adapter son management, fixer des objectifs et renforcer la performance collective.",
        "programme": "Styles de management\nObjectifs et délégation\nMotivation\nFeedback\nGestion des conflits",
        "duree": 3,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("175000"),
    },
    {
        "nom": "Prise de parole en public",
        "categorie": "Développement personnel",
        "description": "Présenter ses idées avec clarté, assurance et impact.",
        "objectifs": "Structurer une intervention, gérer le stress et captiver un auditoire.",
        "programme": "Préparation du message\nVoix et posture\nGestion du trac\nInteraction avec le public",
        "duree": 2,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("95000"),
    },
    {
        "nom": "Gestion du temps et efficacité professionnelle",
        "categorie": "Développement personnel",
        "description": "Mieux prioriser les activités et réduire les pertes de temps.",
        "objectifs": "Planifier efficacement, gérer les urgences et améliorer son organisation.",
        "programme": "Diagnostic personnel\nPriorisation\nPlanification\nGestion des interruptions\nPlan de progrès",
        "duree": 2,
        "unite_duree": Formation.UniteDuree.JOURS,
        "prix_standard": Decimal("90000"),
    },
]


class Command(BaseCommand):
    help = "Crée le catalogue initial de catégories et formations BALY'S GROUP."

    def handle(self, *args, **options):
        categories = {}
        categories_creees = 0
        formations_creees = 0

        for data in CATEGORIES:
            categorie, created = CategorieFormation.objects.update_or_create(
                nom=data["nom"],
                defaults={
                    "description": data["description"],
                    "couleur": data["couleur"],
                    "is_active": True,
                },
            )
            categories[categorie.nom] = categorie
            categories_creees += int(created)

        for data in FORMATIONS:
            categorie_nom = data["categorie"]
            defaults = {
                key: value for key, value in data.items() if key not in {"nom", "categorie"}
            }
            defaults["categorie"] = categories[categorie_nom]
            defaults["statut"] = Formation.Statut.ACTIVE
            _, created = Formation.objects.update_or_create(
                nom=data["nom"],
                defaults=defaults,
            )
            formations_creees += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed terminé : {categories_creees} catégorie(s) et "
                f"{formations_creees} formation(s) créées."
            )
        )
