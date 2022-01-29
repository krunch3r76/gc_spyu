#!/bin/sh

PROVIDERNAME=$1
PROVIDERID=$2
/bin/cat /proc/cpuinfo |grep 'model name' | head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p' >/golem/output/model
/usr/bin/lstopo --output-format svg \
                --append-legend $PROVIDERNAME@$PROVIDERID \
		--append-legend "$(cat /golem/output/model)" \
                /golem/output/topology.svg

