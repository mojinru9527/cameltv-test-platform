# CamelTv Jenkins Controller — 预装 Python 3.12 + Node 18 + Docker CLI
FROM jenkins/jenkins:lts

USER root

# ── System deps (retry on network failure) ──
RUN apt-get update -o Acquire::Retries=3 \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        curl wget unzip git openssh-client \
    && rm -rf /var/lib/apt/lists/*

# ── Docker CLI (for Pipeline docker build/push) ──
RUN curl -fsSL https://get.docker.com -o /tmp/get-docker.sh \
    && sh /tmp/get-docker.sh \
    && rm /tmp/get-docker.sh \
    || echo "Docker CLI install skipped (will use host socket)"

# ── Node 18 ──
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps (global) ──
RUN pip3 install --break-system-packages pytest pytest-html httpx 2>/dev/null \
    || pip3 install pytest pytest-html httpx

# ── Link python → python3 ──
RUN ln -sf /usr/bin/python3 /usr/bin/python

# ── Jenkins plugins (pre-downloaded for faster first boot) ──
RUN jenkins-plugin-cli --plugins \
    "workflow-aggregator git pipeline-stage-view blueocean docker-workflow configuration-as-code job-dsl junit htmlpublisher ansicolor timestamper build-timeout credentials-binding"

USER jenkins

# ── Environment ──
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
