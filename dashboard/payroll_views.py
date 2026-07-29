from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django import forms
from django.db.models import F
from django.shortcuts import redirect, render

from django_paie.models import EcheanceSalariale, PaiementSalarial
from django_paie.services import ModeSimpleService
from django_rh.models import Employee


class SalaryDueChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, due):
        employee = due.employe
        employee_name = (
            f"{employee.first_name} {employee.last_name}"
            if employee
            else f"Employé #{due.employe_object_id}"
        )
        return (
            f"{employee_name} · {due.periode} · "
            f"reste {due.reste_a_payer:,.0f} FCFA"
        )


class SalaryPaymentForm(forms.Form):
    echeance = SalaryDueChoiceField(
        label="Employé et échéance",
        queryset=EcheanceSalariale.objects.none(),
    )
    montant = forms.DecimalField(
        label="Montant payé",
        min_value=1,
        max_digits=14,
        decimal_places=0,
    )
    type_paiement = forms.ChoiceField(
        label="Type de paiement",
        required=False,
        choices=[("", "Paiement salarial")] + list(PaiementSalarial.TYPE_CHOICES),
    )
    date_paiement = forms.DateField(
        label="Date du paiement",
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["echeance"].queryset = (
            EcheanceSalariale.objects.filter(montant_net__gt=F("montant_paye"))
            .select_related("employe_content_type")
            .order_by("-annee", "-mois", "employe_object_id")
        )

    def clean(self):
        cleaned = super().clean()
        due = cleaned.get("echeance")
        amount = cleaned.get("montant")
        if due and amount and amount > due.reste_a_payer:
            self.add_error(
                "montant",
                f"Le montant dépasse le reste à payer ({due.reste_a_payer:,.0f} FCFA).",
            )
        return cleaned


@login_required
@permission_required("django_paie.add_paiementsalarial", raise_exception=True)
def payroll_payment_create(request):
    form = SalaryPaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ModeSimpleService().enregistrer_paiement(
            echeance_id=form.cleaned_data["echeance"].pk,
            montant=form.cleaned_data["montant"],
            date_paiement=form.cleaned_data["date_paiement"],
            type_paiement=form.cleaned_data.get("type_paiement") or "PAIEMENT",
            notes=form.cleaned_data.get("notes", ""),
        )
        messages.success(request, "Le paiement salarial a été enregistré.")
        return redirect("django_paie:paiement-list")
    return render(request, "django_paie/paiement_form.html", {"form": form})


@login_required
@permission_required("rh.change_employee", raise_exception=True)
def payroll_employees(request):
    users = Employee.objects.exclude(status=Employee.Status.ARCHIVED).order_by(
        "last_name", "first_name"
    )
    return render(
        request,
        "django_paie/employees.html",
        {"payroll_users": users},
    )


@login_required
@permission_required("rh.change_employee", raise_exception=True)
def payroll_employee_salary_update(request, user_id):
    if request.method != "POST":
        return redirect("dashboard:payroll-employees")

    employee = Employee.objects.get(pk=user_id)
    raw_salary = request.POST.get("salaire_mensuel", "").strip()
    try:
        salary = Decimal(raw_salary) if raw_salary else None
        if salary is not None and salary < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        messages.error(request, "Le salaire mensuel saisi est invalide.")
        return redirect("dashboard:payroll-employees")

    employee.salaire_mensuel = salary
    employee.save(update_fields=["salaire_mensuel"])
    messages.success(request, f"Salaire de {employee} enregistré.")
    return redirect("dashboard:payroll-employees")


@login_required
@permission_required("django_paie.add_echeancesalariale", raise_exception=True)
def payroll_generate(request):
    if request.method != "POST":
        return redirect("django_paie:dashboard")

    period = request.POST.get("periode") or f"{date.today().month:02d}/{date.today().year}"
    employees = Employee.objects.filter(
        status=Employee.Status.ACTIVE,
        salaire_mensuel__isnull=False,
        salaire_mensuel__gt=0,
    )
    service = ModeSimpleService()
    generated = 0
    errors = []

    for employee in employees:
        try:
            service.creer_echeance(
                employee,
                period,
                employee.salaire_mensuel,
            )
            generated += 1
        except (ValueError, TypeError) as exc:
            errors.append(f"{employee}: {exc}")

    if generated:
        messages.success(
            request,
            f"{generated} échéance(s) générée(s) ou actualisée(s) pour {period}.",
        )
    elif not employees:
        messages.warning(
            request,
            "Aucun employé actif ne possède encore de salaire mensuel.",
        )
    for error in errors[:5]:
        messages.error(request, error)
    return redirect("django_paie:echeance-list")
