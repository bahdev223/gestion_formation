from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DocumentIndexView(LoginRequiredMixin, TemplateView):
    template_name = "documents/index.html"

