FROM alpine:latest
RUN set -ex && \
    apk add --no-cache util-linux-misc jq

