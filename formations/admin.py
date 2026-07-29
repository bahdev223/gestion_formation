from django.contrib import admin

from .models import CategorieFormation, Formation, SessionFormation, Seance

admin.site.register(CategorieFormation)
admin.site.register(Formation)
admin.site.register(SessionFormation)
admin.site.register(Seance)

