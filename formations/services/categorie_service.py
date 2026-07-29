from django.db import transaction

from formations.models import CategorieFormation


@transaction.atomic
def create_categorie(data):
    return CategorieFormation.objects.create(**data)


@transaction.atomic
def toggle_categorie_status(categorie, is_active):
    categorie.is_active = is_active
    categorie.save(update_fields=["is_active", "updated_at"])
    return categorie

