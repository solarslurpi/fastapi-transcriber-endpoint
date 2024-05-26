# Fastapi Service
The FastAPI service is bundled as a Docker Container to ensure consistent deployment across different environments and to streamline the application setup process.

# Build The Image
```bash
docker build -t obsidian-transcriber-service:latest .
```

The command `docker build -t obsidian-transcriber-service:latest .` builds a Docker image from the [Dockerfile](../../dockerfile) in the current directory (.) and tags the resulting image with the name obsidian-transcriber-service and the tag latest.


## See Log Files
```bash
docker logs obsidian-transcriber-service
```

## Run the Service Locally
To run the Docker container locally, make sure the bash script [start_service.sh](../../start_service.sh) is an executable: `chmod +x start_service.sh`.  The type `./start_service.sh` at the bash command line to start the obsidian-transcriber-service running.

The bash file relies a [Docker Compose](../../docker-compose.yml) File that specifies the configuration for running the obsidian-transcriber-service Docker container with GPU support, port mapping, and a restart policy, using Docker Compose file format version 3.8.

docker push solarslurpie/obsidian-transcriber-service:latest



```
docker tag obsidian-transcriber-service:latest <Docker hub username>/obsidian-transcriber-service:latest
docker login
docker push <Docker hub username>/obsidian-transcriber-service:latest

```

## Logging
The [logging module]


# Navigate to the directory with your docker-compose.yml
cd path/to/your/docker-compose-directory

# Stop and remove containers, networks, and volumes
docker-compose down

# Or stop containers without removing them
docker-compose stop

# Start containers again if you stopped them without removing
docker-compose start
