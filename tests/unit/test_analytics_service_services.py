# tests/unit/test_analytics_service_services.py
import pytest
from datetime import datetime, timezone, timedelta
from src.services.analytics_service import AnalyticsService
from src.models.models import Service, Incident, Team, EscalationPolicy
from tests.integration.test_base import TestBase


class TestAnalyticsServicesMethods(TestBase):
    # Services tests
    def test_get_service_detail(self):
        """Test getting detailed information for a specific service."""
        # Setup test data
        service = Service(id="SERVICE1", name="Test Service", status="active", last_incident_timestamp=datetime.utcnow())
        team = Team(id="TEAM1", name="Test Team")
        policy = EscalationPolicy(id="POL1", name="Test Policy")
        service.teams.append(team)
        service.escalation_policies.append(policy)

        self.db_session.add(service)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        result = analytics.get_service_detail("SERVICE1")

        # Verify results
        assert result["id"] == "SERVICE1"
        assert result["name"] == "Test Service"
        assert len(result["teams"]) == 1
        assert result["teams"][0]["name"] == "Test Team"
        assert len(result["escalation_policies"]) == 1
        assert result["escalation_policies"][0]["name"] == "Test Policy"

    def test_get_service_detail_not_found(self):
        """Test getting detail for non-existent service."""
        analytics = AnalyticsService(self.db_session)
        with pytest.raises(ValueError):
            analytics.get_service_detail("NONEXISTENT")

    def test_get_service_incidents(self):
        """Test getting incidents for a specific service."""
        # Setup test data
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incident1 = Incident(id="INC1", service_id="SERVICE1", title="Test Incident 1", status="resolved", urgency="high", created_at=datetime.utcnow())
        incident2 = Incident(id="INC2", service_id="SERVICE1", title="Test Incident 2", status="triggered", urgency="low", created_at=datetime.utcnow())

        self.db_session.add(service)
        self.db_session.add(incident1)
        self.db_session.add(incident2)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        results = analytics.get_service_incidents("SERVICE1")

        # Verify results
        assert len(results) == 2
        assert results[0]["id"] in ["INC1", "INC2"]
        assert results[1]["id"] in ["INC1", "INC2"]

    def test_get_service_with_most_incidents(self):
        """Test analyzing service with most incidents."""
        # Setup test data
        service1 = Service(id="SERVICE1", name="Busy Service", status="active")
        service2 = Service(id="SERVICE2", name="Quiet Service", status="active")
        
        # Add more incidents to service1
        incidents1 = [
            Incident(
                id=f"INC{i}",
                service_id="SERVICE1",
                title=f"Test Incident {i}",
                status="resolved" if i % 2 == 0 else "triggered",
                urgency="high",
                created_at=datetime.utcnow()
            )
            for i in range(3)  # INC0, INC1, INC2
        ]
        
        # Add fewer incidents to service2, starting from a different index
        incidents2 = [
            Incident(
                id=f"INC{i + 10}",  # INC10 to avoid collision with service1's incidents
                service_id="SERVICE2",
                title=f"Test Incident {i}",
                status="resolved",
                urgency="low",
                created_at=datetime.utcnow()
            )
            for i in range(1)
        ]
        
        self.db_session.add(service1)
        self.db_session.add(service2)
        self.db_session.add_all(incidents1)
        self.db_session.add_all(incidents2)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        result = analytics.get_service_with_most_incidents()

        # Verify results
        assert result["service_id"] == "SERVICE1"
        assert result["total_incidents"] == 3
        assert len(result["status_breakdown"]) == 2  # triggered and resolved
        assert result["status_breakdown"]["resolved"] > 0
        assert result["status_breakdown"]["triggered"] > 0

    def test_get_service_detail_with_dates(self):
        """Test service detail with date handling."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        service = Service(
            id="SERVICE1",
            name="Test Service",
            status="active",
            last_incident_timestamp=timestamp
        )
        self.db_session.add(service)
        self.db_session.commit()

        analytics = AnalyticsService(self.db_session)
        result = analytics.get_service_detail("SERVICE1")
        
        assert result["last_incident_timestamp"] == timestamp

    def test_get_service_incidents_ordering(self):
        """Test incidents are returned in correct order."""
        service = Service(id="SERVICE1", name="Test Service", status="active")
        incidents = []
        for i in range(3):
            incident = Incident(
                id=f"INC{i}",
                service_id="SERVICE1",
                title=f"Incident {i}",
                status="resolved",
                urgency="high",
                created_at=datetime.now(timezone.utc) + timedelta(hours=i)
            )
            incidents.append(incident)
        
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        analytics = AnalyticsService(self.db_session)
        results = analytics.get_service_incidents("SERVICE1")
        
        # Verify descending order by created_at
        created_times = [incident["created_at"] for incident in results]
        assert created_times == sorted(created_times, reverse=True)

    @pytest.mark.parametrize("status", ["triggered", "acknowledged", "resolved"])
    def test_get_service_with_most_incidents_single_status(self, status):
        """Test analyzing services with incidents of a single status."""
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
            for i in range(3)
        ]
        self.db_session.add(service)
        self.db_session.add_all(incidents)
        self.db_session.commit()

        analytics = AnalyticsService(self.db_session)
        result = analytics.get_service_with_most_incidents()
        
        assert result["status_breakdown"][status] == 3
        assert sum(result["status_breakdown"].values()) == 3