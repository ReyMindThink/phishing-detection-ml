# Demo lokal (BUKAN layanan). Model TIDAK ikut image: dipasang saat docker run.
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt
COPY src ./src
COPY docs/app_rules.json docs/model_manifest.json ./docs/
COPY samples ./samples
RUN useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 5000
# 0.0.0.0 hanya di dalam container; publikasikan ke host dengan -p 127.0.0.1:5000:5000
CMD ["python", "-c", "from src.app import buat_app; buat_app().run(host='0.0.0.0', port=5000, debug=False)"]
