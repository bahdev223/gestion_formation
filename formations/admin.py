from django.contrib import admin

from .models import CategorieFormation, Formation, Seance, SessionFormation

admin.site.register(CategorieFormation)
admin.site.register(Formation)
admin.site.register(SessionFormation)
admin.site.register(Seance)

