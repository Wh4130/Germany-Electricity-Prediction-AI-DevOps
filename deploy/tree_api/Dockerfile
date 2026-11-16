# Build context: deploy/tree_api (run stage.sh first)
FROM python:3.13-slim

# LightGBM needs the OpenMP runtime, which the slim image does not have
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py service.py features.py ./
COPY artifacts/ ./artifacts/

ENV TREE_ARTIFACTS=/app/artifacts \
    PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
