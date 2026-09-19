FROM ghcr.io/astral-sh/uv:alpine

RUN apk update && apk add --no-cache git openssh-client

# Install run_agent
RUN git clone https://github.com/mbr4477/dev-tools.git /dev-tools && cd /dev-tools && uv tool install .

# Install Claude Code
RUN apk add --no-cache bash curl libgcc libstdc++ ripgrep
ENV USE_BUILTIN_RIPGREP=0
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH=$PATH:/root/.local/bin

WORKDIR /code

ENTRYPOINT ["/bin/sh"]