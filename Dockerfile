FROM debian:bookworm-slim as base

ARG USER=backend_user
ARG WORKDIR=/backend

# update and install everything needed
RUN apt-get update \
    && apt-get install -y python3 python3-venv curl git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash ${USER} \
    && mkdir -p ${WORKDIR} \
    && chown ${USER}:${USER} ${WORKDIR} \
    # install pdm for ${USER}
    && su -c "curl -sSL https://pdm.fming.dev/dev/install-pdm.py | python3 - " ${USER}

WORKDIR ${WORKDIR}
USER ${USER}

# extend path for pdm (it must be $PATH to use the container env var)
ENV PATH=/home/${USER}/.local/bin:$PATH

# speed up rebuilds by installing dependencies before copying the project
COPY --chown=${USER}:${USER} .pdm-python .pdm-python
COPY --chown=${USER}:${USER} pyproject.toml pyproject.toml
COPY --chown=${USER}:${USER} pdm.lock pdm.lock


FROM base as development
RUN pdm install --dev --no-self


FROM base as production
RUN pdm install --prod --no-self
# copy the project
COPY --chown=${USER}:${USER} src src

