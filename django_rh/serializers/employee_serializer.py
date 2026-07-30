from rest_framework import serializers
from django_rh.models import Employee, Department, Position


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "code", "name", "description", "manager"]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "code", "title", "description", "department"]


class EmployeeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            "id", "matricule", "first_name", "last_name", "sex",
            "status", "contract_type", "department", "position",
            "hire_date", "created_at",
        ]


class EmployeeDetailSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    position = PositionSerializer(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id", "matricule", "first_name", "last_name", "sex",
            "birth_date", "phone", "email", "status", "contract_type",
            "department", "position", "hire_date", "termination_date",
            "created_by", "created_at", "updated_at",
        ]


class EmployeeCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    sex = serializers.ChoiceField(choices=["M", "F"], default="M")
    birth_date = serializers.DateField(required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    department_id = serializers.IntegerField(required=False, allow_null=True)
    position_id = serializers.IntegerField(required=False, allow_null=True)
    contract_type = serializers.ChoiceField(choices=["CDI", "CDD", "internship", "consultant"], default="CDI")
