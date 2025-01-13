# tests/unit/test_analytics_service_services.py
import pytest
from datetime import datetime, timezone, timedelta
from src.services.analytics_service import AnalyticsService
from src.models.models import User
from tests.integration.test_base import TestBase


class TestAnalyticsUsersMethods(TestBase):
    # Users tests
    def test_get_inactive_users(self):
        """Test get_inactive_users method."""
        # Setup test data
        user1 = User(id="user1", name="User 1", active=True)
        user2 = User(id="user2", name="User 2", active=False)
        self.db_session.add(user1)
        self.db_session.add(user2)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        result = analytics.get_inactive_users()

        # Verify results
        assert len(result) == 1
        assert result[0]["id"] == "user2"
        assert result[0]["name"] == "User 2"
        assert result[0]["active_schedules_count"] == 0
