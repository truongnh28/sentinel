# The environment the AGENT works in. Deliberately NOT the environment the
# measurement runs in: the agent needs the repo's own toolchain, while the
# measurement core stays stdlib-only so the benchmark is clone-and-run (ABC T.6).
# Mixing them would make "reproduce our numbers" require reproducing every repo
# under test.
FROM python:3.11-slim
# Pinned by digest-equivalent tag (not `:latest`) for the same reason the rest of
# this image is pinned: the environment is part of the result. This only puts the
# `uv`/`uvx` binaries on PATH for whatever the agent does inside its own repo
# checkout -- it does not add numpy/scipy/etc to THIS image or touch the
# measurement core's stdlib-only guarantee (test_environment.py).
COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /uvx /usr/local/bin/
# The IMAGE TAG is a mutable local name -- `auditgame:latest` is whatever was built
# last, and an older image left behind under that name runs and produces numbers.
# This label is what harness.container_ready() actually checks, so "the image is
# built" and "the image is THIS image" stop being the same question. Bump the
# value when the environment changes in a way a recorded run must not inherit.
LABEL org.auditgame.harness="auditgame-se-1"
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
# No network at run time. An agent that can reach the internet can fetch the
# upstream fix, and `solved` then measures retrieval rather than repair. uv
# respects the same pip env vars for index resolution, so this still holds.
ENV PIP_NO_INDEX=1
ENV UV_NO_INDEX=1
