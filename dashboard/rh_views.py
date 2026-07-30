from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views.generic import CreateView, ListView

from django_rh.models import Department, Employee, Position
from django_rh.services import EmployeeService
from organisations.utils import require_request_organisation, tenant_reverse

from .rh_forms import DepartmentForm, EmployeeCreateForm


@login_required
@permission_required("rh.view_employee", raise_exception=True)
def rh_dashboard(request, **kwargs):
    organisation = require_request_organisation(request)
    employees = Employee.objects.select_related("department", "position").filter(
        organisation=organisation
    )
    departments = Department.objects.filter(organisation=organisation)
    positions = Position.objects.filter(organisation=organisation)
    active_employees = employees.filter(status=Employee.Status.ACTIVE)
    salary_mass = (
        active_employees.aggregate(total=Sum("salaire_mensuel"))["total"] or 0
    )
    context = {
        "employees_count": employees.count(),
        "active_count": active_employees.count(),
        "recruited_count": employees.filter(
            status=Employee.Status.RECRUITED
        ).count(),
        "suspended_count": employees.filter(
            status=Employee.Status.SUSPENDED
        ).count(),
        "departments_count": departments.count(),
        "positions_count": positions.count(),
        "salary_mass": salary_mass,
        "recent_employees": employees.order_by("-created_at")[:6],
    }
    return render(request, "django_rh/dashboard.html", context)


@login_required
@permission_required("rh.add_employee", raise_exception=True)
def rh_employee_create(request, **kwargs):
    organisation = require_request_organisation(request)
    form = EmployeeCreateForm(request.POST or None, organisation=organisation)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        service = EmployeeService()
        employee = service.create(
            first_name=data["first_name"],
            last_name=data["last_name"],
            sex=data["sex"],
            birth_date=data["birth_date"],
            phone=data["phone"],
            email=data["email"],
            department_id=data["department"].pk if data["department"] else None,
            position_id=data["position"].pk if data["position"] else None,
            contract_type=data["contract_type"],
            created_by_id=request.user.pk,
            organisation=organisation,
        )
        employee.salaire_mensuel = data["salaire_mensuel"]
        employee.save(update_fields=["salaire_mensuel"])
        if data["activate_now"]:
            service.hire(employee.pk, performed_by_id=request.user.pk)
        messages.success(
            request,
            f"L’employé {employee.first_name} {employee.last_name} a été créé.",
        )
        destination = tenant_reverse(request, "dashboard:payroll-employees")
        response = redirect(destination)
        if request.headers.get("HX-Request") == "true":
            response.status_code = 204
            response["HX-Redirect"] = destination
        return response
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "components/modal_form.html",
            {
                "form": form,
                "modal_title": "Nouvel employé",
                "modal_eyebrow": "Ressources humaines",
                "submit_label": "Enregistrer l’employé",
                "full_width_fields": "activate_now",
            },
        )
    return render(request, "django_rh/employee_form.html", {"form": form})


class DepartmentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Department
    template_name = "django_rh/department_list.html"
    context_object_name = "departments"
    permission_required = "rh.view_department"

    def get_queryset(self):
        organisation = require_request_organisation(self.request)
        return (
            Department.objects.select_related("manager")
            .filter(organisation=organisation)
            .order_by("name")
        )


class DepartmentCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = Department
    form_class = DepartmentForm
    template_name = "django_rh/department_form.html"
    permission_required = "rh.add_department"
    def get_success_url(self):
        return tenant_reverse(self.request, "dashboard:rh-department-list")
    success_message = "Le département a été créé avec succès."

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["django_rh/partials/department_form.html"]
        return ["django_rh/department_form.html"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organisation"] = require_request_organisation(self.request)
        return kwargs

    def form_valid(self, form):
        form.instance.organisation = require_request_organisation(self.request)
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            response = render(
                self.request,
                "django_rh/partials/department_success.html",
                {"department": self.object},
            )
            response["HX-Trigger"] = "departmentCreated"
            return response
        return super().form_valid(form)
