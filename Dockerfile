FROM ubuntu:24.04
ENV DEBIAN_FRONTEND noninteractive
ENV NS3_DIR=/opt/ns-3
ENV WORKSPACE=/workspace
ARG NS3_VERSION=ns-3.47

# Instalação de dependências do sistema, Python e SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates build-essential g++ cmake ninja-build pkg-config \
    python3 python3-dev python3-flask sqlite3 libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

# Clone e compilação do NS-3.47
RUN git clone --depth 1 --branch ${NS3_VERSION} https://gitlab.com/nsnam/ns-3-dev.git ${NS3_DIR}
WORKDIR ${NS3_DIR}
RUN ./ns3 configure --disable-examples --disable-tests && ./ns3 build

WORKDIR ${WORKSPACE}
EXPOSE 5000
CMD ["/bin/bash", "/workspace/scripts/start.sh"]