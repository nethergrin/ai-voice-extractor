# Docker Setup Guide

This project includes Docker and Docker Compose configurations for easy deployment and development.

## Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 1.29+)

## Quick Start

### Production Build

Run both backend and web client in production mode:

```bash
docker-compose up --build
```

This will:
1. Build the backend Docker image
2. Build the web client Docker image
3. Start both services
4. Create a shared network and volumes

Access the application at:
- **Web Client**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Development Build

For development with hot reload and live reloading:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

Changes to source files will be reflected immediately without rebuilding the containers.

## Services

### Backend Service

- **Image**: Python 3.11 slim
- **Port**: 8000
- **Database**: SQLite (at `./app.db`)
- **Audio Storage**: Volume at `/app/audio_storage`
- **Hot Reload**: Available in dev mode with `--reload` flag

**Environment Variables:**
- `DATABASE_URL`: SQLite database connection string
- `AUDIO_STORAGE_PATH`: Path to store audio files
- `DEBUG`: Enable/disable debug mode

### Web Service

- **Image**: Node 18 Alpine (multi-stage build)
- **Port**: 3000
- **Build Stage**: Compiles React with npm
- **Runtime Stage**: Serves with `serve` package
- **API URL**: Configured via `REACT_APP_API_URL`

**Environment Variables:**
- `REACT_APP_API_URL`: Backend API endpoint

## Volumes

### Persistent Volumes

- `audio_storage`: Stores uploaded audio files (survives container restarts)

### Bind Mounts (Development Only)

- Backend: `./backend/app` → `/app/app` (for hot reload)
- Web: `./clients/web/src` → `/app/src` (for hot reload)
- Web: `./clients/web/public` → `/app/public` (for hot reload)

## Networking

Both services are connected via a Docker network named `app-network`, allowing them to communicate via service names (e.g., `http://backend:8000`).

## Health Checks

Both services include health checks:

**Backend**: Checks `/health` endpoint every 30s
**Web**: Checks HTTP response every 30s

## Common Commands

### Start Services
```bash
docker-compose up
```

### Start in Background
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Stop and Remove Volumes
```bash
docker-compose down -v
```

### View Logs
```bash
docker-compose logs -f
```

### View Specific Service Logs
```bash
docker-compose logs -f backend
docker-compose logs -f web
```

### Rebuild Images
```bash
docker-compose build --no-cache
```

### Run Command in Container
```bash
docker-compose exec backend /bin/bash
docker-compose exec web /bin/sh
```

## Configuration

### Environment Variables

Create a `.env` file in the project root or modify `docker-compose.yml` to set environment variables:

```env
# Backend
DATABASE_URL=sqlite:///./app.db
AUDIO_STORAGE_PATH=/app/audio_storage
DEBUG=False

# Web Client
REACT_APP_API_URL=http://localhost:8000/api/v1
```

### Port Mapping

Edit `docker-compose.yml` to change port mappings:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Change backend port to 8001
  web:
    ports:
      - "3001:3000"  # Change web port to 3001
```

## Multi-Stage Builds

The Dockerfiles use multi-stage builds for optimization:

**Backend**: Single stage (Python runtime)
**Web**: Two stages (Node build → runtime with serve)

## Production Considerations

For production deployment:

1. **Use PostgreSQL instead of SQLite**:
   ```env
   DATABASE_URL=postgresql://user:password@postgres-service:5432/dbname
   ```

2. **Set DEBUG=False** in environment

3. **Use separate `.env.production`** file with secrets

4. **Configure reverse proxy** (nginx) in front of services

5. **Use persistent volumes** for audio storage with proper backup

6. **Scale services** with Docker Swarm or Kubernetes

## Troubleshooting

### Connection Refused

If you see "connection refused" errors:
- Ensure services are running: `docker-compose ps`
- Check service names in connections (e.g., `http://backend:8000`)
- Review logs: `docker-compose logs`

### Port Already in Use

If ports 3000 or 8000 are in use:
- Change ports in `docker-compose.yml`
- Or stop the conflicting service: `lsof -i :8000`

### Database Connection Issues

- Ensure `DATABASE_URL` is correctly set
- Check database file permissions in volume
- View logs for detailed error messages

### Audio Storage Issues

- Verify volume mount: `docker volume inspect ai-voice-extractor_audio_storage`
- Check file permissions in the container
- Ensure sufficient disk space

## Development Workflow

1. Start development environment:
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

2. Edit source files (changes reload automatically)

3. View logs to verify changes:
   ```bash
   docker-compose logs -f
   ```

4. Stop when done:
   ```bash
   docker-compose down
   ```
