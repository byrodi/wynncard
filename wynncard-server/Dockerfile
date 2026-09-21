# Build from the repository root: docker build -f wynncard-server/Dockerfile -t wynncard-server .
FROM python:3.12-slim
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY wynncard ./wynncard
COPY wynncard-server ./wynncard-server
RUN pip install --no-cache-dir . ./wynncard-server
ENV RENDER_HOST=0.0.0.0
EXPOSE 8765
CMD ["wynncard-server"]
