# Chronos Trade API — pure-stdlib Python service (no third-party deps).
# Build from the repo root:  docker build -f services/api/Dockerfile -t chronos-api .
FROM python:3.12-slim AS runtime

WORKDIR /app
COPY services/ ./services/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080
EXPOSE 8080

# Run as a non-root user.
RUN useradd --system --uid 10001 chronos && mkdir -p /data && chown chronos /data
USER chronos
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2).status==200 else 1)"

CMD ["python", "-m", "services.api.server"]
