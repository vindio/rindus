# Rindus


## Getting Started 🏁

1. **Clone the repository:**
    ```bash
    git clone https://github.com/vindio/rindus.git
    ```

2. **Change directory into the project:**
    ```bash
    cd rindus
    ```

3. **Create env files:**


   - **For Linux/macOS:**
     ```bash
     mkdir .envs

     touch .env .envs/django .envs/postgres

     ```

    .env example
     ```
    USE_DOCKER=yes
    POSTGRES_HOST=postgres
    POSTGRES_PORT=5432
    POSTGRES_LOCAL_PORT=5432
    POSTGRES_DB=rindus_blog
    POSTGRES_USER=django_db_user
    POSTGRES_PASSWORD=secret_password
    DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
     ```

    .envs/django example
     ```
    USE_DOCKER=yes
    IPYTHONDIR=/app/.ipython
    DJANGO_PORT=8080
     ```

    .envs/postgres example
     ```
    POSTGRES_HOST=postgres
    POSTGRES_PORT=5432
    POSTGRES_LOCAL_PORT=5432
    POSTGRES_DB=rindus_blog
    POSTGRES_USER=django_db_user
    POSTGRES_PASSWORD=secret_password
     ```
---

## Initial Setup ⚙️

### Development Prerequisites

1. **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

2. **Activate the virtual environment:**
    ```bash
    source venv/bin/activate
    ```

3. **Install the development requirements.**
    ```bash
    pip install -r requirements/local.txt
    ```

4. **Build the image and run the container:**

   - Build docker image
     ```bash
     docker compose build
     ```

   - Run containers
     ```bash
     docker compose up -d
     ```

You can now access the application at http://localhost:8000.
