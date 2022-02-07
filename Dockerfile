# Dockerfile for spyu

FROM alpine:latest
VOLUME /golem/work /golem/output
COPY provider.sh /root

