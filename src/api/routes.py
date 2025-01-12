# /src/api/routes.py
from flask import jsonify, send_file, current_app, request
from flask.views import MethodView
from src.api.schemas import SimpleCountSchema, ServiceSchema, IncidentSchema, TeamSchema, EscalationPolicyBasicSchema, ServiceIncidentBreakdownSchema, ServiceChartDataSchema, ServiceDetailSchema, IncidentsByServiceSchema, IncidentStatusGroupSchema, ServiceStatusGroupSchema, EscalationPolicySchema
from flask_smorest import Blueprint, abort
from src.services.analytics_service import AnalyticsService
from src.services.data_sync_service import DataSyncService
from src.database import db
from sqlalchemy import text
from typing import Dict
import pandas as pd
import logging
import asyncio

logger = logging.getLogger(__name__)
blp = Blueprint(
    "api",
    __name__,
    url_prefix="/api/v1",
    description="PagerDuty Analytics API",
)


def get_analytics_service():
    """Get analytics service instance with database session."""
    return AnalyticsService(db.session)


# Error Handlers
@blp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not Found", "message": str(error)}), 404


@blp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()  # Reset the session in case of database error
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500


# System Endpoints


# Health Check
@blp.route("/health", methods=["GET"])
def health_check():
    """Check the health of the application and its dependencies."""
    try:
        health_status = {"status": "healthy", "components": {"database": "healthy", "api": "healthy"}}

        # Check database connection
        try:
            db.session.execute(text("SELECT 1"))
            db.session.commit()
        except Exception as e:
            health_status["components"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "unhealthy"

        # Check PagerDuty API connection
        try:
            sync_service = DataSyncService(current_app.config["PAGERDUTY_API_KEY"])
            asyncio.run(sync_service.client._make_request(None, "GET", "abilities"))
        except Exception as e:
            health_status["components"]["api"] = f"unhealthy: {str(e)}"
            health_status["status"] = "unhealthy"

        status_code = 200 if health_status["status"] == "healthy" else 503
        return jsonify(health_status), status_code
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


# Data Sync:
@blp.route("/sync", methods=["POST"])
def sync_data():
    """Manually trigger data synchronization."""
    try:
        sync_service = DataSyncService(current_app.config["PAGERDUTY_API_KEY"])
        asyncio.run(sync_service.sync_all_data())
        return jsonify({"message": "Data synchronization completed successfully"})
    except Exception as e:
        logger.error(f"Data sync failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Validation
@blp.before_request
def validate_service_id():
    """Validate service ID format if present in URL."""
    if "service_id" in request.view_args:
        service_id = request.view_args["service_id"]
        if not service_id:
            abort(400, message="Service ID is required")


# API Endpoints

# # ! REQUIRED:
# ● The number of existing Services. [✅] - /services/count -
# ● Number of Incidents per Service. - [✅] - /services - List all services with incident counts
# ● Number of Incidents by Service and Status. [✅] - /services AND /incidents/by-status AND /incidents/by-service
# ● Number of Teams and their related Services. [✅] - /teams/count AND /teams
# ● Number of Escalation Policies and their Relationship with Teams and Services. [✅] - /escalation-policies/count AND /escalation-policies
# ● CSV report of each of the above points.
# ● Analysis of which Service has more Incidents and breakdown of Incidents by status.
# ● Graph reflecting the previous point.


# Services
# GET /api/v1/services/count            # Total number of services
# GET /api/v1/services                  # List all services
# GET /api/v1/services/{id}             # Get specific service details
# GET /api/v1/services/{id}/incidents   # Get incidents for a service
# GET /api/v1/services/most-incidents   # Service with most incidents + breakdown
# GET /api/v1/services/chart            # Graph data for service with most incidents


# ! REQUIRED
@blp.route("/services/count")
class ServiceCount(MethodView):
    @blp.response(200, SimpleCountSchema)
    def get(self):
        """Gets the exact number of services."""
        analytics = get_analytics_service()
        return analytics.get_service_count()


# ! REQUIRED
@blp.route("/services")
class ServiceList(MethodView):
    @blp.response(200, ServiceSchema(many=True))
    def get(self):
        """Get list of services with incident counts"""
        analytics = get_analytics_service()
        return analytics.get_services_with_incidents_and_status()


@blp.route("/services/<string:service_id>")
class ServiceDetail(MethodView):
    @blp.response(200, ServiceDetailSchema)
    @blp.doc(description="Get detailed information for a specific service")
    def get(self, service_id):
        """Get detailed information for a specific service."""
        try:
            analytics = get_analytics_service()
            service = analytics.get_service_detail(service_id)
            if not service:
                abort(404, message=f"Service with id {service_id} not found")
            return service
        except ValueError as e:
            abort(404, message=str(e))
        except Exception as e:
            logger.error(f"Error getting service detail: {str(e)}")
            abort(500, message=str(e))


@blp.route("/services/<string:service_id>/incidents")
class ServiceIncidents(MethodView):
    @blp.response(200, IncidentSchema(many=True))
    @blp.doc(description="Get all incidents for a specific service")
    def get(self, service_id):
        """Get all incidents for a specific service."""
        try:
            analytics = get_analytics_service()
            return analytics.get_service_incidents(service_id)
        except Exception as e:
            logger.error(f"Error getting service incidents: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/services/most-incidents")
class ServiceMostIncidents(MethodView):
    @blp.response(200, ServiceIncidentBreakdownSchema)
    @blp.doc(description="Get service with most incidents and breakdown")
    def get(self):
        """Get service with most incidents and breakdown by status."""
        try:
            analytics = get_analytics_service()
            return analytics.get_service_with_most_incidents()
        except Exception as e:
            logger.error(f"Error getting service with most incidents: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/services/chart")
class ServiceIncidentChart(MethodView):
    @blp.response(200, ServiceChartDataSchema)
    @blp.doc(description="Get chart data for service with most incidents")
    def get(self):
        """Get chart data for service with most incidents."""
        try:
            analytics = get_analytics_service()
            return analytics.get_service_incident_chart_data()
        except Exception as e:
            logger.error(f"Error getting chart data: {str(e)}")
            abort(500, message="Internal server error")


# Incidents
# GET /api/v1/incidents                 # List all incidents
# GET /api/v1/incidents/by-service      # Incidents grouped by service
# GET /api/v1/incidents/by-status       # Incidents grouped by status
# GET /api/v1/incidents/by-service-status # Incidents grouped by service and status


@blp.route("/incidents")
class IncidentList(MethodView):
    @blp.response(200, IncidentSchema(many=True))
    @blp.doc(description="Get all incidents")
    def get(self):
        """List all incidents."""
        try:
            analytics = get_analytics_service()
            return analytics.get_all_incidents()
        except Exception as e:
            logger.error(f"Error getting all incidents: {str(e)}")
            abort(500, message="Internal server error")


# ! REQUIRED
@blp.route("/incidents/by-service")
class IncidentsByService(MethodView):
    @blp.response(200, IncidentsByServiceSchema(many=True))
    @blp.doc(description="Get incidents grouped by service")
    def get(self):
        """Get incidents grouped by service."""
        try:
            analytics = get_analytics_service()
            return analytics.get_incidents_by_service()
        except Exception as e:
            logger.error(f"Error getting incidents by service: {str(e)}")
            abort(500, message="Internal server error")


# ! REQUIRED
@blp.route("/incidents/by-status")
class IncidentsByStatus(MethodView):
    @blp.response(200, IncidentStatusGroupSchema(many=True))
    @blp.doc(description="Get incidents grouped by status")
    def get(self):
        """Get incidents grouped by status."""
        try:
            analytics = get_analytics_service()
            return analytics.get_incidents_by_status()
        except Exception as e:
            logger.error(f"Error getting incidents by status: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/incidents/by-service-status")
class IncidentsByServiceStatus(MethodView):
    @blp.response(200, ServiceStatusGroupSchema(many=True))
    @blp.doc(description="Get incidents grouped by service and status")
    def get(self):
        """Get incidents grouped by service and status."""
        try:
            analytics = get_analytics_service()
            return analytics.get_incidents_by_service_status()
        except Exception as e:
            logger.error(f"Error getting incidents by service and status: {str(e)}")
            abort(500, message="Internal server error")


# Teams
# GET /api/v1/teams/count               # Total number of teams
# GET /api/v1/teams                     # List all teams

# TODO:
# GET /api/v1/teams/{id}                # Get specific team details
# GET /api/v1/teams/{id}/services       # Get services for a team
# GET /api/v1/teams/service-summary     # Teams with their related services count


# ! REQUIRED
@blp.route("/teams/count")
class ServiceCount(MethodView):
    @blp.response(200, SimpleCountSchema)
    def get(self):
        """Gets the exact number of services."""
        analytics = get_analytics_service()
        return analytics.get_team_count()


# ! REQUIRED
@blp.route("/teams")
class TeamList(MethodView):
    @blp.response(200, TeamSchema(many=True))
    @blp.doc(description="Get all teams")
    def get(self):
        """List all teams."""
        try:
            analytics = get_analytics_service()
            return analytics.get_all_teams()
        except Exception as e:
            logger.error(f"Error getting all teams: {str(e)}")
            abort(500, message="Internal server error")


# Escalation Policies
# GET /api/v1/escalation-policies/count          # Total number of teams
# GET /api/v1/escalation-policies                # List all policies with teams and services


# ! REQUIRED
@blp.route("/escalation-policies/count")
class EscalationPolicyCount(MethodView):
    @blp.response(200, SimpleCountSchema)
    def get(self):
        """Gets the exact number of escalation policies."""
        analytics = get_analytics_service()
        return analytics.get_escalation_policy_count()


# ! REQUIRED
@blp.route("/escalation-policies")
class EscalationPolicyList(MethodView):
    @blp.response(200, EscalationPolicySchema(many=True))
    @blp.doc(description="Get all escalation policies")
    def get(self):
        """List all escalation policies."""
        try:
            analytics = get_analytics_service()
            return analytics.get_all_escalation_policies()
        except Exception as e:
            logger.error(f"Error getting all escalation policies: {str(e)}")
            abort(500, message="Internal server error")


# Users
# GET /api/v1/users/inactive           # Get inactive users in schedules

# Reports Endpoints (CSV exports)
# GET /api/v1/reports/services         # Services report
# GET /api/v1/reports/incidents        # Incidents report
# GET /api/v1/reports/teams           # Teams report
# GET /api/v1/reports/policies        # Escalation policies report
# GET /api/v1/reports/inactive-users  # Inactive users report
