#!/bin/sh

PROVIDERNAME=${1:-"\{PROVIDERNAME\}"}
PROVIDERID=${2:-"\{PROVIDERID\}"}
UNIXTIME=$3
WORKDIR=/golem/work
OUTPUTDIR=/golem/output

# POST
# /golem/work
#	/model			: model name
# 	/topology_host.xml	: modified topology.xml with hostname as $PROVIDERNAME@PROVIDERID
#	/topology.xml		: original topology
#	/topology.svg		: svg from modified topology.xml
#	/topology.asc		: asc from ...
# /golem/output

# /golem/work/model
/bin/cat /proc/cpuinfo |grep 'model name' | head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p' >$WORKDIR/model

# /golem/output/topology.xml
/usr/bin/lstopo --output-format xml \
		$WORKDIR/topology.xml

# /golem/work/topology.xml
SEDX='s/(<info name="HostName" value=")([^\"]*+)("\/>)/\1'
SEDX="${SEDX}${PROVIDERNAME}@${PROVIDERID}\3/"
/bin/sh -c "sed -E '$SEDX' $WORKDIR/topology.xml >$WORKDIR/topology_host.xml"
# STATE: HostName field replaced with provider@address in work xml file

# /golem/output/topology.svg
lstopo -i $WORKDIR/topology_host.xml --of svg \
	--append-legend "$(cat $WORKDIR/model)" \
 	$WORKDIR/topology.svg

lstopo -i $WORKDIR/topology_host.xml --of ascii \
	--append-legend "$(cat $WORKDIR/model)" $WORKDIR/topology.asc

jq -R -s <$WORKDIR/topology.svg >$WORKDIR/topology_svg.jstr
jq --null-input \
	--arg unixtime "$UNIXTIME" \
	--arg name "$PROVIDERNAME" \
	--arg addr "$PROVIDERID" \
	--arg model "$(cat $WORKDIR/model)" \
	--slurpfile svg $WORKDIR/topology_svg.jstr \
	--arg asc "$(cat $WORKDIR/topology.asc)" \
	--arg xml "$(cat $WORKDIR/topology.xml)" \
	'{"unixtime": $unixtime, "name": $name, "addr", $addr, "model": $model, "svg": $svg[0], "asc": $asc, "xml": $xml}' \
	>$OUTPUTDIR/topology.json

