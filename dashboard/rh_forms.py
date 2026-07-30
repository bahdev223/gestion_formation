from django import forms

from django_rh.models import Department, Employee, Position


class EmployeeCreateForm(forms.Form):
    first_name = forms.CharField(label="Prénom", max_length=100)
    last_name = forms.CharField(label="Nom", max_length=100)
    sex = forms.ChoiceField(label="Sexe", choices=Employee.Sex.choices)
    birth_date = forms.DateField(
        label="Date de naissance",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    phone = forms.CharField(label="Téléphone", max_length=30, required=False)
    email = forms.EmailField(label="Email", required=False)
    department = forms.ModelChoiceField(
        label="Département",
        queryset=Department.objects.none(),
        required=False,
    )
    position = forms.ModelChoiceField(
        label="Poste",
        queryset=Position.objects.none(),
        required=False,
    )
    contract_type = forms.ChoiceField(
        label="Type de contrat",
        choices=Employee.ContractType.choices,
    )
    salaire_mensuel = forms.DecimalField(
        label="Salaire mensuel (FCFA)",
        max_digits=12,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    activate_now = forms.BooleanField(
        label="Embaucher et activer immédiatement",
        required=False,
        initial=True,
    )

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        departments = Department.objects.order_by("name")
        positions = Position.objects.select_related(
            "department"
        ).order_by("title")
        if self.organisation is not None:
            departments = departments.filter(organisation=self.organisation)
            positions = positions.filter(organisation=self.organisation)
        self.fields["department"].queryset = departments
        self.fields["position"].queryset = positions
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-md border border-slate-300 bg-white px-3.5 py-3 "
                "text-sm outline-none focus:border-blue-600 focus:ring-2 "
                "focus:ring-blue-100"
            )
        self.fields["activate_now"].widget.attrs["class"] = (
            "h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
        )


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["code", "name", "description", "manager"]
        labels = {
            "code": "Code du département",
            "name": "Nom du département",
            "description": "Description",
            "manager": "Responsable",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        managers = Employee.objects.filter(
            status=Employee.Status.ACTIVE
        ).order_by("last_name", "first_name")
        if self.organisation is not None:
            managers = managers.filter(organisation=self.organisation)
        self.fields["manager"].queryset = managers
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-md border border-slate-300 bg-white px-3.5 py-3 "
                "text-sm outline-none focus:border-blue-600 focus:ring-2 "
                "focus:ring-blue-100"
            )
