# tests/unit/test_analytics_service_incidents.py
from datetime import datetime, timezone, timedelta
from src.services.analytics_service import AnalyticsService
from src.models.models import Service, Incident
from tests.integration.test_base import TestBase


class TestAnalyticsServiceIncidents(TestBase):
    """Test suite for incident-related analytics methods."""

    def test_get_all_incidents(self):
        """Test getting all incidents."""
        # Setup test data
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incidents = [
            Incident(
                id=f"INC{i}",
                incident_number=i,
                title=f"Test Incident {i}",
                status="resolved" if i % 2 == 0 else "triggered",
                urgency="high",
                service_id="SERVICE1",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            for i in range(3)
        ]
        
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        results = analytics.get_all_incidents()

        # Verify results
        assert len(results) == 3
        assert all(isinstance(incident["id"], str) for incident in results)
        assert all(isinstance(incident["incident_number"], int) for incident in results)
        # Verify ordering by created_at desc
        created_times = [incident["created_at"] for incident in results]
        assert created_times == sorted(created_times, reverse=True)

    def test_get_incidents_by_service(self):
        """Test getting incidents grouped by service."""
        # Setup test data
        services = [
            Service(id=f"SERVICE{i}", name=f"Service {i}", status="active")
            for i in range(2)
        ]
        self.db_session.add_all(services)
        
        incidents = [
            Incident(
                id=f"INC{i}",
                incident_number=i,
                title=f"Test Incident {i}",
                status="resolved",
                urgency="high",
                service_id="SERVICE0",
                created_at=datetime.utcnow()
            )
            for i in range(2)
        ] + [
            Incident(
                id="INC_OTHER",
                incident_number=100,
                title="Test Incident Other",
                status="triggered",
                urgency="low",
                service_id="SERVICE1",
                created_at=datetime.utcnow()
            )
        ]
        self.db_session.add_all(incidents)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        results = analytics.get_incidents_by_service()

        # Verify results
        assert len(results) == 2
        service0_data = next(r for r in results if r["service_id"] == "SERVICE0")
        service1_data = next(r for r in results if r["service_id"] == "SERVICE1")
        
        assert len(service0_data["incidents"]) == 2
        assert len(service1_data["incidents"]) == 1

    def test_get_incidents_by_status(self):
        """Test getting incidents grouped by status."""
        # Setup test data
        service = Service(id="SERVICE1", name="Test Service", status="active")
        self.db_session.add(service)
        
        statuses = ["triggered", "acknowledged", "resolved"]
        incidents = []
        for i, status in enumerate(statuses):
            incidents.extend([
                Incident(
                    id=f"INC{i}_{j}",
                    incident_number=int(f"{i}{j}"),
                    title=f"Test Incident {i}_{j}",
                    status=status,
                    urgency="high",
                    service_id="SERVICE1",
                    created_at=datetime.utcnow()
                )
                for j in range(2)  # 2 incidents per status
            ])
        
        self.db_session.add_all(incidents)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        results = analytics.get_incidents_by_status()

        # Verify results
        assert len(results) == 3  # Three different statuses
        for result in results:
            assert result["count"] == 2  # Two incidents per status
            assert len(result["incidents"]) == 2
            assert all(inc["status"] == result["status"] for inc in result["incidents"])

    def test_get_incidents_by_service_status(self):
        """Test getting incidents grouped by service and status."""
        # Setup test data
        services = [
            Service(id=f"SERVICE{i}", name=f"Service {i}", status="active")
            for i in range(2)
        ]
        self.db_session.add_all(services)
        
        current_time = datetime.now(timezone.utc)

        
        # Add 2 triggered and 1 resolved for SERVICE0
        # Add 1 triggered and 2 acknowledged for SERVICE1
        incidents = [
            # SERVICE0 incidents
            Incident(
                id="INC1",
                incident_number=1,
                title="Test Incident 1",
                status="triggered",
                service_id="SERVICE0",
                urgency="high",
                created_at=current_time,
            ),
            Incident(
                id="INC2",
                incident_number=2,
                title="Test Incident 2",
                status="triggered",
                service_id="SERVICE0",
                urgency="high",
                created_at=current_time,
            ),
            Incident(
                id="INC3",
                incident_number=3,
                title="Test Incident 3",
                status="resolved",
                service_id="SERVICE0",
                urgency="high",
                created_at=current_time,
            ),
            # SERVICE1 incidents
            Incident(
                id="INC4",
                incident_number=4,
                title="Test Incident 4",
                status="triggered",
                service_id="SERVICE1",
                urgency="high",
                created_at=current_time,
            ),
            Incident(
                id="INC5",
                incident_number=5,
                title="Test Incident 5",
                status="acknowledged",
                service_id="SERVICE1",
                urgency="high",
                created_at=current_time,
            ),
            Incident(
                id="INC6",
                incident_number=6,
                title="Test Incident 6",
                status="acknowledged",
                service_id="SERVICE1",
                urgency="high",
                created_at=current_time,
            )
        ]
        self.db_session.add_all(incidents)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        results = analytics.get_incidents_by_service_status()

        # Verify results
        assert len(results) == 2
        
        service0_data = next(r for r in results if r["service_id"] == "SERVICE0")
        assert service0_data["status_groups"]["triggered"] == 2
        assert service0_data["status_groups"]["resolved"] == 1
        assert "acknowledged" not in service0_data["status_groups"]
        
        service1_data = next(r for r in results if r["service_id"] == "SERVICE1")
        assert service1_data["status_groups"]["triggered"] == 1
        assert service1_data["status_groups"]["acknowledged"] == 2
        assert "resolved" not in service1_data["status_groups"]