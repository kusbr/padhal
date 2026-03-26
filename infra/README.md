# Azure Container Apps (Single App, 3 Containers)

This deployment creates:

- 1 Log Analytics workspace
- 1 User-assigned managed identity (for ACR pull)
- 1 Container Apps managed environment
- 1 Azure Container App with 3 containers:
1. `api` (`0.5 CPU`, `1Gi`)
2. `frontend` (`0.25 CPU`, `0.5Gi`)
3. `redis` (`0.25 CPU`, `0.5Gi`)

Ingress is mapped to the `api` container on port `8000`.

## Why ingress points to `api`

A single Container App exposes one ingress target port per revision.  
To keep `/api/*` and gameplay working without extra reverse-proxy config, this template routes traffic to `api`.

## Prerequisites

- Azure CLI logged in: `az login`
- Existing resource group in `southindia` (or change location in params)
- Deploy Azure Container Registry first (same resource group)
- ACR has images:
1. `<acr-login-server>/padhal-api:latest`
2. `<acr-login-server>/padhal-frontend:latest`

## Deploy

1. Create ACR in the same resource group:

```bash
az deployment group create \
  --resource-group <your-rg> \
  --template-file infra/container-registry.bicep \
  --parameters namePrefix=padhal acrName=<globally-unique-acr-name>
```

2. Update ACR values in [aca-single-app.parameters.json](/home/dev/learn/codex-cli/infra/aca-single-app.parameters.json), then deploy Container App:

```bash
az deployment group create \
  --resource-group <your-rg> \
  --template-file infra/aca-single-app.bicep \
  --parameters @infra/aca-single-app.parameters.json
```

Get app URL:

```bash
az containerapp show \
  --name padhal-app \
  --resource-group <your-rg> \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

## Notes

- Container App uses a user-assigned managed identity with `AcrPull` role on ACR.
- Default images point to `:latest` tags in ACR.
- Redis is in-app for simplicity. For production, prefer Azure Cache for Redis.
