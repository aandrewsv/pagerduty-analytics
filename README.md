# PagerDuty Analytics System

A system for analyzing PagerDuty data with a focus on service incidents, team relationships, and escalation policies.

## Features

- Data synchronization with PagerDuty API
- MySQL database for data persistence and analysis
- RESTful API with OpenAPI documentation
- Metabase integration for data visualization
- Comprehensive test suite
- Dockerized project and tests

## Required API Endpoints for PagerDuty take home excercise

The number of existing Services

- `GET /api/v1/services/count`

Number of Incidents per Service

- `GET /api/v1/services`

Number of Incidents by Service and Status

- `GET /api/v1/services`
- `GET /api/v1/incidents/by-status`
- `GET /api/v1/incidents/by-service`

Number of Teams and their related Services

- `GET /api/v1/teams/count`
- `GET /api/v1/teams`

Number of Escalation Policies and their Relationship with Teams and Services

- `GET /api/v1/escalation-policies/count`
- `GET /api/v1/escalation-policies`

CSV report of each of the above points

- `GET /api/v1/reports/services_count`
- `GET /api/v1/reports/incidents_count_per_service`
- `GET /api/v1/reports/incidents_status_count_by_service/:service_id`
- `GET /api/v1/reports/services`
- `GET /api/v1/reports/teams`
- `GET /api/v1/reports/services_teams`
- `GET /api/v1/reports/escalation_policies`
- `GET /api/v1/reports/escalation_policies_teams`
- `GET /api/v1/reports/escalation_policies_services`

Analysis of which Service has more Incidents and breakdown of Incidents by status

- `GET /api/v1/services/most-incidents`

Graph reflecting the previous point

- `GET /api/v1/services/chart`

Analysis of inactive users in Schedules

- `GET /api/v1/users/inactive`

## Architecture

### Components

- Flask REST API
- MySQL Database
- Analytics Service
- Metabase Dashboard
- PagerDuty API Client

### Design Patterns

- Repository Pattern (Data access)
- Observer Pattern (Data sync)
- Service Layer Pattern (Business logic)

## Setup

1. Clone the repository:

```bash
git clone https://github.com/aandrewsv/pagerduty-analytics.git
```

2. Create .env file:

```bash
cp .env.example .env
# Edit .env with your PagerDuty API key
```

3. Start services:

```bash
docker compose -f docker/docker-compose.yml up --build
```

4. Access:

- API: <http://localhost:5000/api>
- API Docs: <http://localhost:5000/api/docs>
- Metabase: <http://localhost:3000>

5. Finally make a POST Request to the sync endpoint to start the data synchronization:

```bash
curl -X POST http://localhost:5000/api/v1/sync
```

## All API Endpoints

### Services

- `GET /api/v1/services/count` - Total number of services
- `GET /api/v1/services` - List all services
- `GET /api/v1/services/{id}` - Get specific service details
- `GET /api/v1/services/{id}/incidents` - Get incidents for a service
- `GET /api/v1/services/most-incidents` - Service with most incidents + breakdown
- `GET /api/v1/services/chart` - Graph data for service with most incidents

### Incidents

- `GET /api/v1/incidents` - List all incidents
- `GET /api/v1/incidents/by-service` - Get Incidents grouped by service
- `GET /api/v1/incidents/by-status` - Incidents grouped by status
- `GET /api/v1/incidents/by-service-status` - Incidents grouped by service and status

### Teams

- `GET /api/v1/teams/count` - Total number of teams
- `GET /api/v1/teams` - List all teams

### Escalation Policies

- `GET /api/v1/escalation-policies/count` - Total number of escalation policies
- `GET /api/v1/escalation-policies` - List all escalation policies with teams and services

### Users

- `GET /api/v1/users/inactive` - List all inactive users in schedules

### Reports

- `GET /api/v1/reports/services_count` - Services count CSV report
- `GET /api/v1/reports/incidents_count_per_service` - Incidents count per service CSV report
- `GET /api/v1/reports/incidents_status_count_by_service/:service_id` - Incidents status count by service CSV report
- `GET /api/v1/reports/services` - All services CSV report
- `GET /api/v1/reports/teams` - All teams CSV report
- `GET /api/v1/reports/services_teams` - All Services and Teams Relationships CSV report
- `GET /api/v1/reports/escalation_policies` - All escalation policies CSV report
- `GET /api/v1/reports/escalation_policies_teams` - All escalation policies and teams relationships CSV report
- `GET /api/v1/reports/escalation_policies_services` - All escalation policies and services relationships CSV report

## Testing

Run tests (it will automatically build the image):

```bash
docker compose -f .\docker\docker-compose.test.yml run --rm test pytest -v
```

Note: run the project one time before running tests to ensure the database and its tables are properly created.

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License
