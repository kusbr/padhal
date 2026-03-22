# Padhal

Padhal is a browser-based five-letter word game inspired by Wordle.

The name blends Sanskrit `padam` with `Wordle`. The UI is branded as **Padhal** and shows the Devanagari form **पदल**.

Padhal uses:
- Datamuse to fetch candidate five-letter words
- `dictionaryapi.dev` to validate words and fetch definitions
- Redis for shared game state when running in containerized or multi-replica setups

Padhal is an unofficial word game. Word definitions and candidate words are provided by third-party APIs and may occasionally be unavailable or inconsistent.

## Architecture

The backend is structured as a three-layer system:

1. Frontend layer
   - Static UI served from [static/index.html](/home/dev/learn/codex-cli/static/index.html) and [static/app.js](/home/dev/learn/codex-cli/static/app.js)
2. API layer
   - HTTP server in [padhal_app/api.py](/home/dev/learn/codex-cli/padhal_app/api.py)
3. Repository and service layer
   - Domain rules: [padhal_app/domain.py](/home/dev/learn/codex-cli/padhal_app/domain.py)
   - External API repositories: [padhal_app/repositories.py](/home/dev/learn/codex-cli/padhal_app/repositories.py)
   - Game orchestration and storage: [padhal_app/services.py](/home/dev/learn/codex-cli/padhal_app/services.py)

## Run Locally

Start the API and frontend server together:

```bash
cd /home/dev/learn/codex-cli
python3 padhal_api.py
```

Open:

```text
http://127.0.0.1:8000
```

Terminal version:

```bash
python3 padhal.py
```

## Run With Docker Compose

This starts:
- `padhal-frontend`
- `padhal-api`
- `padhal-redis`

```bash
docker compose up --build
```

Frontend:

```text
http://127.0.0.1:8080
```

API:

```text
http://127.0.0.1:8000
```

## Run On Kubernetes

Kubernetes manifests are under [k8s](/home/dev/learn/codex-cli/k8s).

Build and push the images:

```bash
docker build -f Dockerfile.api -t your-registry/padhal-api:latest .
docker build -f Dockerfile.frontend -t your-registry/padhal-frontend:latest .
docker push your-registry/padhal-api:latest
docker push your-registry/padhal-frontend:latest
```

Update image references in:
- [k8s/api-deployment.yaml](/home/dev/learn/codex-cli/k8s/api-deployment.yaml)
- [k8s/frontend-deployment.yaml](/home/dev/learn/codex-cli/k8s/frontend-deployment.yaml)

Apply:

```bash
kubectl apply -k k8s/
```

The Kubernetes deployment includes Redis so API replicas can share game state.

## Deploy With Helm

A Helm chart is available under [helm/padhal](/home/dev/learn/codex-cli/helm/padhal).

The GitHub Actions workflow packages this chart with:
- `appVersion = <github.sha>`
- Docker images already published with the same commit SHA tag

The chart defaults image tags in this order:
1. `.Values.api.image.tag` / `.Values.frontend.image.tag`
2. `.Values.global.imageTag`
3. `.Chart.AppVersion`

That means the packaged chart artifact from CI will naturally use the commit SHA as the image tag.

Example local install with an explicit tag:

```bash
helm upgrade --install padhal ./helm/padhal \
  --namespace padhal \
  --create-namespace \
  --set global.imageTag=<git-sha>
```

## API Endpoints

- `POST /api/games`
- `GET /api/games/<game_id>`
- `POST /api/games/<game_id>/guesses`

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/games
```

## Development Notes

- The frontend auto-creates a game for a new browser session.
- Typing works directly on the board. On mobile, tapping the board opens the software keyboard.
- Duplicate guesses are rejected.
- Invalid English words are rejected.
- Game state is thread-safe in-process and Redis-backed when `REDIS_URL` is configured.

## Tests

Run:

```bash
python3 -m unittest -v
```
