import pytest
from django.urls import reverse


class TestEmployeeAPI:
    def test_create_employee(self, client, db):
        response = client.post(reverse("rh:employee-create"), {
            "first_name": "Jean", "last_name": "Dupont",
        }, content_type="application/json")
        assert response.status_code == 201
        assert response.data["matricule"].startswith("EMP-")

    def test_list_employees(self, client, db):
        response = client.get(reverse("rh:employee-list"))
        assert response.status_code == 200

    def test_get_employee_not_found(self, client, db):
        response = client.get(reverse("rh:employee-detail", args=[999]))
        assert response.status_code == 404
