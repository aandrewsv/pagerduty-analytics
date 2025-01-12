# tests/unit/test_analytics_service_services.py
import pytest
from datetime import datetime, timezone, timedelta
from src.services.analytics_service import AnalyticsService
from src.models.models import Service, Incident, Team, EscalationPolicy
from tests.integration.test_base import TestBase


class TestAnalyticsEscalationPoliciesMethods(TestBase):
    # Teams tests
    def test_get_escalation_policy_count(self):
        """Test get_escalation_policy_count method."""
        # Setup test data
        policy1 = EscalationPolicy(id="policy1", name="Policy 1")
        policy2 = EscalationPolicy(id="policy2", name="Policy 2")
        self.db_session.add(policy1)
        self.db_session.add(policy2)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        result = analytics.get_escalation_policy_count()

        # Verify results
        assert result["count"] == 2

    def test_get_all_escalation_policies(self):
        """Test get_all_escalation_policies method."""
        # Setup test data
        policy1 = EscalationPolicy(id="policy1", name="Policy 1")
        policy2 = EscalationPolicy(id="policy2", name="Policy 2")
        self.db_session.add(policy1)
        self.db_session.add(policy2)
        self.db_session.commit()

        # Execute test
        analytics = AnalyticsService(self.db_session)
        result = analytics.get_all_escalation_policies()

        # Verify results
        assert len(result) == 2
        assert result[0]["id"] == "policy1"  # TODO: verify relationships
        assert result[1]["id"] == "policy2"  # TODO: verify relationships
