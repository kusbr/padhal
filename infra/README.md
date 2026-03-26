# Azure Container Apps (Single App, 3 Containers)

This deployment creates:

- 1 Log Analytics workspace
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
- Published images for:
1. `kumsub/padhal-api:<tag>`
2. `kumsub/padhal-frontend:<tag>`

## Deploy

Update image tags in [aca-single-app.parameters.json](/home/dev/learn/codex-cli/infra/aca-single-app.parameters.json), then run:

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

- Do not keep `replace-me` image tags; deployment will succeed but app startup will fail if images are missing.
- Redis is in-app for simplicity. For production, prefer Azure Cache for Redis.
