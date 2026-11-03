FROM ghcr.io/astral-sh/uv:0.11.8@sha256:3b7b60a81d3c57ef471703e5c83fd4aaa33abcd403596fb22ab07db85ae91347 AS uv
FROM python:3.14.4-slim-bookworm@sha256:fc74d22ffd0d5ac395a4b7bdda75a4539758862c49ebf3005647084631e63789
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /simulator
COPY tools/pas600_simulator/pyproject.toml tools/pas600_simulator/uv.lock ./
COPY tools/pas600_simulator/src ./src
RUN uv sync --locked --no-dev && useradd --uid 10001 --create-home demo
COPY deploy/demo/demo_profile.py deploy/demo/runner.py /runner/
ENV PATH="/simulator/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PAS600_SIM_STATE_DIRECTORY=/demo/state
USER demo
CMD ["python", "/runner/runner.py"]
