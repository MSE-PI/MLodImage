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

## API call
```bash
curl -X 'POST' \
  'http://prefect-server:4200/api/deployments/03a44ad2-cf9f-4c81-8c54-7bd1d6bfaecd/create_flow_run' \
  -H 'accept: application/json' \
  -H 'x-prefect-api-version: 0.8.4' \
  -H 'Content-Type: application/json' \
  -d '{
  "state": {
    "type": "SCHEDULED"
  },
  "name": "my-flow-run"
}'
```

## URL's
```bash
# Add to /etc/hosts
nano /etc/hosts
# Add the following lines
127.0.0.1       prefect-server
```

- **Prefect Server:** http://prefect-server:4200
- **Prefect API:** http://prefect-server:4200/docs
- **Minio:** http://prefect-server:9001