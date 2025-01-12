import pytest

class TestBase:
    """Base class for all integration tests."""
    @pytest.fixture(autouse=True)
    def setup(self, client, app, db_session):
        """Setup test environment."""
        self.client = client
        self.app = app
        self.db_session = db_session
