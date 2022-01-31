#!/bin/sh

PROVIDERNAME=$1
PROVIDERID=$2
WORKDIR=/golem/work
OUTPUTDIR=/golem/output

# POST
# /golem/work
#	/model			: model name
# 	/topology.xml		: modified topology.xml with hostname as $PROVIDERNAME@PROVIDERID
# /golem/output
#	/topology.xml	: original topology with modified legend
#	/topology.svg	: svg from modified topology.xml

# /golem/work/model
/bin/cat /proc/cpuinfo |grep 'model name' | head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p' >$WORKDIR/model

# /golem/output/topology.xml
/usr/bin/lstopo --output-format xml \
		--append-legend "$(cat $WORKDIR/model)" \
		$OUTPUTDIR/topology.xml

# /golem/work/topology.xml
SEDX='s/(<info name="HostName" value=")([^\"]*+)("\/>)/\1'
SEDX="${SEDX}${PROVIDERNAME}@${PROVIDERID}\3/"
/bin/sh -c "sed -E '$SEDX' $OUTPUTDIR/topology.xml >$WORKDIR/topology.xml"

# /golem/output/topology.svg
lstopo -i $WORKDIR/topology.xml --of svg $OUTPUTDIR/topology.svg

