# tests/integration/test_incident_endpoints.py
from datetime import datetime, timezone, timedelta
from src.models.models import Service, Incident
from tests.integration.test_base import TestBase

class TestIncidentsEndpoints(TestBase):
    def test_get_all_incidents_empty(self):
        """Test getting all incidents when there are none."""
        response = self.client.get("/api/v1/incidents")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_all_incidents(self):
        """Test getting all incidents."""
        # Setup test data
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incident = Incident(
            id="INC1",
            incident_number=1,
            title="Test Incident",
            status="resolved",
            urgency="high",  # Añadido campo obligatorio
            service_id="SERVICE1",
            created_at=datetime.now(timezone.utc)
        )
        self.db_session.add(service)
        self.db_session.add(incident)
        self.db_session.commit()

        response = self.client.get("/api/v1/incidents")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["id"] == "INC1"

    def test_get_incidents_by_service(self):
        """Test getting incidents grouped by service."""
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incidents = [
            Incident(
                id=f"INC{i}",
                incident_number=i,
                title=f"Test Incident {i}",
                status="resolved",
                urgency="high",  # Añadido campo obligatorio
                service_id="SERVICE1",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(2)
        ]
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        response = self.client.get("/api/v1/incidents/by-service")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["service_id"] == "SERVICE1"
        assert len(data[0]["incidents"]) == 2

    def test_get_incidents_by_status(self):
        """Test getting incidents grouped by status."""
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incidents = [
            Incident(
                id=f"INC{i}",
                incident_number=i,
                title=f"Test Incident {i}",
                status=status,
                urgency="high",  # Añadido campo obligatorio
                service_id="SERVICE1",
                created_at=datetime.now(timezone.utc)
            )
            for i, status in enumerate(["triggered", "resolved"])
        ]
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        response = self.client.get("/api/v1/incidents/by-status")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2  # dos estados diferentes
        statuses = {group["status"] for group in data}
        assert statuses == {"triggered", "resolved"}

    def test_get_incidents_by_service_status(self):
        """Test getting incidents grouped by service and status."""
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incidents = [
            Incident(
                id=f"INC{i}",
                incident_number=i,
                title=f"Test Incident {i}",
                status="triggered" if i % 2 == 0 else "resolved",
                urgency="high",  # Añadido campo obligatorio
                service_id="SERVICE1",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(2)
        ]
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        response = self.client.get("/api/v1/incidents/by-service-status")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1  # un servicio
        service_data = data[0]
        assert service_data["service_id"] == "SERVICE1"
        assert "triggered" in service_data["status_groups"]
        assert "resolved" in service_data["status_groups"]
