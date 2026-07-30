from datetime import date
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render

from django_paie.models import EcheanceSalariale, PaiementSalarial
from django_paie.services import ModeSimpleService
from django_paie.utils import extraire_mois_annee
from django_rh.models import Employee
from organisations.utils import require_request_organisation, tenant_reverse


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
        self.organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        dues = (
            EcheanceSalariale.objects.filter(montant_net__gt=F("montant_paye"))
            .select_related("employe_content_type")
            .order_by("-annee", "-mois", "employe_object_id")
        )
        if self.organisation is not None:
            dues = dues.filter(entreprise_id=self.organisation.slug)
        self.fields["echeance"].queryset = dues

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
def payroll_payment_create(request, **kwargs):
    organisation = require_request_organisation(request)
    form = SalaryPaymentForm(request.POST or None, organisation=organisation)
    if request.method == "POST" and form.is_valid():
        paiement = ModeSimpleService(
            entreprise_id=organisation.slug
        ).enregistrer_paiement(
            echeance_id=form.cleaned_data["echeance"].pk,
            montant=form.cleaned_data["montant"],
            date_paiement=form.cleaned_data["date_paiement"],
            type_paiement=form.cleaned_data.get("type_paiement") or "PAIEMENT",
            notes=form.cleaned_data.get("notes", ""),
        )
        messages.success(request, "Le paiement salarial a été enregistré.")
        return redirect(
            tenant_reverse(
                request,
                "django_paie:paiement-bulletin",
                kwargs={"pk": paiement.pk},
            )
        )
    return render(request, "django_paie/paiement_form.html", {"form": form})


@login_required
@permission_required("rh.change_employee", raise_exception=True)
def payroll_employees(request, **kwargs):
    organisation = require_request_organisation(request)
    users = (
        Employee.objects.filter(organisation=organisation)
        .exclude(status=Employee.Status.ARCHIVED)
        .order_by("last_name", "first_name")
    )
    return render(
        request,
        "django_paie/employees.html",
        {"payroll_users": users},
    )


@login_required
@permission_required("rh.change_employee", raise_exception=True)
def payroll_employee_salary_update(request, user_id, **kwargs):
    if request.method != "POST":
        return redirect(tenant_reverse(request, "dashboard:payroll-employees"))

    organisation = require_request_organisation(request)
    employee = get_object_or_404(
        Employee.objects.filter(organisation=organisation), pk=user_id
    )
    raw_salary = request.POST.get("salaire_mensuel", "").strip()
    try:
        salary = Decimal(raw_salary) if raw_salary else None
        if salary is not None and salary < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        messages.error(request, "Le salaire mensuel saisi est invalide.")
        return redirect(tenant_reverse(request, "dashboard:payroll-employees"))

    employee.salaire_mensuel = salary
    employee.save(update_fields=["salaire_mensuel"])
    messages.success(request, f"Salaire de {employee} enregistré.")
    return redirect(tenant_reverse(request, "dashboard:payroll-employees"))


@login_required
@permission_required("django_paie.add_echeancesalariale", raise_exception=True)
def payroll_generate(request, **kwargs):
    if request.method != "POST":
        return redirect(tenant_reverse(request, "django_paie:dashboard"))

    raw_period = (request.POST.get("periode") or "").strip()
    if not raw_period:
        period = f"{date.today().month:02d}/{date.today().year}"
    elif len(raw_period) == 7 and raw_period[4] == "-":
        year, month = raw_period.split("-", maxsplit=1)
        period = f"{month}/{year}"
    else:
        period = raw_period

    try:
        month, year = extraire_mois_annee(period)
        period = f"{month:02d}/{year}"
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(tenant_reverse(request, "django_paie:dashboard"))

    organisation = require_request_organisation(request)
    employees = Employee.objects.filter(
        status=Employee.Status.ACTIVE,
        salaire_mensuel__isnull=False,
        salaire_mensuel__gt=0,
        organisation=organisation,
    )
    service = ModeSimpleService(entreprise_id=organisation.slug)
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
    return redirect(tenant_reverse(request, "django_paie:echeance-list"))
