#!/usr/bin/env bash

pid_file="${PWD}/rsyslog-client.pid"

rsyslogd -f ./examples/rsyslog-client.conf -i "${pid_file}" &
sleep 1

pid="$(<"${pid_file}")"

trap 'kill -9 ${pid}; rm ${pid_file}; echo "Done killing rsyslogd"' EXIT

echo "Waiting for process ${pid} to exit"
wait "${pid}"
