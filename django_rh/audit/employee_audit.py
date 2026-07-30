from django_rh.models import EmployeeAuditLog


def log_audit(employee, action, performed_by=None, details=None, request=None):
    EmployeeAuditLog.objects.create(
        employee=employee, action=action, details=details or {},
        performed_by=performed_by,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )
