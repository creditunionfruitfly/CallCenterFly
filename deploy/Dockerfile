FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir '.[serve]'

RUN useradd --create-home --uid 10001 callcenterfly \
    && mkdir -p /app/logs \
    && chown -R callcenterfly:callcenterfly /app/logs
USER callcenterfly

EXPOSE 8080
CMD ["callcenterfly", "serve", "--host", "0.0.0.0", "--port", "8080"]
