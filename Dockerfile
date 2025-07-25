# Effectively this will be debian:bookworm-slim - see https://docs.astral.sh/uv/guides/integration/docker/#available-images
FROM ghcr.io/astral-sh/uv:debian-slim
RUN mkdir -p /hntags/output
WORKDIR /hntags
COPY src src
COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
COPY README.md README.md
RUN uv sync
COPY docker_scripts/run run
ENTRYPOINT [ "/hntags/run" ]