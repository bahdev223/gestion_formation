from django_rh.domain.entities.employee import EmployeeEntity
from django_rh.domain.events.employee_events import EmployeeEvent, EmployeeEvents
from django_rh.domain.exceptions.rh_exceptions import EmployeeNotFoundError
from django_rh.domain.services.employee_domain_service import EmployeeDomainService
from django_rh.models import Employee, EmployeeAuditLog, EmployeeHistory
from django_rh.settings import get_setting
from django_rh.utils.numbering import generate_matricule


class EmployeeService:
    def __init__(self):
        self.domain = EmployeeDomainService()

    def create(self, first_name: str, last_name: str, sex: str = "M",
               birth_date=None, phone: str = "", email: str = "",
               department_id: int | None = None, position_id: int | None = None,
               contract_type: str = "CDI", created_by_id: int | None = None,
               organisation=None) -> Employee:
        entity = self.domain.create_employee(first_name, last_name, sex, birth_date, phone, email, department_id, position_id, contract_type)
        employee = Employee.objects.create(
            matricule=generate_matricule(),
            first_name=entity.first_name, last_name=entity.last_name,
            sex=entity.sex, birth_date=entity.birth_date,
            phone=entity.phone, email=entity.email,
            status=entity.status, contract_type=entity.contract_type,
            department_id=entity.department_id, position_id=entity.position_id,
            created_by_id=created_by_id,
            organisation=organisation,
        )
        self._record_history(employee, "created", {}, {"id": employee.id})
        self._record_audit(employee, EmployeeAuditLog.Action.CREATE, created_by_id)
        self._publish_event(EmployeeEvents.CREATED, employee, {})
        return employee

    def hire(self, employee_id: int, performed_by_id: int | None = None) -> Employee:
        employee = self._get_or_raise(employee_id)
        entity = self._to_entity(employee)
        self.domain.hire(entity)
        employee.status = entity.status
        employee.hire_date = entity.hire_date
        employee.save(update_fields=["status", "hire_date"])
        self._record_history(employee, "hired", {}, {"status": "active"})
        self._record_audit(employee, EmployeeAuditLog.Action.HIRE, performed_by_id)
        self._publish_event(EmployeeEvents.HIRED, employee, {})
        return employee

    def suspend(self, employee_id: int, reason: str = "", performed_by_id: int | None = None) -> Employee:
        employee = self._get_or_raise(employee_id)
        entity = self._to_entity(employee)
        self.domain.suspend(entity)
        employee.status = entity.status
        employee.save(update_fields=["status"])
        self._record_history(employee, "suspended", {}, {"status": "suspended"}, performed_by_id, reason)
        self._record_audit(employee, EmployeeAuditLog.Action.SUSPEND, performed_by_id)
        self._publish_event(EmployeeEvents.SUSPENDED, employee, {"reason": reason})
        return employee

    def terminate(self, employee_id: int, reason: str = "", performed_by_id: int | None = None) -> Employee:
        employee = self._get_or_raise(employee_id)
        entity = self._to_entity(employee)
        self.domain.terminate(entity)
        employee.status = entity.status
        employee.termination_date = entity.termination_date
        employee.save(update_fields=["status", "termination_date"])
        self._record_history(employee, "terminated", {}, {"status": "terminated"}, performed_by_id, reason)
        self._record_audit(employee, EmployeeAuditLog.Action.TERMINATE, performed_by_id)
        self._publish_event(EmployeeEvents.TERMINATED, employee, {"reason": reason})
        return employee

    def _get_or_raise(self, employee_id: int) -> Employee:
        try:
            return Employee.objects.select_related("department", "position").get(id=employee_id)
        except Employee.DoesNotExist:
            raise EmployeeNotFoundError(employee_id)

    def _to_entity(self, employee: Employee) -> EmployeeEntity:
        return EmployeeEntity(
            id=employee.id, matricule=employee.matricule,
            first_name=employee.first_name, last_name=employee.last_name,
            sex=employee.sex, birth_date=employee.birth_date,
            phone=employee.phone, email=employee.email,
            status=employee.status,
            department_id=employee.department_id, position_id=employee.position_id,
            contract_type=employee.contract_type,
            hire_date=employee.hire_date, termination_date=employee.termination_date,
            created_by_id=employee.created_by_id,
        )

    def _record_history(self, employee, action, old, new, performed_by_id=None, reason=""):
        if not get_setting("ENABLE_HISTORY"):
            return
        EmployeeHistory.objects.create(
            employee=employee, action=action, old_value=old, new_value=new,
            performed_by_id=performed_by_id, reason=reason,
            organisation=employee.organisation,
        )

    def _record_audit(self, employee, action, performed_by_id=None):
        if not get_setting("ENABLE_AUDIT"):
            return
        EmployeeAuditLog.objects.create(
            employee=employee,
            action=action,
            performed_by_id=performed_by_id,
            organisation=employee.organisation,
        )

    def _publish_event(self, event_name, employee, extra=None):
        from django_rh.signals.employee_signals import employee_event
        data = {"employee_id": employee.id, "matricule": employee.matricule, "status": employee.status, **(extra or {})}
        employee_event.send(sender=self.__class__, event=EmployeeEvent(name=event_name, employee_id=employee.id, data=data))
