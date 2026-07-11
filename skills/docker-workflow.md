# Docker Workflow Skill

Best practices for Docker development.

## Dockerfile Best Practices

### Multi-stage Build
```dockerfile
# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

# Runtime stage
FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
CMD ["./main"]
```

### Optimization Tips
```dockerfile
# Use specific tags, not latest
FROM node:20-alpine  # Good
FROM node:latest     # Bad

# Order layers by frequency of change
COPY package*.json ./
RUN npm install
COPY . .  # This layer changes often

# Use .dockerignore
# .dockerignore
node_modules
.git
*.md
.env
```

## Docker Compose

### Development Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8080:8080"
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Production Setup
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    environment:
      - NODE_ENV=production
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - app
```

## Common Commands

### Build & Run
```bash
# Build image
docker build -t myapp:latest .

# Run container
docker run -d -p 8080:8080 --name myapp myapp:latest

# Run with environment variables
docker run -d -e DATABASE_URL=postgres://... myapp:latest

# Run with volume mount
docker run -d -v $(pwd)/data:/app/data myapp:latest
```

### Management
```bash
# List running containers
docker ps

# List all containers
docker ps -a

# View logs
docker logs -f myapp

# Execute command in container
docker exec -it myapp sh

# Stop container
docker stop myapp

# Remove container
docker rm myapp

# Remove image
docker rmi myapp:latest
```

### Cleanup
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a
```

## Networking

### Create Network
```bash
# Create custom network
docker network create mynetwork

# Run containers in network
docker run -d --network mynetwork --name app myapp:latest
docker run -d --network mynetwork --name db postgres:15-alpine

# App can connect to db using hostname "db"
```

### Port Mapping
```bash
# Map to specific interface
docker run -d -p 127.0.0.1:8080:8080 myapp:latest

# Map multiple ports
docker run -d -p 8080:8080 -p 9090:9090 myapp:latest

# Map UDP ports
docker run -d -p 53:53/udp myapp:latest
```

## Volumes

### Named Volumes
```bash
# Create volume
docker volume create mydata

# Use volume
docker run -d -v mydata:/app/data myapp:latest

# Backup volume
docker run --rm -v mydata:/data -v $(pwd):/backup alpine \
  tar czf /backup/backup.tar.gz -C /data .

# Restore volume
docker run --rm -v mydata:/data -v $(pwd):/backup alpine \
  tar xzf /backup/backup.tar.gz -C /data
```

### Bind Mounts
```bash
# Mount current directory
docker run -d -v $(pwd):/app myapp:latest

# Mount with read-only
docker run -d -v $(pwd):/app:ro myapp:latest

# Mount specific file
docker run -d -v $(pwd)/config.json:/app/config.json myapp:latest
```

## Security

### Best Practices
```dockerfile
# Don't run as root
RUN adduser -D -u 1001 appuser
USER appuser

# Use read-only filesystem
docker run --read-only myapp:latest

# Limit capabilities
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myapp:latest

# Scan for vulnerabilities
docker scan myapp:latest
```

### Secrets Management
```bash
# Use Docker secrets
docker secret create db_password password.txt

# Use environment files
docker run --env-file .env myapp:latest

# Never commit .env files
echo ".env" >> .dockerignore
```

## Troubleshooting

### Common Issues
```bash
# Container exits immediately
docker logs myapp

# Port already in use
lsof -i :8080
docker kill $(docker ps -q --filter publish=8080)

# Permission denied
docker run -u $(id -u):$(id -g) myapp:latest

# Out of disk space
docker system prune -a
docker volume prune
```

### Debugging
```bash
# Enter container
docker exec -it myapp sh

# View running processes
docker top myapp

# View resource usage
docker stats myapp

# Inspect container
docker inspect myapp
```
