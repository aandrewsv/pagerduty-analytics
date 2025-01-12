# /src/api/routes.py
from flask import jsonify, send_file, current_app, request, Response
from flask.views import MethodView
from src.api.schemas import (
    SimpleCountSchema,
    ServiceSchema,
    IncidentSchema,
    TeamSchema,
    UserSchema,
    ServiceIncidentBreakdownSchema,
    ServiceChartDataSchema,
    ServiceDetailSchema,
    IncidentsByServiceSchema,
    IncidentStatusGroupSchema,
    ServiceStatusGroupSchema,
    EscalationPolicySchema,
    ServicesReportSchema,
    IncidentsCountPerServiceReportSchema,
    ReportsIncidentsStatusCountByService,
    ReportsTeams,
    ReportsServices,
    ReportsServicesTeams,
    ReportEscalationPolicies,
    ReportEscalationPoliciesTeams,
    ReportEscalationPoliciesServices,
)
from flask_smorest import Blueprint, abort
from src.services.analytics_service import AnalyticsService
from src.services.data_sync_service import DataSyncService
from src.database import db
from sqlalchemy import text
import csv
import io
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


# Services
# GET /api/v1/services/count            # Total number of services
# GET /api/v1/services                  # List all services
# GET /api/v1/services/{id}             # Get specific service details
# GET /api/v1/services/{id}/incidents   # Get incidents for a service
# GET /api/v1/services/most-incidents   # Service with most incidents + breakdown
# GET /api/v1/services/chart            # Graph data for service with most incidents


@blp.route("/services/count")
class ServiceCount(MethodView):
    @blp.response(200, SimpleCountSchema)
    def get(self):
        """Gets the exact number of services."""
        analytics = get_analytics_service()
        return analytics.get_service_count()


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


@blp.route("/teams/count")
class ServiceCount(MethodView):
    @blp.response(200, SimpleCountSchema)
    def get(self):
        """Gets the exact number of services."""
        analytics = get_analytics_service()
        return analytics.get_team_count()


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
# GET /api/v1/escalation-policies/count          # Total number of escalation policies
# GET /api/v1/escalation-policies                # List all escalation policies with teams and services


@blp.route("/escalation-policies/count")
class EscalationPolicyCount(MethodView):
    @blp.response(200, SimpleCountSchema)
    def get(self):
        """Gets the exact number of escalation policies."""
        analytics = get_analytics_service()
        return analytics.get_escalation_policy_count()


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


@blp.route("/users/inactive")
class UserInactive(MethodView):
    @blp.response(200, UserSchema(many=True))
    @blp.doc(description="Get inactive users in schedules")
    def get(self):
        """Get inactive users in schedules."""
        try:
            analytics = get_analytics_service()
            return analytics.get_inactive_users()
        except Exception as e:
            logger.error(f"Error getting inactive users: {str(e)}")
            abort(500, message="Internal server error")


# Reports Endpoints (CSV exports) ALL REQUIRED
# GET /api/v1/reports/services_count
# GET /api/v1/reports/incidents_count_per_service
# GET /api/v1/reports/incidents_status_count_by_service/:service_id
# GET /api/v1/reports/teams
# GET /api/v1/reports/services
# GET /api/v1/reports/services_teams
# GET /api/v1/reports/escalation_policies
# GET /api/v1/reports/escalation_policies_teams
# GET /api/v1/reports/escalation_policies_services


@blp.route("/reports/services_count")
class ReportsServices(MethodView):
    @blp.response(200, ServicesReportSchema)
    @blp.doc(description="Services report")
    def get(self):
        """Services count CSV report."""
        try:
            # Get services count
            analytics = get_analytics_service()
            count = analytics.get_service_count()["count"]

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Service Count"])
            writer.writerow([count])

            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=services_count.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting services report: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/reports/incidents_count_per_service")
class ReportsIncidentsCountPerService(MethodView):
    @blp.response(200, IncidentsCountPerServiceReportSchema)
    @blp.doc(description="Incidents count per service CSV report")
    def get(self):
        """Incidents count per service CSV report."""
        try:
            # Get services count
            analytics = get_analytics_service()
            data = analytics.get_incidents_by_service()

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Service", "Incidents"])
            for row in data:
                writer.writerow([row["service_name"], len(row["incidents"])])

            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=incidents_count_per_service.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting incidents count per service report: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/reports/incidents_status_count_by_service/<string:service_id>")
