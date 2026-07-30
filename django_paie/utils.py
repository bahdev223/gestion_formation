from datetime import date, datetime, timedelta
from calendar import monthrange


def extraire_mois_annee(periode):
    try:
        mois, annee = str(periode).strip().split("/")
        mois, annee = int(mois), int(annee)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(
            f"Période invalide : {periode}. Format attendu : MM/AAAA"
        ) from exc

    if not 1 <= mois <= 12 or not 2000 <= annee <= 2100:
        raise ValueError(
            f"Période invalide : {periode}. "
            "Le mois doit être compris entre 01 et 12 et l'année entre 2000 et 2100."
        )
    return mois, annee


def generer_periodes_annee(annee):
    return [f"{m:02d}/{annee}" for m in range(1, 13)]


def periode_en_cours():
    today = date.today()
    return f"{today.month:02d}/{today.year}"


def mois_precedent():
    today = date.today()
    m = today.month - 1
    y = today.year
    if m == 0:
        m = 12
        y -= 1
    return f"{m:02d}/{y}"


def duree_mois(mois, annee):
    _, nb_jours = monthrange(annee, mois)
    return nb_jours


def est_periode_valide(periode):
    try:
        mois, annee = periode.split("/")
        m, a = int(mois), int(annee)
        return 1 <= m <= 12 and a > 1900
    except (ValueError, AttributeError):
        return False


def formater_montant(montant, devise="XOF"):
    return f"{int(montant):,} {devise}".replace(",", " ")
