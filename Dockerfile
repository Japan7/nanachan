FROM cgr.dev/chainguard/wolfi-base:latest

# renovate: datasource=docker depName=python
ARG PYTHON_VERSION=3.12

ENV POETRY_VIRTUALENVS_IN_PROJECT=1

RUN apk add --no-cache python-${PYTHON_VERSION} py${PYTHON_VERSION}-pip ffmpeg opus

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN apk add --no-cache --virtual .build-deps build-base python-${PYTHON_VERSION}-dev && \
    pip install poetry && \
    poetry install --without dev --no-root && \
    apk del --purge .build-deps && \
    rm -rf ~/.cache/

COPY nanachan nanachan
COPY README.md .
RUN poetry install --only-root

ENTRYPOINT [ "poetry", "run", "nanachan" ]
