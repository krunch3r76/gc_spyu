# Dockerfile for spyu
# post
# /root/provider.sh
# /golem/work/
# /golem/output/
# /usr/bin/lstopo
# xml and cairo libraries
# REM lscpu is available from util-linux-misc

FROM alpine:latest
VOLUME /golem/work /golem/output
COPY provider.sh /root
WORKDIR /root
RUN apk add --no-cache --virtual myvapk build-base git bash autoconf automake libtool && \
	apk add --no-cache cairo libxml2 jq && \
	cd /root && \
	git clone https://github.com/open-mpi/hwloc && \
	cd hwloc && \
	./autogen.sh && \
	CFLAGS=-Os ./configure --prefix=/usr && \
	make -j $(( $(nproc)-1 )) && \
	make install && \
	apk del myvapk && \
	rm -rf /root/hwloc && \
	chmod +x /root/provider.sh && \
	rm -rf /var/cache/*
WORKDIR /golem/work

