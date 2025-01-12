# src/models/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, func
from sqlalchemy.orm import relationship
from src.database import db

Base = db.Model

# Association tables for many-to-many relationships
service_team = Table(
    "service_team",
    Base.metadata,
    Column("service_id", String(32), ForeignKey("services.id"), primary_key=True),
    Column("team_id", String(32), ForeignKey("teams.id"), primary_key=True),
)

service_escalation_policy = Table(
    "service_escalation_policy",
    Base.metadata,
    Column("service_id", String(32), ForeignKey("services.id"), primary_key=True),
    Column("escalation_policy_id", String(32), ForeignKey("escalation_policies.id"), primary_key=True),
)

schedule_users = Table(
    "schedule_users",
    Base.metadata,
    Column("schedule_id", String(32), ForeignKey("schedules.id"), primary_key=True),
    Column("user_id", String(32), ForeignKey("users.id"), primary_key=True),
)

user_teams = Table(
    "user_teams",
    Base.metadata,
    Column("user_id", String(32), ForeignKey("users.id"), primary_key=True),
    Column("team_id", String(32), ForeignKey("teams.id"), primary_key=True),
)

schedule_teams = Table("schedule_teams", Base.metadata, Column("schedule_id", String(32), ForeignKey("schedules.id"), primary_key=True), Column("team_id", String(32), ForeignKey("teams.id"), primary_key=True))

schedule_escalation_policies = Table(
    "schedule_escalation_policies",
    Base.metadata,
    Column("schedule_id", String(32), ForeignKey("schedules.id"), primary_key=True),
    Column("escalation_policy_id", String(32), ForeignKey("escalation_policies.id"), primary_key=True),
)

escalation_policy_teams = Table(
    "escalation_policy_teams",
    Base.metadata,
    Column("escalation_policy_id", String(32), ForeignKey("escalation_policies.id")),
    Column("team_id", String(32), ForeignKey("teams.id")),
)


class Service(Base):
    """
    Service model representing PagerDuty services.
    Only includes fields necessary for reporting requirements.
    """

    __tablename__ = "services"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="active")  # active, warning, critical
    last_incident_timestamp = Column(DateTime, nullable=True)

    # Relationships
    incidents = relationship("Incident", back_populates="service", lazy="dynamic")
    teams = relationship("Team", secondary=service_team, back_populates="services", lazy="joined")
    escalation_policies = relationship("EscalationPolicy", secondary=service_escalation_policy, back_populates="services", lazy="joined")

    @property
    def incident_count(self):
        """Get total number of incidents for this service"""
        return self.incidents.count()

    def incident_count_by_status(self, status):
        """Get number of incidents for this service filtered by status"""
        return self.incidents.filter_by(status=status).count()

    def __repr__(self):
        return f"<Service {self.name}>"


class Incident(Base):
    """
    Incident model representing PagerDuty incidents.
    Only includes fields necessary for reporting requirements.
    """

    __tablename__ = "incidents"

    id = Column(String(32), primary_key=True)
    incident_number = Column(Integer, unique=True)
    title = Column(String(255))
    status = Column(String(50), nullable=False, index=True)  # triggered, acknowledged, resolved
    urgency = Column(String(20), nullable=False)  # high, low
    created_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Foreign Keys
    service_id = Column(String(32), ForeignKey("services.id"), nullable=False, index=True)

    # Relationships
    service = relationship("Service", back_populates="incidents")

    @classmethod
    def get_incidents_by_service(cls, service_id: str) -> int:
        """Get count of incidents for a specific service"""
        return cls.query.filter_by(service_id=service_id).count()

    @classmethod
    def get_incidents_by_service_and_status(cls, service_id: str, status: str) -> int:
        """Get count of incidents for a specific service and status"""
        return cls.query.filter_by(service_id=service_id, status=status).count()

    @classmethod
    def get_service_incident_breakdown(cls):
        """
        Get a breakdown of incidents per service with status counts.
        Returns a list of dicts with service details and incident counts.
        """
        from sqlalchemy import func

        results = db.session.query(cls.service_id, Service.name.label("service_name"), cls.status, func.count(cls.id).label("count")).join(Service).group_by(cls.service_id, Service.name, cls.status).all()

        # Transform into a more usable format
        breakdown = {}
        for result in results:
            if result.service_id not in breakdown:
                breakdown[result.service_id] = {"service_name": result.service_name, "total": 0, "by_status": {}}
            breakdown[result.service_id]["by_status"][result.status] = result.count
            breakdown[result.service_id]["total"] += result.count

        return breakdown

    def __repr__(self):
        return f"<Incident #{self.incident_number} - {self.status}>"


class Team(Base):
    """
    Team model representing PagerDuty teams.
    Focuses on essential fields and service relationships for reporting.
    """

    __tablename__ = "teams"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)

    # Relationships
    services = relationship("Service", secondary=service_team, back_populates="teams")
    users = relationship("User", secondary=user_teams, back_populates="teams")
    schedules = relationship("Schedule", secondary=schedule_teams, back_populates="teams")

    @property
    def service_count(self) -> int:
        """Get number of services associated with this team"""
        return len(self.services)

    @classmethod
    def get_team_service_breakdown(cls):
        """
        Get a breakdown of services per team.
        Returns list of dicts with team details and service counts.
        """
        results = db.session.query(cls.id, cls.name, func.count(service_team.c.service_id).label("service_count")).outerjoin(service_team).group_by(cls.id, cls.name).all()

        return [{"team_id": r.id, "team_name": r.name, "service_count": r.service_count} for r in results]

    @classmethod
    def get_teams_with_services(cls):
        """
        Get all teams with their associated services.
        Returns list of dicts with team details and service information.
        """
        teams = cls.query.options(relationship("services").joinedload()).all()

        return [{"team_id": team.id, "team_name": team.name, "services": [{"service_id": svc.id, "service_name": svc.name, "status": svc.status, "incident_count": svc.incident_count} for svc in team.services]} for team in teams]

    def __repr__(self):
        return f"<Team {self.name}>"


