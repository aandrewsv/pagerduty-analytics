# src/services/data_sync_service.py
from src.api.pagerduty_client import PagerDutyClient
from src.models.models import Service, Incident, Team, EscalationPolicy, EscalationRule, EscalationTarget, Schedule, User
from src.database import db
from datetime import datetime
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class DataSyncService:
    def __init__(self, api_key: str):
        self.client = PagerDutyClient(api_key)

    async def sync_services(self, services_data: List[Dict]) -> None:
        """
        Synchronize services data with refined fields and relationship handling.

        Args:
            services_data: List of service dictionaries from PagerDuty API
        """
        try:
            logger.debug(f"Received {len(services_data)} services to sync")
            for service_data in services_data:
                service = Service.query.get(service_data["id"])
                if not service:
                    service = Service(id=service_data["id"])

                # Update basic fields
                service.name = service_data["name"]
                service.description = service_data.get("description")
                service.status = service_data["status"]

                # Handle last incident timestamp
                if service_data.get("last_incident_timestamp"):
                    service.last_incident_timestamp = datetime.fromisoformat(service_data["last_incident_timestamp"].replace("Z", "+00:00"))

                # Handle team relationships
                if "teams" in service_data and service_data["teams"]:
                    team_ids = [team["id"] for team in service_data["teams"]]
                    teams = Team.query.filter(Team.id.in_(team_ids)).all()
                    service.teams = teams
                    logger.debug(f"Associated service {service.name} with {len(teams)} teams: {[t.name for t in teams]}")

                # Handle escalation policy relationship
                if "escalation_policy" in service_data and service_data["escalation_policy"]:
                    policy_id = service_data["escalation_policy"]["id"]
                    policy = EscalationPolicy.query.get(policy_id)
                    if policy:
                        service.escalation_policies = [policy]
                        logger.debug(f"Associated service {service.name} with escalation policy {policy.name}")

                db.session.add(service)

            db.session.commit()

            # Verify team associations
            for service_data in services_data:
                service = Service.query.get(service_data["id"])
                if "teams" in service_data and service_data["teams"]:
                    expected_team_count = len(service_data["teams"])
                    actual_team_count = len(service.teams)
                    logger.info(f"Service {service.name} team association verification: " f"Expected {expected_team_count} teams, found {actual_team_count} teams")

            logger.info(f"Successfully synchronized {len(services_data)} services")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing services: {str(e)}")
            raise

    async def sync_incidents(self, incidents_data: List[Dict]) -> None:
        """
        Synchronize incidents data with refined fields.

        Args:
            incidents_data: List of incident dictionaries from PagerDuty API
        """
        try:
            logger.debug(f"Received {len(incidents_data)} incidents to sync")

            for incident_data in incidents_data:
                incident = Incident.query.get(incident_data["id"])
                if not incident:
                    incident = Incident(id=incident_data["id"])

                # Update basic fields
                incident.incident_number = incident_data["incident_number"]
                incident.title = incident_data["title"]
                incident.status = incident_data["status"]
                incident.urgency = incident_data["urgency"]
                incident.service_id = incident_data["service"]["id"]

                # Handle timestamps
                incident.created_at = datetime.fromisoformat(incident_data["created_at"].replace("Z", "+00:00"))

                if incident_data.get("resolved_at"):
                    incident.resolved_at = datetime.fromisoformat(incident_data["resolved_at"].replace("Z", "+00:00"))

                db.session.add(incident)

                # Update service's last incident timestamp if this is more recent
                service = Service.query.get(incident.service_id)
                if service and (not service.last_incident_timestamp or incident.created_at > service.last_incident_timestamp):
                    service.last_incident_timestamp = incident.created_at

            db.session.commit()
            logger.info(f"Successfully synchronized {len(incidents_data)} incidents")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing incidents: {str(e)}")
            raise

    async def sync_teams(self, teams_data: List[Dict]) -> None:
        """
        Synchronize teams data with refined fields.

        Args:
            teams_data: List of team dictionaries from PagerDuty API
        """
        try:
            logger.debug(f"Received {len(teams_data)} teams to sync")

            # Get existing teams for bulk update
            existing_teams = {team.id: team for team in Team.query.all()}

            for team_data in teams_data:
                team = existing_teams.get(team_data["id"])
                if not team:
                    team = Team(id=team_data["id"])

                # Update basic fields
                team.name = team_data["name"]

                db.session.add(team)

            db.session.commit()
            logger.info(f"Successfully synchronized {len(teams_data)} teams")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing teams: {str(e)}")
            raise

    async def sync_escalation_policies(self, policies_data: List[Dict]) -> None:
        """
        Synchronize escalation policies data with refined fields and relationship handling.
        """
        try:
            logger.debug(f"Received {len(policies_data)} escalation policies to sync")

            # Clear existing escalation rules and targets to avoid conflicts
            db.session.query(EscalationTarget).delete()
            db.session.query(EscalationRule).delete()
            db.session.commit()

            for policy_data in policies_data:
                policy = EscalationPolicy.query.get(policy_data["id"])
                if not policy:
                    policy = EscalationPolicy(id=policy_data["id"])

                # Update basic fields
                policy.name = policy_data["name"]
                policy.description = policy_data.get("description")
                policy.num_loops = policy_data.get("num_loops", 0)

                # Handle team relationship
                if policy_data.get("teams"):
                    policy.team_id = policy_data["teams"][0]["id"] if policy_data["teams"] else None

                db.session.add(policy)

            # First commit to ensure all policies exist
            db.session.commit()

            # Now create rules and targets
            for policy_data in policies_data:
                policy = EscalationPolicy.query.get(policy_data["id"])

                if "escalation_rules" in policy_data:
                    for rule_data in policy_data["escalation_rules"]:
                        rule = EscalationRule(id=rule_data["id"], policy_id=policy.id, escalation_delay_in_minutes=rule_data["escalation_delay_in_minutes"])
                        db.session.add(rule)

                        # Add targets
                        for target_data in rule_data["targets"]:
                            if not target_data.get("deleted_at"):
                                target = EscalationTarget(target_id=target_data["id"], rule_id=rule.id, type=target_data["type"], summary=target_data["summary"])
                                db.session.add(target)

            db.session.commit()
            logger.info(f"Successfully synchronized {len(policies_data)} escalation policies")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing escalation policies: {str(e)}")
            raise

    async def sync_users(self, users_data: List[Dict]) -> None:
        """
        Synchronize users data with refined fields and relationship handling.

        Args:
            users_data: List of user dictionaries from PagerDuty API
        """
        try:
            logger.debug(f"Received {len(users_data)} users to sync")

            for user_data in users_data:
                user = User.query.get(user_data["id"])
                if not user:
                    user = User(id=user_data["id"])

                # Update basic fields
                user.name = user_data["name"]
                user.email = user_data["email"]
                user.role = user_data["role"]

                # Handle team relationships
                if "teams" in user_data:
                    team_ids = [team["id"] for team in user_data["teams"]]
                    teams = Team.query.filter(Team.id.in_(team_ids)).all()
                    user.teams = teams

                db.session.add(user)

            db.session.commit()
            logger.info(f"Successfully synchronized {len(users_data)} users")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing users: {str(e)}")
            raise

    async def sync_schedules(self, schedules_data: List[Dict]) -> None:
        """
        Synchronize schedules data with refined fields and relationship handling.

        Args:
            schedules_data: List of schedule dictionaries from PagerDuty API
        """
        try:
            logger.debug(f"Received {len(schedules_data)} schedules to sync")

            for schedule_data in schedules_data:
                schedule = Schedule.query.get(schedule_data["id"])
                if not schedule:
                    schedule = Schedule(id=schedule_data["id"])

                # Update basic fields
                schedule.name = schedule_data["name"]
                schedule.time_zone = schedule_data.get("time_zone")

                # Handle user relationships - skip deleted users
                if "users" in schedule_data:
                    user_ids = [user["id"] for user in schedule_data["users"] if not user.get("deleted_at")]
                    users = User.query.filter(User.id.in_(user_ids)).all()
                    schedule.users = users

                # Handle team relationships
                if "teams" in schedule_data:
                    team_ids = [team["id"] for team in schedule_data["teams"]]
                    teams = Team.query.filter(Team.id.in_(team_ids)).all()
                    schedule.teams = teams

                db.session.add(schedule)

            db.session.commit()
            logger.info(f"Successfully synchronized {len(schedules_data)} schedules")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing schedules: {str(e)}")
            raise

    async def sync_all_data(self) -> None:
        """Synchronize all data from PagerDuty."""
        try:
            logger.info("Starting full data synchronization...")

            # Fetch all data concurrently
            all_data = await self.client.fetch_all_data()

            # Synchronize data in order of dependencies
            await self.sync_services(all_data["services"])
            await self.sync_incidents(all_data["incidents"])
            await self.sync_teams(all_data["teams"])
            await self.sync_escalation_policies(all_data["escalation_policies"])
            await self.sync_users(all_data["users"])
            await self.sync_schedules(all_data["schedules"])

            logger.info("Full data synchronization completed successfully")
        except Exception as e:
            logger.error(f"Error during full data sync: {str(e)}")
            raise
