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
FROM 
```

---

## Environment Configuration

The application relies on several environment variables. Below is a minimal `.env` example:

```dotenv
# Flask secret keys
SECRET_KEY=super-secret-key
JWT_SECRET_KEY=jwt-super-secret

# Flask‑Mail configuration (example using MailHog)
MAIL_SERVER=mailhog
MAIL_PORT=1025
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=no-reply@example.com

# AWS credentials (required for any AWS integrations)
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
```

**Important:**  
- Do **not** commit the `.env` file or any secret values to version control.  
- When deploying via GitHub Actions, store `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as **encrypted repository secrets**.  
- A helper script `set_github_secrets.sh` is provided to automate adding these secrets to the repository using the GitHub CLI.

---

## API Documentation

*(Documentation placeholder – add your API specs here.)*

---

## Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a pull request.

---

## License

MIT License. See `LICENSE` file for details.