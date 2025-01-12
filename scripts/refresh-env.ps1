# Stop all containers
docker compose -f .\docker\docker-compose.yml down

# Remove all images
docker compose -f .\docker\docker-compose.yml down --rmi all

# Remove volumes (optional, comment out if you want to keep data)
docker compose -f .\docker\docker-compose.yml down -v

# Clean Docker cache
docker builder prune -f

# Rebuild and start
docker compose -f .\docker\docker-compose.yml up --build