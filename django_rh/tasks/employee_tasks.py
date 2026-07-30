def cleanup_archived_employees(days: int = 365):
    from datetime import timedelta
    from django.utils import timezone
    from django_rh.models import Employee
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = Employee.objects.filter(status="terminated", updated_at__lt=cutoff).delete()
    return deleted
