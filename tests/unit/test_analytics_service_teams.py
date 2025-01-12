# tests/unit/test_analytics_service_services.py
import pytest
from datetime import datetime, timezone, timedelta
from src.services.analytics_service import AnalyticsService
from src.models.models import Service, Incident, Team, EscalationPolicy
from tests.integration.test_base import TestBase


class TestAnalyticsTeamsMethods(TestBase):
    # Teams tests
    def test_get_team_count(self):
        """Test get_team_count method."""
        # Setup test data
        team1 = Team(id="team1", name="Team 1")
        team2 = Team(id="team2", name="Team 2")
        self.db_session.add(team1)
        self.db_session.add(team2)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        result = analytics.get_team_count()

        # Verify results
        assert result["count"] == 2

    def test_get_all_teams(self):
        """Test get_all_teams method."""
        # Setup test data
        team1 = Team(id="team1", name="Team 1")
        team2 = Team(id="team2", name="Team 2")
        self.db_session.add(team1)
        self.db_session.add(team2)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        result = analytics.get_all_teams()

        # Verify results
        assert len(result) == 2
        assert result[0]["id"] == "team1"
        assert result[1]["id"] == "team2"
