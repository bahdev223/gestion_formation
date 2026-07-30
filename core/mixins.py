class UserAuditMixin:
    pass


class HtmxModalFormMixin:
    modal_title = "Nouvelle saisie"
    modal_eyebrow = "Gestion"
    submit_label = "Enregistrer"
    full_width_fields = ""

    def is_htmx(self):
        return self.request.headers.get("HX-Request") == "true"

    def get_template_names(self):
        if self.is_htmx():
            return ["components/modal_form.html"]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "modal_title": self.modal_title,
                "modal_eyebrow": self.modal_eyebrow,
                "submit_label": self.submit_label,
                "full_width_fields": self.full_width_fields,
            }
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.is_htmx():
            response.status_code = 204
            response["HX-Redirect"] = self.get_success_url()
        return response


class OrganisationScopedMixin:
    organisation_field = "organisation"
    tenant_success_view_name = None

    def get_current_organisation(self):
        from organisations.utils import require_request_organisation

        return require_request_organisation(self.request)

    def get_queryset(self):
        qs = super().get_queryset()
        organisation = self.get_current_organisation()
        if hasattr(qs.model, self.organisation_field):
            return qs.filter(**{self.organisation_field: organisation})
        return qs

    def form_valid(self, form):
        organisation = self.get_current_organisation()
        if hasattr(form.instance, self.organisation_field):
            form.instance.organisation = organisation
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organisation"] = self.get_current_organisation()
        return kwargs

    def get_success_url(self):
        if self.tenant_success_view_name:
            from organisations.utils import tenant_reverse

            return tenant_reverse(self.request, self.tenant_success_view_name)
        return super().get_success_url()


def organisation_lookup_for(model, field="organisation"):
    """Determine par quel chemin filtrer un modele sur son organisation.

    Tous les modeles ne portent pas un champ organisation : certains ne sont
    rattaches au tenant que par une relation (un mouvement appartient a un
    compte, qui appartient a une organisation). Leve ImproperlyConfigured
    plutot que de renvoyer None : un chemin introuvable doit casser
    bruyamment, jamais produire un queryset non filtre.
    """
    from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured

    if hasattr(model, field):
        return field

    for relation in (
        "compte",
        "source",
        "inscription",
        "ecriture",
        "immobilisation",
        "exercice",
    ):
        try:
            candidate = model._meta.get_field(relation)
        except FieldDoesNotExist:
            continue
        if candidate.is_relation and hasattr(
            candidate.related_model, field
        ):
            return f"{relation}__{field}"

    raise ImproperlyConfigured(
        f"{model.__name__} n'expose aucun chemin vers une organisation. "
        "Declarez organisation_lookup explicitement sur la vue : sans "
        "chemin d'isolation, le queryset exposerait tous les tenants."
    )


class OrganisationScopedViewSetMixin:
    """Isolation tenant pour les ViewSets DRF.

    Filtre le queryset, force l'organisation a la creation quand le modele
    porte le champ, et fournit scoped_object() pour resoudre un identifiant
    venu du client sans jamais sortir de l'organisation courante.

    Les modeles sans champ organisation sont filtres par relation. Si aucun
    chemin n'est trouvable, le mixin leve une erreur au lieu de laisser
    passer un queryset global.
    """

    organisation_field = "organisation"
    organisation_lookup = None

    def get_organisation(self):
        from organisations.utils import require_request_organisation

        return require_request_organisation(self.request)

    def get_organisation_lookup(self, model):
        if self.organisation_lookup:
            return self.organisation_lookup
        return organisation_lookup_for(model, self.organisation_field)

    def get_queryset(self):
        qs = super().get_queryset()
        lookup = self.get_organisation_lookup(qs.model)
        return qs.filter(**{lookup: self.get_organisation()})

    def perform_create(self, serializer):
        model = serializer.Meta.model
        if hasattr(model, self.organisation_field):
            serializer.save(
                **{self.organisation_field: self.get_organisation()}
            )
        else:
            serializer.save()

    def scoped_object(self, model, pk, field="pk"):
        """Resout un objet appartenant obligatoirement a l'organisation courante.

        A utiliser pour tout identifiant fourni dans le corps de la requete ou
        la query string : sans ce filtre, un client peut designer l'objet d'un
        autre tenant.
        """
        from django.shortcuts import get_object_or_404

        if pk in (None, ""):
            return None
        lookup = self.get_organisation_lookup(model)
        return get_object_or_404(
            model, **{field: pk, lookup: self.get_organisation()}
        )
