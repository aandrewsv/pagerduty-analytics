# tests/integration/test_service_endpoints.py
from datetime import datetime, timezone, timedelta
from src.models.models import User
from tests.integration.test_base import TestBase


class TestUsersEndpoints(TestBase):

    def test_get_inactive_users(self):
        """Test the inactive users endpoint."""
        # Setup test data
        user1 = User(id="user1", name="User 1", active=True)
        user2 = User(id="user2", name="User 2", active=False)
        self.db_session.add(user1)
        self.db_session.add(user2)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/users/inactive")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["id"] == "user2"
        assert data[0]["name"] == "User 2"
        assert data[0]["email"] == "user2@example.com"
        assert data[0]["role"] == "user"
        assert data[0]["active_schedules"] == []
