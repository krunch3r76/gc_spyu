#!/bin/sh
# authored by krunch3r (https://www.github.com/krunch3r76)
# license GPL 3.0
PROVIDERNAME=${1:-"\{PROVIDERNAME\}"}
PROVIDERID=${2:-"\{PROVIDERID\}"}
UNIXTIME=$3
FLAG_FOR_TOPOLOGY=${4:-0} # must be 1 to enable
WORKDIR=/golem/work
OUTPUTDIR=/golem/output

# POST
# /golem/work
#	/model			: model name
# /golem/output

## grep the model information ##
################################
# /golem/work/model
/bin/cat /proc/cpuinfo |grep 'model name' | head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p' >$WORKDIR/model


## pack outputs into a json ##
##############################
jq --null-input \
	--arg unixtime "$UNIXTIME" \
	--arg name "$PROVIDERNAME" \
	--arg addr "$PROVIDERID" \
	--arg model "$(cat $WORKDIR/model)" \
	'{"unixtime": $unixtime, "name": $name, "addr", $addr, "model": $model}' \
	>$OUTPUTDIR/intelGathered.json
## end pack outputs into a json
