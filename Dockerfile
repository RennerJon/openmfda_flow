FROM openroad/orfs:latest

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# We are on Ubuntu 22.04 base
# Install dependencies not in ORFS
# ORFS has yosys, klayout, openroad.
# We need openscad, time, python3-pip, libgl1, libx11-6

RUN apt-get update && apt-get install -y \
    openscad \
    time \
    curl \
    wget \
    python3-pip \
    libgl1-mesa-glx \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Add OpenROAD to PATH
ENV PATH=$PATH:/OpenROAD-flow-scripts/tools/install/OpenROAD/bin

# Set up user (Jovyan) if needed, but ORFS might have its own.
# We'll stick to root or create one to match previous behavior if critical.
# Previous Dockerfile created 'jovyan'.
ARG NB_USER=jovyan
ARG NB_UID=1000
ENV USER ${NB_USER}
ENV NB_UID ${NB_UID}
ENV HOME /home/${NB_USER}

RUN adduser --disabled-password \
    --gecos "Default user" \
    --uid ${NB_UID} \
    ${NB_USER} || echo "User might exist"

WORKDIR ${HOME}

# Copy requirements
COPY requirements.txt /tmp/requirements.txt

# Remove strict constraints if any
RUN sed -i 's/==.*//g' /tmp/requirements.txt

# Install python dependencies
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir -r /tmp/requirements.txt \
    && pip3 install --no-cache-dir opendbpy matplotlib pandas

# Install Miniforge for multi-arch Xyce support
ENV CONDA_DIR=/opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH
RUN wget -O Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" \
    && bash Miniforge3.sh -b -p $CONDA_DIR \
    && rm Miniforge3.sh

RUN mamba install -y -c vlsida-eda xyce \
    && mamba clean --all -y


# Copy flow
COPY --chown=${NB_UID}:${NB_UID} . ${HOME}/openmfda_flow

# Permissions
USER ${NB_USER}
WORKDIR ${HOME}/openmfda_flow

# Environment
ENV OPENMFDA_ROOT=${HOME}/openmfda_flow
ENV PYTHONPATH=${HOME}/openmfda_flow/src
# Force python command to python3 (system python)
ENV PYTHON_CMD=python3

CMD ["/bin/bash"]
