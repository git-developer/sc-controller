#!/bin/bash

# Ensure correct cwd
cd "$(dirname "$0")"

# Set PATH
SCRIPTS="$(pwd)/scripts"
export PATH="$SCRIPTS":"$PATH"
export PYTHONPATH=".":"$PYTHONPATH"
export SCC_SHARED="$(pwd)"

if [ "$1" == "lldb" ] ; then
	shift
	lldb python3 -- 'scripts/scc-daemon' debug $@
else
	python3 'scripts/scc-daemon' $@
fi
