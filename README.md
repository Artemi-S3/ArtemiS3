# ArtemiS3
This document aims to provide a delivery-focused user manual for installing, configuring, operating, and maintaining ArtemiS3.

## Introduction

ArtemiS3 is a web application for searching and exploring NASA and USGS data stored in public AWS S3 buckets. It indexes bucket contents into Meilisearch and provides a browser UI for query, filtering, sorting, previewing, downloading, and tagging files.

Core stack:

- Frontend: Svelte (TypeScript) + TailwindCSS
- Backend API: FastAPI (Python)
- Search engine: Meilisearch
- Metadata/tags store: PostgreSQL
- Reverse proxy: NGINX
- Orchestration: Docker Compose

## Installation

### Local Development Installation

#### Required software

- **Git**
- **Docker**
- **Docker Compose**
- Optional: **Visual Studio Code**
- Optional on Windows: **WSL**

Verify tools:

```bash
docker --version
docker compose version
git --version
```

#### Clone repository

```bash
git clone https://github.com/Artemi-S3/ArtemiS3.git
cd ArtemiS3
```

#### Start application

Run from the project root:

```bash
docker compose up -d --build
```

Notes:

- First startup may take several minutes.
- `frontend-test` and `backend-test` run as one-shot containers before app containers are considered healthy.

#### Verify containers

```bash
docker ps
```

Expected running service containers include:

- `nginx`
- `frontend`
- `backend`
- `meilisearch`
- `postgres`

Test containers (`frontend-test`, `backend-test`) should complete and exit successfully.

#### Access services

| Service | URL | Purpose |
| --- | --- | --- |
| Frontend (via NGINX) | http://localhost | Primary ArtemiS3 UI |
| Backend API (direct) | http://localhost:8000/api/ | FastAPI endpoint base |
| Vite dev server (direct) | http://localhost:5173 | Frontend dev server |

#### Stop / restart / rebuild

```bash
# stop (CTRL + C to exit logs)
docker compose down

# restart without rebuild
docker compose up -d

# rebuild after dependency or image changes
docker compose up -d --build
```

## Configuration and Daily Operation

### Configure indexed S3 buckets

ArtemiS3 indexes one or more public S3 URIs through `REFRESH_BUCKETS`.

Current default fallback is in `backend/app/main.py`. You can:

1. Update the fallback value directly in code, or
2. Pass `REFRESH_BUCKETS` as a backend container environment variable in `docker-compose.yml`.

Value format:

```text
REFRESH_BUCKETS=s3://example-bucket-1,s3://example-bucket-2/path-prefix
```

After changing bucket targets, restart backend:

```bash
docker compose restart backend
```

### Configure refresh interval

`REFRESH_INTERVAL_SECONDS` controls how often bucket refresh runs.

Examples:

- Every hour (default): `3600`
- Every 30 minutes: `1800`
- Every day: `86400`

Set it the same way as `REFRESH_BUCKETS` (code fallback or container environment), then restart backend.

### Monitor user file tags

File tags are stored in Postgres and improve search organization. Operationally, monitor for excessive tagging on single objects, which may affect performance and usability over time.

Recommended future hardening:

- Tag validation rules
- Tag count limits per file
- Admin moderation controls

### End-user operations

Typical daily use:

1. Open ArtemiS3 in the browser.
2. Search by keyword, mission term, filename, metadata, or type.
3. Set result limit and optional filters.
4. Review in table or folder mode.
5. Sort by filename, size, or last-modified date.
6. Preview supported files.
7. Download needed files.
8. Add/edit/remove tags for future discovery.

## Maintenance

ArtemiS3 is designed for low-touch operation, but the tasks below are useful for recovery and migration.

### System Pruning

Use with care. This removes containers and can remove volumes/data.

```bash
docker compose down
docker system prune
```

If you need to remove all Docker volumes:

```bash
docker volume rm $(docker volume ls -q)
```

### Delete a Meilisearch Index

When a bucket is removed from tracking or you need a full reindex:

```bash
curl -X DELETE "localhost:7700/indexes/{index_name}"
```

### Postgres backup and restore

Create backup archive:

```bash
docker run --rm -v artemis3_postgres_data:/postgresql -v "$(pwd)":/backup busybox tar cvf /backup/postgres_volume_backup.tar /postgresql
```

Restore into a new volume:

```bash
docker run --rm -v postgres_data:/postgresql -v "$(pwd)":/backup ubuntu bash -c "cd /postgresql && tar -xvf /backup/postgres_volume_backup.tar"
```

If restoring to a new stack, ensure the destination Compose config uses the intended Postgres volume name.

## Troubleshooting

### Restart stack

```bash
docker compose down
docker compose up --build
```

### View logs

```bash
docker compose logs -f
docker logs <container_name>
```

### Meilisearch quick checks

```bash
curl -X GET "localhost:7700/indexes"
curl -X GET "localhost:7700/tasks?statuses=failed"
curl -X GET "localhost:7700/stats"
curl -X GET "localhost:7700/indexes/{index_uid}/documents/{document_id}"
```

## Team Contact

- Joseph Laity - jbl265@nau.edu
- Jeffrey Hoelzel Jr. - jmh2338@nau.edu
- Samuel Bodenheimer - swb79@nau.edu
- Travian Lenox - tjl379@nau.edu
