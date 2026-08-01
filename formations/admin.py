from django.contrib import admin

from .models import CategorieFormation, Formation, Seance, SessionAccessLink, SessionFormation

admin.site.register(CategorieFormation)
admin.site.register(Formation)
admin.site.register(SessionFormation)
admin.site.register(SessionAccessLink)
admin.site.register(Seance)
