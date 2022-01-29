FROM alpine:latest
VOLUME /golem/output
RUN set -ex && \
    apk add --no-cache util-linux-misc jq && \
    apk add --no-cache hwloc-tools
COPY provider.sh /root
WORKDIR /golem/output

