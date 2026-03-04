# syntax=docker/dockerfile:1
# syntax directive is used to enable Docker BuildKit

ARG PYTHON_VERSION=3.14.2

FROM python:${PYTHON_VERSION}-slim AS base

ARG PROJECT_DIR="/src"
ARG APP_USER="app"
ARG APP_GROUP="app"
ARG NEW_UID
ARG NEW_GID

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    POETRY_VIRTUALENVS_CREATE=false

ENV APP_NAME=gfmodules_national_referral_index
ENV APP_VERSION=0.1.0

# Create a non-privileged user that the app will run under.
RUN groupadd --system ${APP_GROUP} --gid=${NEW_GID} && \
    adduser \
        --disabled-password \
        --gecos "" \
        --uid ${NEW_UID} \
        --gid ${NEW_GID} \
        ${APP_USER}

RUN apt update && \
    apt install -y \
        git \
        gnupg2 \
        make \
        postgresql-client \
        postgresql-client-common \
        curl \
        pkg-config \
        openssl \
        libssl-dev \
        libsodium-dev \
        build-essential

# We need to compile liboprf from source as the current distributed versions are outdated.
RUN git clone https://github.com/stef/liboprf.git && cd liboprf/src && make

RUN pip3 install --upgrade pip && \
    pip3 install poetry --no-cache-dir

RUN chown -R ${APP_USER}:${APP_GROUP} /usr/local/lib/python3.14/site-packages/packaging*

WORKDIR ${PROJECT_DIR}

COPY ./pyproject.toml ./poetry.lock README.md ./



#
# This stage is the builder stage which builds a clean package without dev and debug packages
#
FROM base AS lean-builder

COPY ./app /src/app

RUN --mount=type=cache,target=${POETRY_CACHE_DIR} poetry install --only main --no-interaction

RUN --mount=type=cache,target=${POETRY_CACHE_DIR} poetry build

RUN tar xzvf /src/dist/${APP_NAME}-${APP_VERSION}.tar.gz -C /src/dist



#
# This stage is the debug builder which builds poetry with dev dependencies
#
FROM base AS debug-builder

RUN --mount=type=cache,target=${POETRY_CACHE_DIR} poetry install --no-root --no-interaction



#
# This stage builds the final debug stage with debug package
#
FROM base AS debug-final

# We need to copy the compiled shared libraries from the builder stage to the correct location so they can be found.
RUN mkdir -p /usr/lib/x86_64-linux-gnu/
COPY --from=debug-builder liboprf/src/noise_xk/lib*.so /usr/local/lib/
COPY --from=debug-builder liboprf/src/lib*.so /usr/local/lib/
RUN ldconfig

COPY --from=debug-builder /usr/local /usr/local
RUN chown -R ${APP_USER}:${APP_GROUP} /usr/local/lib/python3.14

COPY ./docker/init.sh /docker-entrypoint.sh

USER ${APP_USER}

EXPOSE 8502
WORKDIR ${PROJECT_DIR}

ENV PYTHONPATH=${PROJECT_DIR}

CMD ["/docker-entrypoint.sh"]



#
# This stage builds the final stage without debug and build dependencies
#
FROM base AS final

# We need to copy the compiled shared libraries from the builder stage to the correct location so they can be found.
RUN mkdir -p /usr/lib/x86_64-linux-gnu/
COPY --from=lean-builder liboprf/src/noise_xk/lib*.so /usr/local/lib/
COPY --from=lean-builder liboprf/src/lib*.so /usr/local/lib/
RUN ldconfig

COPY --from=lean-builder /usr/local /usr/local
RUN chown -R ${APP_USER}:${APP_GROUP} /usr/local/lib/python3.14

COPY --from=lean-builder /src/dist/${APP_NAME}-${APP_VERSION} /src

COPY ./docker/init-standalone.sh /docker-entrypoint.sh

USER ${APP_USER}

EXPOSE 8502
WORKDIR ${PROJECT_DIR}

ENV PYTHONPATH=${PROJECT_DIR}

CMD ["/docker-entrypoint.sh"]
