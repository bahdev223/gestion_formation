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
        organisation = getattr(self.request, "organisation", None)
        if organisation is not None:
            return organisation
        from organisations.models import Organisation

        return Organisation.objects.filter(slug="balys-group").first()

    def get_queryset(self):
        qs = super().get_queryset()
        organisation = self.get_current_organisation()
        if organisation is not None and hasattr(qs.model, self.organisation_field):
            return qs.filter(**{self.organisation_field: organisation})
        return qs

    def form_valid(self, form):
        organisation = self.get_current_organisation()
        if organisation is not None and hasattr(form.instance, self.organisation_field):
            form.instance.organisation = organisation
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        organisation = self.get_current_organisation()
        if organisation is not None:
            kwargs["organisation"] = organisation
        return kwargs

    def get_success_url(self):
        if self.tenant_success_view_name:
            from organisations.utils import tenant_reverse

            return tenant_reverse(self.request, self.tenant_success_view_name)
        return super().get_success_url()
