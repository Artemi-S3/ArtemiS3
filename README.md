# Quick Start Guide — ArtemiS3 Development Environment

## Overview
A guide for setting up and running ArtemiS3 for local development.  
**The project uses:**
- **Svelte (Vite)** for the frontend  
- **FastAPI** for the backend  
- **NGINX** as a reverse proxy  
All components run inside Docker containers.

---

## 1. Install Prerequisites
Make sure the following are installed on your computer:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Git](https://git-scm.com/)

Verify installations:
```bash
docker --version
docker compose version
git --version
```

## 2. Clone the Repository
```bash
git clone <repo_url>
cd artemis3
```

## 3. Build and Start the Project
This command builds the frontend, backend, and NGINX images, creates the network, and starts everything.

```bash
# first time
docker compose up --build
# every other time
docker compose up
```

- The first build may take several minutes.
- Leave this command running while developing.
- Use Ctrl + C to stop the stack.
- Run using `-d` option to run in detached mode (to use terminal while running).

## 4. Access the Running Services
| Service               | URL	                     | Description               |
| --------------------- | -------------------------- |-------------------------- |
| Frontend (via NGINX)  | http://localhost	         | Main Svelte web app       |
| Backend API	        | http://localhost:8000/api/ | Start of endpoints        |
| Vite Dev Server	    | http://localhost:5173	     | Svelte live reload server |

## 5. Verify the Connection
Run this test from your terminal:

```bash
curl http://localhost/api/test?name=Svelte
```
Expected response:

```json
{"message": "Hello, Svelte!"}
```
If that appears, the frontend --> NGINX --> backend communication works correctly.

## 6. Developing Locally
- Frontend changes:<br>
Edit files in frontend/src/. The app reloads automatically.

- Backend changes:<br>
Edit files in backend/app/. Uvicorn reloads the API automatically.

- Rebuild if dependencies change:
```bash
docker compose build
docker compose up
```

## 7. Stopping and Cleaning Up
Stop all containers:
```bash
docker compose down
```

If you want to remove unused images, volumes, and networks:
```bash
docker system prune
```

## 8. Common Issues
**Port already in use:** Change ports in `docker-compose.yml` or stop other apps using 80, 5173, or 8000.

**Nothing loads on localhost:** Wait for all containers to finish building, or check logs:
```bash
docker compose logs -f
```

**Backend not reachable:**<br>
Test directly:
```bash
curl http://localhost:8000/api/test
```