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
