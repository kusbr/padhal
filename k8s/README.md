The workflow publishes commit-SHA image tags to Docker Hub, not `latest`.

Use a specific published tag in Compose or Kubernetes:

```bash
kumsub/padhal-api:<git-sha>
kumsub/padhal-frontend:<git-sha>
```

For Docker Compose:

```bash
export PADHAL_API_TAG=<git-sha>
export PADHAL_FRONTEND_TAG=<git-sha>
docker compose -f docker/docker-compose.yml up
```

For Kubernetes, update:

- `k8s/api-deployment.yaml`
- `k8s/frontend-deployment.yaml`

and replace `replace-me` with the exact published image tag.

Apply everything with:

```bash
kubectl apply -k k8s/
```

This setup deploys Redis alongside the API so game state is shared across API replicas. The API reads `REDIS_URL=redis://padhal-redis:6379/0`.

This setup expects an Ingress controller in the cluster. The frontend is served at `/` and the API is routed at `/api`.

If your cluster does not have Ingress, expose the frontend and API separately with `LoadBalancer` or `NodePort` services and adjust the frontend API base URL accordingly.

## Helm

A Helm chart is available in `helm/padhal`.

The GitHub Actions workflow packages the chart with `appVersion` set to the current commit SHA. The chart templates default image tags to `.Chart.AppVersion` when no explicit values override is provided.

Deploy with a specific SHA:

```bash
helm upgrade --install padhal ./helm/padhal \
  --namespace padhal \
  --create-namespace \
  --set global.imageTag=<git-sha>
```
