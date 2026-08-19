FROM node:24-slim@sha256:6f7b03f7c2c8e2e784dcf9295400527b9b1270fd37b7e9a7285cf83b6951452d AS frontend
WORKDIR /frontend
COPY caos/frontend/package.json caos/frontend/package-lock.json ./
RUN npm ci
COPY caos/frontend/ ./
RUN npm run build

FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOST=0.0.0.0 PORT=8000 ENVIRONMENT=production
WORKDIR /app
COPY caos/server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY caos/server/ ./
COPY caos/deploy/verify_image_resources.py ./verify_image_resources.py
COPY --from=frontend /frontend/out ./static
RUN useradd -m -u 10001 caos && mkdir -p /vault && chown -R caos:caos /app /vault
USER caos
RUN python -m compileall -q .
RUN python verify_image_resources.py
EXPOSE 8000
CMD ["python", "run.py"]
