# ============================================
# Stage 1: NS-3 Builder (cacheado separadamente)
# Só reconstrói se NS3_VERSION ou os comandos de build mudarem
# ============================================
FROM ubuntu:22.04 AS ns3-builder
ENV DEBIAN_FRONTEND noninteractive
ENV NS3_DIR=/opt/ns-3
ARG NS3_VERSION=ns-3.47

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates build-essential g++ cmake ninja-build pkg-config \
    python3 python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch ${NS3_VERSION} https://gitlab.com/nsnam/ns-3-dev.git ${NS3_DIR}
WORKDIR ${NS3_DIR}
RUN ./ns3 configure --disable-examples --disable-tests && ./ns3 build

# ============================================
# Stage 2: Imagem principal (SDN/NFV + webapp)
# Usa o NS-3 já compilado do stage anterior
# ============================================
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND noninteractive
ENV NS3_DIR=/opt/ns-3
ENV WORKSPACE=/workspace

# Dependências de runtime (inclui build tools para ./ns3 run recompilar scratch/)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates build-essential g++ cmake ninja-build pkg-config \
    python3 python3-dev python3-pip python3-flask sqlite3 libsqlite3-dev \
    mininet openvswitch-switch openvswitch-common \
    iptables iproute2 iputils-ping net-tools curl tcpdump && \
    rm -rf /var/lib/apt/lists/*

# Copia o NS-3 já compilado do stage 1
COPY --from=ns3-builder /opt/ns-3 /opt/ns-3

# Instala Ryu com eventlet compatível com Python 3.10
# eventlet==0.33.0 corrige o bug is_timeout (imutable TimeoutError no Py3.10)
# O sed corrige o ryu 4.34 para não depender de ALREADY_HANDLED (removido no eventlet>=0.31)
RUN pip3 install "setuptools<67" "eventlet==0.33.3" && \
    pip3 install ryu && \
    sed -i 's/from eventlet.wsgi import ALREADY_HANDLED/ALREADY_HANDLED = b""/' \
        /usr/local/lib/python3.10/dist-packages/ryu/app/wsgi.py

WORKDIR ${WORKSPACE}
EXPOSE 5000
CMD ["/bin/bash", "/workspace/scripts/start.sh"]