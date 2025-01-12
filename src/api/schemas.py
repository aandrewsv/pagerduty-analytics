from marshmallow import Schema, fields, validate, pre_dump


class ServiceSchema(Schema):
    """Schema for Service objects."""

    id = fields.Str(required=True, metadata={"description": "Service unique identifier"})
    name = fields.Str(required=True, metadata={"description": "Service name"})
    status = fields.Str(required=True, validate=validate.OneOf(["active", "warning", "critical"]), metadata={"description": "Service status"})
    incident_count = fields.Int(metadata={"description": "Total number of incidents"})
    last_incident_timestamp = fields.DateTime(format="iso", metadata={"description": "Timestamp of last incident"})

    @pre_dump
    def process_timestamps(self, data, **kwargs):
        """Convert datetime strings to datetime objects if needed."""
        if isinstance(data, dict):
            if data.get("last_incident_timestamp"):
                if isinstance(data["last_incident_timestamp"], str):
                    from datetime import datetime

                    try:
                        data["last_incident_timestamp"] = datetime.fromisoformat(data["last_incident_timestamp"].replace("Z", "+00:00"))
                    except ValueError:
                        data["last_incident_timestamp"] = None
        return data


class IncidentSchema(Schema):
    """Schema for Incident objects."""

    id = fields.Str(required=True, metadata={"description": "Incident unique identifier"})
    incident_number = fields.Int(required=True, metadata={"description": "Incident number"})
    title = fields.Str(required=True, metadata={"description": "Incident title"})
    status = fields.Str(required=True, validate=validate.OneOf(["triggered", "acknowledged", "resolved"]), metadata={"description": "Incident status"})
    urgency = fields.Str(required=True, validate=validate.OneOf(["high", "low"]), metadata={"description": "Incident urgency"})
    service_id = fields.Str(required=True, metadata={"description": "Service unique identifier"})
    created_at = fields.DateTime(required=True, format="iso", metadata={"description": "Incident creation timestamp"})
    resolved_at = fields.DateTime(allow_none=True, format="iso", metadata={"description": "Incident resolution timestamp"})


class TeamSchema(Schema):
    """Schema for Team objects."""

    id = fields.Str(required=True, metadata={"description": "Team unique identifier"})
    name = fields.Str(required=True, metadata={"description": "Team name"})
    service_count = fields.Int(metadata={"description": "Number of services in the team"})
    services = fields.List(fields.Nested(ServiceSchema), metadata={"description": "List of services associated with the team"})


class IncidentAnalysisSchema(Schema):
    """Schema for Incident Analysis response."""

    service_name = fields.Str(required=True, metadata={"description": "Service name"})
    total_incidents = fields.Int(required=True, metadata={"description": "Total number of incidents"})
    status_breakdown = fields.Dict(keys=fields.Str(), values=fields.Int(), metadata={"description": "Incident status breakdown"})


class ChartDataSchema(Schema):
    """Schema for Chart Data response."""

    labels = fields.List(fields.Str(), required=True, metadata={"description": "Chart labels"})
    datasets = fields.List(fields.Dict(keys=fields.Str(), values=fields.Raw()), required=True, metadata={"description": "Chart datasets"})


class ServiceDetailSchema(Schema):
    """Schema for detailed Service information."""

    id = fields.Str(required=True, metadata={"description": "Service unique identifier"})
    name = fields.Str(required=True, metadata={"description": "Service name"})
    status = fields.Str(required=True, validate=validate.OneOf(["active", "warning", "critical"]), metadata={"description": "Service status"})
    incident_count = fields.Int()
    last_incident_timestamp = fields.DateTime(format="iso", allow_none=True)
    teams = fields.List(fields.Nested(lambda: TeamBasicSchema()))
    escalation_policies = fields.List(fields.Nested(lambda: EscalationPolicyBasicSchema()))


class TeamBasicSchema(Schema):
    """Basic Team information schema."""

    id = fields.Str(required=True)
    name = fields.Str(required=True)


class EscalationPolicyBasicSchema(Schema):
    """Basic Escalation Policy information schema."""

    id = fields.Str(required=True)
    name = fields.Str(required=True)


class ServiceIncidentBreakdownSchema(Schema):
    """Schema for service with most incidents breakdown."""

    service_name = fields.Str(required=True)
    service_id = fields.Str(required=True)
    total_incidents = fields.Int(required=True)
    status_breakdown = fields.Dict(keys=fields.Str(), values=fields.Int())


class ServiceChartDataSchema(Schema):
    """Schema for service incident chart data."""

    labels = fields.List(fields.Str(), required=True)
    datasets = fields.List(fields.Dict(keys=fields.Str(), values=fields.Raw()), required=True)


class IncidentsByServiceSchema(Schema):
    """Schema for incidents grouped by service."""

    service_id = fields.Str(required=True, metadata={"description": "Service identifier"})
    service_name = fields.Str(required=True, metadata={"description": "Service name"})
    incidents = fields.List(fields.Nested(IncidentSchema), required=True, metadata={"description": "List of incidents"})


class IncidentStatusGroupSchema(Schema):
    """Schema for incidents grouped by status."""

    status = fields.Str(required=True, metadata={"description": "Incident status"})
    count = fields.Int(required=True, metadata={"description": "Number of incidents"})
    incidents = fields.List(fields.Nested(IncidentSchema), required=True, metadata={"description": "List of incidents"})


class ServiceStatusGroupSchema(Schema):
    """Schema for incidents grouped by service and status."""

    service_name = fields.Str(required=True, metadata={"description": "Service name"})
    service_id = fields.Str(required=True, metadata={"description": "Service identifier"})
    status_groups = fields.Dict(keys=fields.Str(), values=fields.Int(), required=True, metadata={"description": "Count of incidents by status"})


class SimpleCountSchema(Schema):
    """Schema for simple count response."""

    count = fields.Int(required=True, metadata={"description": "Count"})


class EscalationPolicySchema(Schema):
    """Schema for Escalation Policy objects."""

    id = fields.Str(required=True, metadata={"description": "Escalation Policy unique identifier"})
    name = fields.Str(required=True, metadata={"description": "Escalation Policy name"})
    description = fields.Str(required=True, metadata={"description": "Escalation Policy description"})
    num_loops = fields.Int(required=True, metadata={"description": "Number of loops"})
    teams = fields.List(fields.Nested(lambda: TeamBasicSchema()), required=True, metadata={"description": "List of teams associated with the escalation policy"})
    services = fields.List(fields.Nested(lambda: ServiceSchema()), required=True, metadata={"description": "List of services associated with the escalation policy"})
