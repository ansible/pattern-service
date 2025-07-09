FROM registry.access.redhat.com/ubi9/ubi:latest AS base

ARG USER_ID=${USER_ID:-1001}
ARG PYTHON_BIN="python3.11"

RUN useradd --uid "$USER_ID" --gid 0 --home-dir /app --create-home pattern \
    && mkdir -p /app/.local \
    && chown -R "${USER_ID}:0" /app/.local \
    && chmod 0775 /app


RUN dnf -y install dnf-plugins-core git \
    && dnf -y install ${PYTHON_BIN} ${PYTHON_BIN}-devel ${PYTHON_BIN}-pip\
    && dnf -y clean all \
    && rm -rf /var/cache/dnf

USER "$USER_ID"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.local/bin:$PATH" \
    POETRY_VERSION="2.*" \
    POETRY_NO_INTERACTION=1 \
    VIRTUAL_ENV=/app/venv


# Install poetry, create virtual environment
RUN ${PYTHON_BIN} -m pip install --user "poetry==${POETRY_VERSION}" \
    && ${PYTHON_BIN} -m venv "$VIRTUAL_ENV" \
    && poetry config virtualenvs.create false

ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry install -E all --no-root --no-cache \
    && ${PYTHON_BIN} -m pip install gunicorn

# Copy required files to build the python library
COPY README.md /app/
ADD src /app/src

RUN poetry install -E all --only-root

EXPOSE 5000

USER 0

RUN chown -R "${USER_ID}:0" /app/src/pattern_service

USER "$USER_ID"

FROM base AS dispatcher-image

ARG DISPATCHER_CONFIG=${DISPATCHER_CONFIG:-dispatcher_dev.yml}

COPY "${DISPATCHER_CONFIG}" /app/dispatcher.yml

RUN sed  's/\(node_id: \)pattern-service-a/\1pattern-service-worker/' /app/dispatcher.yml > /app/dispatcher-worker.yml

RUN sed  's/\(node_id: \)pattern-service-a/\1pattern-service-api/' /app/dispatcher.yml > /app/dispatcher-api.yml

FROM base AS aap-dev-image

RUN ["aap-pattern-service-manage", "migrate"]

CMD ["aap-pattern-service-manage", "runserver", "0.0.0.0:5000"]