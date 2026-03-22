Build and push both images to a registry your cluster can reach, then update the image names in the manifests:

```bash
docker build -f Dockerfile.api -t your-registry/padhal-api:latest .
docker build -f Dockerfile.frontend -t your-registry/padhal-frontend:latest .
docker push your-registry/padhal-api:latest
docker push your-registry/padhal-frontend:latest
```

Update:

- `k8s/api-deployment.yaml`
- `k8s/frontend-deployment.yaml`

Apply everything with:

```bash
kubectl apply -k k8s/
```

This setup deploys Redis alongside the API so game state is shared across API replicas. The API reads `REDIS_URL=redis://padhal-redis:6379/0`.

This setup expects an Ingress controller in the cluster. The frontend is served at `/` and the API is routed at `/api`.

If your cluster does not have Ingress, expose the frontend and API separately with `LoadBalancer` or `NodePort` services and adjust the frontend API base URL accordingly.
