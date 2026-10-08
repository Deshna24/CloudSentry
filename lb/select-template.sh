#!/bin/sh
# Picks the nginx template: LB_MODE=internal (docker compose, host:port upstreams) or public (HTTPS URLs).
set -e
cp "/opt/lb/${LB_MODE:-internal}.conf.template" /etc/nginx/templates/default.conf.template
