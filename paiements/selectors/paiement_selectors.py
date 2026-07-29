from paiements.models import Paiement


def get_payments_between_dates(start_date, end_date):
    return Paiement.objects.filter(date_paiement__date__range=(start_date, end_date))

