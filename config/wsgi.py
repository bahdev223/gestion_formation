import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
application = get_wsgi_application()


def _servir_les_medias(app):
    """Fait servir MEDIA_URL par WhiteNoise.

    Le middleware WhiteNoise ne sert que les fichiers statiques. Les fichiers
    envoyes par les utilisateurs (couvertures de formation, logos, photos)
    demandent une declaration explicite, sinon /media/... renvoie 404 en
    production alors que le fichier existe bien sur le volume.

    autorefresh est indispensable ici : par defaut WhiteNoise construit son
    index au demarrage, ce qui ferait echouer toute image envoyee apres le
    lancement du conteneur.
    """
    from django.conf import settings

    media_root = getattr(settings, "MEDIA_ROOT", None)
    media_url = getattr(settings, "MEDIA_URL", None)
    if not media_root or not media_url:
        return app

    try:
        from whitenoise import WhiteNoise
    except ImportError:
        # WhiteNoise n'est installe qu'en production.
        return app

    os.makedirs(media_root, exist_ok=True)
    enveloppe = WhiteNoise(app, autorefresh=True)
    enveloppe.add_files(str(media_root), prefix=media_url)
    return enveloppe


application = _servir_les_medias(application)
