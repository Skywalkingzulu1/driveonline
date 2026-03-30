# Drive Online

Drive Online is a lightweight web application built with **Flask** that provides a simple dashboard for driver job listings, user registration, authentication, and email verification. It is designed to be easy to set up, extend, and deploy using Docker.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running Locally](#running-locally)
- [Docker Usage](#docker-usage)
- [Environment Configuration](#environment-configuration)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Project Overview

Drive Online offers a clean UI for browsing driver job listings and includes the following core features:

- **User registration & login** with password hashing (bcrypt) and JWT token generation.
- **Email verification** using Flask‑Mail and itsdangerous token serializer.
- **Job listings** displayed dynamically on the front‑end.
- **Static file serving** (CSS, images) directly from the project root.
- **Docker support** for easy containerised deployment.

---

## Technology Stack

| Layer | Technology |
|-------|-------------|
| Backend | Python 3.11+, Flask, Flask‑Login, Flask‑Mail, PyJWT |
| Authentication | JWT, bcrypt |
| Data Store | In‑memory dictionary (easy to replace with a DB) |
| Front‑end | HTML5, CSS3, vanilla JavaScript |
| Containerisation | Docker |
| Testing | pytest, pytest‑asyncio |
| Configuration | python‑dotenv, pydantic‑settings |

---

## Prerequisites

- **Python 3.11+** (or use the provided Docker image)
- **Git**
- **Docker** (optional, for containerised run)
- **Node.js** (only if you plan to extend the front‑end with tooling)

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Skywalkingzulu1/driveonline.git
   cd driveonline
   ```

2. **Create a virtual environment** (recommended)

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env` file in the project root (see [Environment Configuration](#environment-configuration) for details).

---

## Running Locally

```bash
export FLASK_APP=app.py
export FLASK_ENV=development   # Enables debug mode
flask run
```

The application will be available at `http://127.0.0.1:5000`.

---

## Docker Usage

### Build the image

```bash
docker build -t driveonline:latest .
```

### Run the container

```bash
docker run -d -p 8000:8000 \
  -e SECRET_KEY=super-secret-key \
  -e JWT_SECRET_KEY=jwt-super-secret \
  -e MAIL_SERVER=mailhog \
  -e MAIL_PORT=1025 \
  --name driveonline \
  driveonline:latest
```

The app will be reachable at `http://localhost:8000`.

### Dockerfile (included)

```dockerfile
# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose the port Flask runs on
EXPOSE 8000

# Set environment variables (can be overridden at runtime)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8000

# Run the application
CMD ["flask", "run"]
```

---

## Environment Configuration

Create a `.env` file in the project root (or set the variables in your deployment environment). Example:

```dotenv
# Core secrets
SECRET_KEY=super-secret-key
JWT_SECRET_KEY=jwt-super-secret

# JWT settings
JWT_ALGORITHM=HS256
JWT_EXP_DELTA_SECONDS=3600

# Flask-Mail (using MailHog for local testing)
MAIL_SERVER=localhost
MAIL_PORT=1025
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_USE_TLS=false
MAIL_USE_SSL=false
MAIL_DEFAULT_SENDER=no-reply@example.com
```

**Important:** Never commit real secrets to version control. Use a secret manager in production.

---

## API Documentation

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/register` | `POST` | Register a new user (email, password, full_name). Sends verification email. | No |
| `/login` | `POST` | Authenticate user, returns JWT token. | No |
| `/verify/<token>` | `GET` | Verify email address using token from email. | No |
| `/jobs` | `GET` | Retrieve list of job listings (static JSON in front‑end). | Optional (JWT can be added later) |
| `/protected` | `GET` | Example protected route – requires valid JWT. | Yes (Bearer token) |

*All responses are JSON formatted.*

---

## Contributing

Contributions are welcome! Follow these steps:

1. Fork the repository.
2. Create a feature branch:

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Make your changes and ensure tests pass:

   ```bash
   pytest
   ```

4. Commit and push your changes.
5. Open a Pull Request describing the changes.

### Code Style

- Use **PEP 8** conventions.
- Run `flake8` before committing.
- Keep the `requirements.txt` up‑to‑date (`pip freeze > requirements.txt`).

---

## License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.