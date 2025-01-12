# src/api/pagerduty_client.py
import aiohttp
import asyncio
from typing import Dict, List, Optional
from functools import partial
import logging

logger = logging.getLogger(__name__)


class PagerDutyClient:
    BASE_URL = "https://api.pagerduty.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Accept": "application/vnd.pagerduty+json;version=2", "Content-Type": "application/json", "Authorization": f"Token token={api_key}"}

    async def _make_request(self, session: aiohttp.ClientSession, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make an async request to the PagerDuty API."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            async with session.request(method, url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Error making request to {endpoint}: {str(e)}")
            raise

    async def fetch_all_pages(self, session: aiohttp.ClientSession, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """Fetch all pages of results from a paginated endpoint."""
        if params is None:
            params = {}
        all_items = []
        params["offset"] = 0

        while True:
            response = await self._make_request(session, "GET", endpoint, params)
            # Get the key that matches the endpoint name (without trailing 's' if present)
            key = endpoint.rstrip("s")
            if key in response:
                all_items.extend(response[key])
            else:
                # Try plural form if singular not found
                key = f"{key}s"
                if key in response:
                    all_items.extend(response[key])

            if not response.get("more"):
                break

            params["offset"] += response.get("limit", 25)

        return all_items

    async def get_services(self) -> List[Dict]:
        """Fetch all services."""
        async with aiohttp.ClientSession() as session:
            return await self.fetch_all_pages(session, "services")

    async def get_incidents(self, service_id: Optional[str] = None) -> List[Dict]:
        """Fetch all incidents, optionally filtered by service."""
        params = {"service_ids[]": service_id} if service_id else None
        async with aiohttp.ClientSession() as session:
            return await self.fetch_all_pages(session, "incidents", params)

    async def get_teams(self) -> List[Dict]:
        """Fetch all teams."""
        async with aiohttp.ClientSession() as session:
            return await self.fetch_all_pages(session, "teams")

    async def get_escalation_policies(self) -> List[Dict]:
        """Fetch all escalation policies."""
        async with aiohttp.ClientSession() as session:
            return await self.fetch_all_pages(session, "escalation_policies")

    async def get_schedules(self) -> List[Dict]:
        """Fetch all schedules."""
        async with aiohttp.ClientSession() as session:
            return await self.fetch_all_pages(session, "schedules")

    async def fetch_all_data(self) -> Dict[str, List[Dict]]:
        """Fetch all required data concurrently."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_all_pages(session, "services"), self.fetch_all_pages(session, "incidents"), self.fetch_all_pages(session, "teams"), self.fetch_all_pages(session, "escalation_policies"), self.fetch_all_pages(session, "users"), self.fetch_all_pages(session, "schedules")]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            return {
                "services": results[0],
                "incidents": results[1],
                "teams": results[2],
                "escalation_policies": results[3],
                "users": results[4],
                "schedules": results[5],
            }
