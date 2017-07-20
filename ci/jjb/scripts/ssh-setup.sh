#!/usr/bin/env bash
set -euo pipefail

ssh-keygen -t rsa -N "" -f pulp_server_key
cat pulp_server_key.pub >> ~/.ssh/authorized_keys