class ReportsIncidentsStatusCountByService(MethodView):
    @blp.response(200, ReportsIncidentsStatusCountByService)
    @blp.doc(description="Incidents status count by service CSV report")
    def get(self, service_id):
        """Incidents status count by service CSV report."""
        try:
            # Get services count
            analytics = get_analytics_service()
            data = analytics.get_incidents_status_count_by_service(service_id)

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Status", "Incident Count"])
            for row in data:
                writer.writerow([row["status"], row["count"]])

            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=incidents_count_per_service.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting incidents status count by service report: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/reports/teams")
class ReportsTeams(MethodView):
    @blp.response(200, ReportsTeams)
    @blp.doc(description="All teams CSV report")
    def get(self):
        """All teams CSV report"""
        try:
            # Get all teams
            analytics = get_analytics_service()
            data = analytics.get_all_teams()

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Team ID", "Team Name"])
            for row in data:
                writer.writerow([row["id"], row["name"]])

            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=incidents_count_per_service.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting teams report: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/reports/services")
class ReportsServices(MethodView):
    @blp.response(200, ReportsServices)
    @blp.doc(description="All services CSV report")
    def get(self):
        """All services CSV report"""
        try:
            # Get all services
            analytics = get_analytics_service()
            data = analytics.get_services_with_incidents_and_status()

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Service ID", "Service Name"])
            for row in data:
                writer.writerow([row["id"], row["name"]])

            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=incidents_count_per_service.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting services report: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/reports/services_teams")
class ReportsServicesTeams(MethodView):
    @blp.response(200, ReportsServicesTeams)
    @blp.doc(description="All services CSV report")
    def get(self):
        """All services CSV report"""
        try:
            # Get all services
            analytics = get_analytics_service()
            data = analytics.get_all_services_teams_relationships()

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Service ID", "Team Name"])
            for row in data:
                writer.writerow([row.service_id, row.team_id])
            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=incidents_count_per_service.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting services and teams report: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/reports/escalation_policies")
class ReportEscalationPolicies(MethodView):
    @blp.response(200, ReportEscalationPolicies)
    @blp.doc(description="All escalation policies CSV report")
    def get(self):
        """All escalation policies CSV report"""
        try:
            # Get all escalation policies
            analytics = get_analytics_service()
            data = analytics.get_all_escalation_policies()

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Escalation Policy ID", "Escalation Policy Name"])
            for row in data:
                writer.writerow([row["id"], row["name"]])
            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=incidents_count_per_service.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting escalation policies report: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/reports/escalation_policies_teams")
class ReportEscalationPoliciesTeams(MethodView):
    @blp.response(200, ReportEscalationPoliciesTeams)
    @blp.doc(description="All escalation policies and teams relationships CSV report")
    def get(self):
        """All escalation policies and teams relationships CSV report"""
        try:
            # Get all escalation policies
            analytics = get_analytics_service()
            data = analytics.get_escalation_policies_teams_relationships()

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Escalation Policy ID", "Team ID"])
            for row in data:
                writer.writerow([row.escalation_policy_id, row.team_id])
            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=incidents_count_per_service.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting escalation policies and teams report: {str(e)}")
            abort(500, message="Internal server error")


@blp.route("/reports/escalation_policies_services")
class ReportEscalationPoliciesServices(MethodView):
    @blp.response(200, ReportEscalationPoliciesServices)
    @blp.doc(description="All escalation policies and services relationships CSV report")
    def get(self):
        """All escalation policies and services relationships CSV report"""
        try:
            # Get all escalation policies
            analytics = get_analytics_service()
            data = analytics.get_escalation_policies_services_relationships()

            # Creates CSV file
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Escalation Policy ID", "Service ID"])
            for row in data:
                writer.writerow([row.escalation_policy_id, row.service_id])
            # Send CSV file as response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=incidents_count_per_service.csv",
                },
            )
        except Exception as e:
            logger.error(f"Error getting escalation policies and services report: {str(e)}")
            abort(500, message="Internal server error")
