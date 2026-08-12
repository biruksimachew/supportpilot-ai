FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system appgroup \
    && useradd --system \
        --gid appgroup \
        --create-home \
        appuser

COPY . .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

CMD ["python", "server.py"]