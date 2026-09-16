# The environment the AGENT works in. Deliberately NOT the environment the
# measurement runs in: the agent needs the repo's own toolchain, while the
# measurement core stays stdlib-only so the benchmark is clone-and-run (ABC T.6).
# Mixing them would make "reproduce our numbers" require reproducing every repo
# under test.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
# No network at run time. An agent that can reach the internet can fetch the
# upstream fix, and `solved` then measures retrieval rather than repair.
ENV PIP_NO_INDEX=1
