FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 ENABLE_WEB_INTERFACE=false HF_HUB_DISABLE_TELEMETRY=1
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY reconcile_lab /app/reconcile_lab
COPY openenv.yaml /app/openenv.yaml
RUN useradd --create-home --uid 10001 lab
USER lab
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"
CMD ["python", "-m", "reconcile_lab.app"]
