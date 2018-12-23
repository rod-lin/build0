#!/bin/bash

if [ -z $1 ]; then
    echo "need one argument"
    exit 1
fi

beautify_date() {
    date -d@$1 -u +%H:%M:%S
}

progress() {
    SECONDS=0
    while true; do
        echo -ne "\rtime elapsed: `beautify_date $SECONDS`"
        sleep 0.5
    done
}

wait() {
    while [ -e /proc/$1 ]; do
        sleep 0.1
    done
}

progress &
PROG_PID=$!

wait $1
EXIT=$?

# echo "" # newline
kill $PROG_PID # kill progress

if [ $EXIT != 0 ]; then
    exit 1
fi
