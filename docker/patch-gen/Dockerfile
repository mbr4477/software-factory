FROM ghcr.io/astral-sh/uv:alpine

RUN apk update && apk add --no-cache git openssh-client
RUN git clone https://github.com/mbr4477/dev-tools.git /dev-tools && cd /dev-tools && uv tool install .

WORKDIR /code

ENTRYPOINT ["/bin/sh"]