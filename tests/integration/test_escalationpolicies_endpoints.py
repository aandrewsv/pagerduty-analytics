# tests/integration/test_service_endpoints.py
from datetime import datetime, timezone, timedelta
from src.models.models import EscalationPolicy
from tests.integration.test_base import TestBase


class TestEscalationPoliciesEndpoints(TestBase):

    def test_get_escalation_policy_count(self):
        """Test the escalation policy count endpoint."""
        # Setup test data
        policy1 = EscalationPolicy(id="policy1", name="Policy 1")
        policy2 = EscalationPolicy(id="policy2", name="Policy 2")
        self.db_session.add(policy1)
        self.db_session.add(policy2)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/escalation-policies/count")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2

    def test_get_all_escalation_policies(self):
        """Test the all escalation policies endpoint."""
        # Setup test data
        policy1 = EscalationPolicy(id="policy1", name="Policy 1")
        policy2 = EscalationPolicy(id="policy2", name="Policy 2")
        self.db_session.add(policy1)
        self.db_session.add(policy2)
        self.db_session.commit()

        # Execute test
        response = self.client.get("/api/v1/escalation-policies")

        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]["id"] == "policy1"
        assert data[1]["id"] == "policy2"
