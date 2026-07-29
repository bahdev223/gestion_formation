from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class PresenceIndexView(LoginRequiredMixin, TemplateView):
    template_name = "presences/index.html"

