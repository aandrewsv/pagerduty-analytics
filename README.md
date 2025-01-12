# PagerDuty Analytics System

A system for analyzing PagerDuty data with a focus on service incidents, team relationships, and escalation policies.

## Features

- Data synchronization with PagerDuty API
- MySQL database for data persistence and analysis
- RESTful API with OpenAPI documentation
- Metabase integration for data visualization
- Comprehensive test suite
- Dockerized project and tests

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

## API Endpoints

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

TODO

### Users

TODO

### Reports

TODO

## Testing

Run tests (it will automatically build the image):

```bash
docker compose -f .\docker\docker-compose.test.yml run --rm test pytest -v
```

## Code Quality

- Linting: `flake8 src/`
- Type checking: `mypy src/`
- Security: `bandit -r src/`

## Metabase Dashboard

TODO

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License
