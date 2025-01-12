# tests/integration/test_service_endpoints.py
from datetime import datetime, timezone, timedelta
from src.models.models import Team
from tests.integration.test_base import TestBase


class TestTeamsEndpoints(TestBase):

    def test_get_team_count(self):
        """Test the team count endpoint."""
        # Setup test data
        team1 = Team(id="team1", name="Team 1")
        team2 = Team(id="team2", name="Team 2")
        self.db_session.add(team1)
        self.db_session.add(team2)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/teams/count")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2

    def test_get_all_teams(self):
        """Test the all teams endpoint."""
        # Setup test data
        team1 = Team(id="team1", name="Team 1")
        team2 = Team(id="team2", name="Team 2")
        self.db_session.add(team1)
        self.db_session.add(team2)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/teams")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]["id"] == "team1"
        assert data[1]["id"] == "team2"
