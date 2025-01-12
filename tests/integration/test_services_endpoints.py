# tests/integration/test_service_endpoints.py
from datetime import datetime, timezone, timedelta
from src.models.models import Service, Incident
from tests.integration.test_base import TestBase


class TestServicesEndpoints(TestBase):

    def test_get_service_incidents_empty(self):
        """Test service incidents when service has no incidents."""
        service = Service(id="EMPTY_SERVICE", name="Empty Service", status="active")
        self.db_session.add(service)
        self.db_session.commit()

        response = self.client.get("/api/v1/services/EMPTY_SERVICE/incidents")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 0

    def test_get_most_incidents_no_services(self):
        """Test most incidents endpoint when no services exist."""
        response = self.client.get("/api/v1/services/most-incidents")
        assert response.status_code == 200
        data = response.get_json()
        assert data["service_id"] is None
        assert data["total_incidents"] == 0

    def test_get_incident_chart_multiple_statuses(self):
        """Test chart data with multiple incident statuses."""
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incidents = [
            Incident(
                id=f"INC{i}",
                service_id="SERVICE1",
                title=f"Incident {i}",
                status=status,
                urgency="high",
                created_at=datetime.utcnow()
            )
            for i, status in enumerate(['triggered', 'acknowledged', 'resolved'])
        ]
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        response = self.client.get("/api/v1/services/chart")
        data = response.get_json()
        
        # Verify all statuses are represented
        assert set(data["labels"]) == {'triggered', 'acknowledged', 'resolved'}
        assert len(data["datasets"][0]["data"]) == 3
        assert all(count == 1 for count in data["datasets"][0]["data"])

    def test_get_service_detail(self):
        """Test the service detail endpoint."""
        # Setup test data
        service = Service(id="SERVICE1", name="Test Service", status="active", last_incident_timestamp=datetime.utcnow())
        self.db_session.add(service)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/services/SERVICE1")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == "SERVICE1"
        assert data["name"] == "Test Service"

    def test_get_service_detail_not_found(self):
        """Test the service detail endpoint with non-existent service."""
        response = self.client.get("/api/v1/services/NONEXISTENT")
        assert response.status_code == 404

    def test_get_service_incidents(self):
        """Test the service incidents endpoint."""
        # Setup test data
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incident = Incident(id="INC1", service_id="SERVICE1", title="Test Incident", status="resolved", urgency="high", created_at=datetime.utcnow())
        self.db_session.add(service)
        self.db_session.add(incident)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/services/SERVICE1/incidents")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["id"] == "INC1"
        assert data[0]["status"] == "resolved"

    def test_get_most_incidents(self):
        """Test the most incidents endpoint."""
        # Setup test data (similar to unit test setup)
        service = Service(id="SERVICE1", name="Busy Service", status="active")
        incidents = [Incident(id=f"INC{i}", service_id="SERVICE1", title=f"Test Incident {i}", status="resolved", urgency="high", created_at=datetime.utcnow()) for i in range(3)]
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/services/most-incidents")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["service_id"] == "SERVICE1"
        assert data["total_incidents"] == 3
        assert "status_breakdown" in data

    def test_get_incident_chart(self):
        """Test the incident chart endpoint."""
        # Setup test data (reuse setup from most_incidents test)
        service = Service(id="SERVICE1", name="Busy Service", status="active")
        incidents = [Incident(id=f"INC{i}", service_id="SERVICE1", title=f"Test Incident {i}", status="resolved", urgency="high", created_at=datetime.utcnow()) for i in range(3)]
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/services/chart")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert "labels" in data
        assert "datasets" in data
        assert len(data["datasets"]) > 0
