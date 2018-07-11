#!/usr/bin/env bash
set -euo pipefail

hostname="$(hostname --all-fqdn | grep openstacklocal | head -n 1)"
# Make sure there is no whitespace around the hostname
hostname="$(echo ${hostname})"
if [ -n "${hostname:-}" ]; then
    # Set hostname the systemd way if possible, else fall back to manual way.
    if [ "$(which hostnamectl 2>/dev/null)" ]; then
        sudo hostnamectl set-hostname "${hostname}"
    else
        sudo hostname "${hostname}"
        sudo tee /etc/hostname <<< "${hostname}"
    fi
fi
