## Run CLI
```bash
docker-compose run cli
```

## Run Prefect Server with Minio and Agent
```bash
docker compose --profile server --profile minio --profile agent up
```

## Build or update a deployment
```bash
prefect deployment build -sb "remote-file-system/minio" -n "MLodImage" -q "awesome" "flow.py:greetings"
```
## Apply a deployment
```bash
prefect deployment apply greetings-deployment.yaml
```