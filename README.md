# ACEest Fitness & Gym


This is a project to modernise the ACEest Fitness app and convert it from a desktop application into a web application.

---

## What the app does

- Login for gym staff (default user: `admin` / `password123`)
- Add a client with just a name and a program (Fat Loss, Muscle Gain, Beginner)
- Client profile page to add age, height, weight and membership end date
- Generate a workout plan for the client

Data is saved in a SQLite file (`aceest.db`).

---

## Project files

```
app.py                     Flask app
templates/                 HTML pages
tests/                     Pytest tests
requirements.txt           Python packages
Dockerfile                 Docker image
Jenkinsfile                Jenkins pipeline
.github/workflows/main.yml GitHub Actions pipeline
aceest_fitness.py          Old Tkinter app (kept only for reference)
```

---

## Run it locally

You need Python 3.9 or newer.

```bash
git clone https://github.com/adi-bits-2025/aceest-fitness.git
cd aceest-fitness

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python app.py
```

Open http://localhost:5000 and log in with `admin` / `password123`.

---

## Run the tests

```bash
source .venv/bin/activate
pytest -v
```

- `tests/test_logic.py` tests the logic: calories, BMI, membership and program generator.
- `tests/test_routes.py` tests the pages and API: login, add client, profile, progress, workouts.

Each test uses its own temporary database, so it does not touch `aceest.db`.

---

## Run with Docker

```bash
docker build -t aceest-fitness .
docker run --rm aceest-fitness pytest -v          # run tests inside the container
docker run --rm -p 5000:5000 aceest-fitness       # run the app
```

The Dockerfile uses the small `python:3.12-slim` image, installs packages without cache and runs the app as a normal user (not root).

---

## CI/CD

### GitHub Actions

File: `.github/workflows/main.yml`

It runs on every push and every pull request:

1. **Build & Lint** - install packages and check the code for syntax errors with flake8
2. **Docker build** - build the Docker image
3. **Test** - run pytest inside the Docker container

### Jenkins

File: `Jenkinsfile`

Jenkins runs on the PRAYOGSHALA lab machine. The job is a Pipeline job that reads the `Jenkinsfile` from the `main` branch of this repo and checks GitHub every 5 minutes for new commits.

1. **Checkout** - pull the latest code from GitHub
2. **Build** - create a fresh Python virtual environment and install packages
3. **Test** - run pytest and show the results in Jenkins

The lab machine's Jenkins user does not have Docker access, so Jenkins uses a Python venv. The Docker build is already checked in GitHub Actions.

### How they work together

```
feature branch --push--> GitHub Actions (lint, docker build, tests)
      |
   pull request --------> GitHub Actions runs again
      |
   merge to main -------> Jenkins picks it up and does a clean build + tests
```

GitHub Actions checks every change before it is merged.
Jenkins is a second check on `main` in a separate build environment.

---

## Git workflow

- Each feature is done on its own branch, for example `feature/flask-app`,
  `test/pytest-suite`, `infra/docker`.
- The branch is merged to `main` using a pull request.
- The first commits show how the old desktop app grew (v1.0 to v3.2.4) before
  I moved it to Flask.

---
