from django.contrib import admin
from django_rh.models import Employee, Department, Position, EmployeeHistory, EmployeeAuditLog
from django_rh.services import EmployeeService


class EmployeeHistoryInline(admin.TabularInline):
    model = EmployeeHistory
    extra = 0
    readonly_fields = ["action", "old_value", "new_value", "performed_by", "performed_at", "reason"]
    can_delete = False


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["matricule", "first_name", "last_name", "status", "contract_type", "department", "hire_date"]
    list_filter = ["status", "contract_type", "department"]
    search_fields = ["matricule", "first_name", "last_name", "email"]
    readonly_fields = ["matricule"]
    inlines = [EmployeeHistoryInline]
    actions = ["hire_employees", "suspend_employees", "terminate_employees"]

    def hire_employees(self, request, queryset):
        svc = EmployeeService()
        for emp in queryset.filter(status="recruited"):
            svc.hire(emp.id, performed_by_id=request.user.id)
        self.message_user(request, f"{queryset.count()} employé(s) embauché(s).")
    hire_employees.short_description = "Embaucher la sélection"

    def suspend_employees(self, request, queryset):
        svc = EmployeeService()
        for emp in queryset.filter(status="active"):
            svc.suspend(emp.id, performed_by_id=request.user.id)
        self.message_user(request, f"{queryset.count()} employé(s) suspendu(s).")
    suspend_employees.short_description = "Suspendre la sélection"

    def terminate_employees(self, request, queryset):
        svc = EmployeeService()
        for emp in queryset.filter(status__in=["active", "suspended"]):
            svc.terminate(emp.id, performed_by_id=request.user.id)
        self.message_user(request, f"{queryset.count()} employé(s) terminé(s).")
    terminate_employees.short_description = "Terminer la sélection"


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "manager"]
    search_fields = ["code", "name"]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "department"]
    list_filter = ["department"]
    search_fields = ["code", "title"]


@admin.register(EmployeeHistory)
class EmployeeHistoryAdmin(admin.ModelAdmin):
    list_display = ["employee", "action", "performed_by", "performed_at"]
    readonly_fields = ["employee", "action", "old_value", "new_value", "performed_by", "performed_at", "reason"]


@admin.register(EmployeeAuditLog)
class EmployeeAuditLogAdmin(admin.ModelAdmin):
    list_display = ["employee", "action", "performed_by", "performed_at"]
    readonly_fields = ["employee", "action", "details", "performed_by", "performed_at"]
