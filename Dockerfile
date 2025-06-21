FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy project metadata and lock file
COPY pyproject.toml ./

# Install dependencies
RUN pip install --upgrade pip \
    && pip install .

# Copy the rest of the source code
COPY . .

ENTRYPOINT ["python", "main.py"]
