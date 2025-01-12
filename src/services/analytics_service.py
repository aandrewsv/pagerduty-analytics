# src/services/analytics_service.py
from typing import Dict, List
import pandas as pd
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from src.models.models import Service, Incident, Team, EscalationPolicy
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, session: Session):
        self.session = session

    # Services Methods
    
    def get_service_count(self) -> int:
        """Get the total number of services."""
        try:
            return { "count": self.session.query(Service).count() }
        except Exception as e:
            logger.error(f"Error counting services: {str(e)}")
            raise
    
    def get_services_with_incidents_and_status(self) -> List[Dict]:
        """Get a list of services with their incident counts and status."""
        try:
            query_result = self.session.query(Service.id, Service.name, Service.status, func.count(Incident.id).label("incident_count")).outerjoin(Incident).group_by(Service.id, Service.name).all()

            return [{"id": service.id, "name": service.name, "incident_count": service.incident_count, "status": service.status} for service in query_result]
        except Exception as e:
            logger.error(f"Error getting services with incidents: {str(e)}")
            raise

    def get_service_detail(self, service_id: str) -> Dict:
        """Get detailed information for a specific service."""
        try:
            service = self.session.query(Service).options(
                joinedload(Service.teams),
                joinedload(Service.escalation_policies)
            ).filter(Service.id == service_id).first()

            if not service:
                raise ValueError(f"Service with id {service_id} not found")

            return {
                "id": service.id,
                "name": service.name,
                "status": service.status,
                "incident_count": service.incident_count,
                "last_incident_timestamp": service.last_incident_timestamp,
                "teams": [{"id": team.id, "name": team.name} for team in service.teams],
                "escalation_policies": [
                    {"id": policy.id, "name": policy.name}
                    for policy in service.escalation_policies
                ],
            }
        except Exception as e:
            logger.error(f"Error getting service detail: {str(e)}")
            raise

    def get_service_incidents(self, service_id: str) -> List[Dict]:
        """Get all incidents for a specific service."""
        try:
            incidents = self.session.query(Incident).filter(Incident.service_id == service_id).order_by(Incident.created_at.desc()).all()

            return [{
                "id": incident.id,
                "incident_number": incident.incident_number,
                "title": incident.title,
                "status": incident.status,
                "urgency": incident.urgency,
                "created_at": incident.created_at,
                "resolved_at": incident.resolved_at
            } for incident in incidents]
        except Exception as e:
            logger.error(f"Error getting service incidents: {str(e)}")
            raise

    def get_service_with_most_incidents(self) -> Dict:
        """Analyze which service has the most incidents and breakdown by status."""
        try:
            # Get service with most incidents
            service_counts = self.session.query(Service.id, Service.name, func.count(Incident.id).label("incident_count")).outerjoin(Incident).group_by(Service.id, Service.name).order_by(func.count(Incident.id).desc()).first()

            if not service_counts:
                return {"service_name": None, "service_id": None, "total_incidents": 0, "status_breakdown": {}}

            # Get status breakdown for this service
            status_breakdown = self.session.query(Incident.status, func.count(Incident.id).label("count")).filter(Incident.service_id == service_counts.id).group_by(Incident.status).all()

            return {"service_name": service_counts.name, "service_id": service_counts.id, "total_incidents": service_counts.incident_count, "status_breakdown": {status: count for status, count in status_breakdown}}
        except Exception as e:
            logger.error(f"Error analyzing service incidents: {str(e)}")
            raise

    def get_service_incident_chart_data(self) -> Dict:
        """Get chart data for the service with most incidents."""
        try:
            service_analysis = self.get_service_with_most_incidents()

            if not service_analysis["service_id"]:
                return {"labels": [], "datasets": []}

            # Transform the data for chart visualization
            statuses = list(service_analysis["status_breakdown"].keys())
            values = list(service_analysis["status_breakdown"].values())

            return {"labels": statuses, "datasets": [{"label": service_analysis["service_name"], "data": values, "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56"]}]}  # triggered  # acknowledged  # resolved
        except Exception as e:
            logger.error(f"Error getting chart data: {str(e)}")
            raise

    # Incidents Methods
    
    def get_all_incidents(self) -> List[Dict]:
        """Get all incidents with their details."""
        try:
            incidents = self.session.query(Incident)\
                .order_by(Incident.created_at.desc())\
                .all()
            
            return [{
                "id": incident.id,
                "incident_number": incident.incident_number,
                "title": incident.title,
                "status": incident.status,
                "urgency": incident.urgency,
                "service_id": incident.service_id,
                "created_at": incident.created_at,
                "resolved_at": incident.resolved_at
            } for incident in incidents]
        except Exception as e:
            logger.error(f"Error getting all incidents: {str(e)}")
            raise

    def get_incidents_by_service(self) -> List[Dict]:
        """Get incidents grouped by service."""
        try:
            results = self.session.query(
                Service.id.label('service_id'),
                Service.name.label('service_name'),
                Incident
            ).join(
                Incident, Service.id == Incident.service_id
            ).order_by(
                Service.name, Incident.created_at.desc()
            ).all()

            # Group results by service
            services_dict = {}
            for service_id, service_name, incident in results:
                if service_id not in services_dict:
                    services_dict[service_id] = {
                        'service_id': service_id,
                        'service_name': service_name,
                        'incidents': []
                    }
                services_dict[service_id]['incidents'].append({
                    "id": incident.id,
                    "incident_number": incident.incident_number,
                    "title": incident.title,
                    "status": incident.status,
                    "urgency": incident.urgency,
                    "created_at": incident.created_at,
                    "resolved_at": incident.resolved_at
                })

            return list(services_dict.values())
        except Exception as e:
            logger.error(f"Error getting incidents by service: {str(e)}")
            raise

    def get_incidents_by_status(self) -> List[Dict]:
        """Get incidents grouped by status."""
        try:
            results = self.session.query(
                Incident.status,
                func.count(Incident.id).label('count')
            ).group_by(
                Incident.status
            ).order_by(
                Incident.status
            ).all()

            # Get incidents for each status
            status_groups = []
            for status, count in results:
                incidents = self.session.query(Incident).filter(
                    Incident.status == status
                ).order_by(
                    Incident.created_at.desc()
                ).all()
                
                status_groups.append({
                    "status": status,
                    "count": count,
                    "incidents": [{
                        "id": inc.id,
                        "incident_number": inc.incident_number,
                        "title": inc.title,
                        "status": inc.status,
                        "urgency": inc.urgency,
                        "created_at": inc.created_at,
                        "resolved_at": inc.resolved_at
                    } for inc in incidents]
                })

            return status_groups
        except Exception as e:
            logger.error(f"Error getting incidents by status: {str(e)}")
            raise

    def get_incidents_by_service_status(self) -> List[Dict]:
        """Get incidents grouped by service and status."""
        try:
            results = self.session.query(
                Service.id.label('service_id'),
                Service.name.label('service_name'),
                Incident.status,
                func.count(Incident.id).label('count')
            ).join(
                Incident, Service.id == Incident.service_id
            ).group_by(
                Service.id, Service.name, Incident.status
            ).order_by(
                Service.name, Incident.status
            ).all()

            # Transform results into the desired format
            services_dict = {}
            for service_id, service_name, status, count in results:
                if service_id not in services_dict:
                    services_dict[service_id] = {
                        'service_id': service_id,
                        'service_name': service_name,
                        'status_groups': {}
                    }
                services_dict[service_id]['status_groups'][status] = count

            return list(services_dict.values())
        except Exception as e:
            logger.error(f"Error getting incidents by service and status: {str(e)}")
            raise

    # Teams Methods
    def get_team_count(self) -> int:
        """Get the total number of teams."""
        try:
            return { "count": self.session.query(Team).count() }
        except Exception as e:
            logger.error(f"Error counting teams: {str(e)}")
            raise

    def get_all_teams(self) -> List[Dict]:
        """Get all teams with their associated services."""
        try:
            teams = self.session.query(Team).options(joinedload(Team.services)).all()

            return [{"id": team.id, "name": team.name, "services": [{"id": svc.id, "name": svc.name, "status": svc.status, "incident_count": svc.incident_count} for svc in team.services]} for team in teams]
        except Exception as e:
            logger.error(f"Error getting all teams: {str(e)}")
            raise
    
    # Escalation Policies Methods
    # Users Methods
    # Reports Methods
