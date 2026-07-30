from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_rh.services import EmployeeService
from django_rh.selectors import EmployeeSelector
from django_rh.models import Department, Position
from django_rh.serializers import (
    EmployeeListSerializer, EmployeeDetailSerializer,
    EmployeeCreateSerializer, DepartmentSerializer, PositionSerializer,
)
from django_rh.permissions import RHCreatePermission, RHPromotePermission, RHTerminatePermission


@api_view(["POST"])
@permission_classes([IsAuthenticated, RHCreatePermission])
def create_employee(request):
    serializer = EmployeeCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    emp = EmployeeService().create(created_by_id=request.user.id, **serializer.validated_data)
    return Response(EmployeeDetailSerializer(emp).data, status=201)


@api_view(["GET"])
def list_employees(request):
    employees = EmployeeSelector().list_employees(
        status=request.query_params.get("status"),
        department_id=request.query_params.get("department_id"),
    )
    return Response(EmployeeListSerializer(employees, many=True).data)


@api_view(["GET"])
def get_employee(request, employee_id: int):
    emp = EmployeeSelector().get_by_id(employee_id)
    if not emp:
        return Response({"error": "Employee not found"}, status=404)
    return Response(EmployeeDetailSerializer(emp).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, RHPromotePermission])
def hire_employee(request, employee_id: int):
    try:
        emp = EmployeeService().hire(employee_id, performed_by_id=request.user.id)
        return Response(EmployeeDetailSerializer(emp).data)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def suspend_employee(request, employee_id: int):
    reason = request.data.get("reason", "")
    try:
        emp = EmployeeService().suspend(employee_id, reason=reason, performed_by_id=request.user.id)
        return Response(EmployeeDetailSerializer(emp).data)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated, RHTerminatePermission])
def terminate_employee(request, employee_id: int):
    reason = request.data.get("reason", "")
    try:
        emp = EmployeeService().terminate(employee_id, reason=reason, performed_by_id=request.user.id)
        return Response(EmployeeDetailSerializer(emp).data)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET"])
def list_departments(request):
    departments = EmployeeSelector().list_departments()
    return Response(DepartmentSerializer(departments, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, RHCreatePermission])
def create_department(request):
    serializer = DepartmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    dept = Department.objects.create(**serializer.validated_data)
    return Response(DepartmentSerializer(dept).data, status=201)


@api_view(["GET"])
def list_positions(request):
    positions = EmployeeSelector().list_positions()
    return Response(PositionSerializer(positions, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, RHCreatePermission])
def create_position(request):
    serializer = PositionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pos = Position.objects.create(**serializer.validated_data)
    return Response(PositionSerializer(pos).data, status=201)


@api_view(["GET"])
def dashboard_stats(request):
    return Response(EmployeeSelector().get_dashboard_stats())