class EscalationTarget(Base):
    """
    Represents a target in an escalation rule (user or schedule)
    """

    __tablename__ = "escalation_targets"
    __table_args__ = (db.UniqueConstraint("target_id", "rule_id", name="uix_target_rule"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto-incrementing primary key
    target_id = Column(String(32), nullable=False, index=True)  # The ID of the user or schedule
    rule_id = Column(String(32), ForeignKey("escalation_rules.id"), nullable=False, index=True)
    type = Column(String(50))  # user_reference, schedule_reference
    summary = Column(String(255))

    rule = relationship("EscalationRule", back_populates="targets")

    def __repr__(self):
        return f"<EscalationTarget {self.type}:{self.target_id} for rule {self.rule_id}>"


class EscalationRule(Base):
    """
    Represents a rule in an escalation policy
    """

    __tablename__ = "escalation_rules"

    id = Column(String(32), primary_key=True)
    policy_id = Column(String(32), ForeignKey("escalation_policies.id"))
    escalation_delay_in_minutes = Column(Integer)

    # Relationships
    policy = relationship("EscalationPolicy", back_populates="rules")
    targets = relationship("EscalationTarget", back_populates="rule", cascade="all, delete-orphan")


class EscalationPolicy(Base):
    """
    Represents a PagerDuty escalation policy with its rules and relationships
    """

    __tablename__ = "escalation_policies"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    num_loops = Column(Integer, default=0)

    # Relationships
    rules = relationship("EscalationRule", cascade="all, delete-orphan")
    teams = relationship("Team", secondary=escalation_policy_teams)
    services = relationship("Service", secondary=service_escalation_policy, back_populates="escalation_policies")
    schedules = relationship("Schedule", secondary=schedule_escalation_policies, back_populates="escalation_policies")

    @property
    def services_count(self) -> int:
        """Get number of services associated with this policy"""
        return len(self.services)

    @classmethod
    def get_policy_summary(cls):
        """
        Get a summary of all policies with their team and service counts
        """
        policies = cls.query.options(relationship("services").joinedload(), relationship("team").joinedload()).all()

        return [{"policy_id": policy.id, "policy_name": policy.name, "team_name": policy.team.name if policy.team else None, "services_count": policy.services_count, "services": [{"id": s.id, "name": s.name} for s in policy.services]} for policy in policies]

    @classmethod
    def get_team_policy_breakdown(cls):
        """
        Get a breakdown of policies grouped by team
        """
        from sqlalchemy import func

        results = db.session.query(Team.id.label("team_id"), Team.name.label("team_name"), func.count(cls.id).label("policy_count")).outerjoin(cls, Team.id == cls.team_id).group_by(Team.id, Team.name).all()

        return [{"team_id": r.team_id, "team_name": r.team_name, "policy_count": r.policy_count} for r in results]

    def __repr__(self):
        return f"<EscalationPolicy {self.name}>"


class Schedule(Base):
    """
    Schedule model representing PagerDuty schedules.
    """

    __tablename__ = "schedules"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    time_zone = Column(String(50))

    # Relationships
    users = relationship("User", secondary=schedule_users, back_populates="schedules")
    teams = relationship("Team", secondary=schedule_teams, back_populates="schedules")
    escalation_policies = relationship("EscalationPolicy", secondary=schedule_escalation_policies, back_populates="schedules")

    @classmethod
    def get_schedule_summary(cls):
        """Get summary of all schedules with user and team counts"""
        schedules = cls.query.options(relationship("users").joinedload(), relationship("teams").joinedload()).all()

        return [{"id": schedule.id, "name": schedule.name, "user_count": len(schedule.users), "team_count": len(schedule.teams), "teams": [{"id": t.id, "name": t.name} for t in schedule.teams]} for schedule in schedules]


class User(Base):
    """
    User model representing PagerDuty users.
    Only includes fields necessary for reporting requirements.
    """

    __tablename__ = "users"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    role = Column(String(50))  # owner, admin, user, limited_user, read_only_user, etc.

    # Relationships
    teams = relationship("Team", secondary=user_teams, back_populates="users", lazy="joined")
    schedules = relationship("Schedule", secondary=schedule_users, back_populates="users", lazy="joined")

    @classmethod
    def get_user_team_breakdown(cls):
        """Get breakdown of users by team"""
        from sqlalchemy import func

        results = db.session.query(Team.id.label("team_id"), Team.name.label("team_name"), func.count(user_teams.c.user_id).label("user_count")).outerjoin(user_teams).group_by(Team.id, Team.name).all()

        return [{"team_id": r.team_id, "team_name": r.team_name, "user_count": r.user_count} for r in results]

    @property
    def active_schedules_count(self):
        """Get count of active schedules for user"""
        return len(self.schedules)

    def __repr__(self):
        return f"<User {self.name}>"
