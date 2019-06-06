#!/usr/bin/env bash
# wait for ssh connection
for i in $(seq 1 20); do printf "%s." "$i";sleep 2; nc -vzw 2 "${PULP_HOSTNAME}" 22 && break; done
echo "$PULP_HOSTNAME"
# This information can aid in debugging failed jobs.
ssh cloud-user@"${PULP_HOSTNAME}" << 'EOF'
hostname --all-fqdn
hostname
# Setting the hostname of the system to enable connectivity
hostname="$(hostname --all-fqdn | grep upshift | head -n 1)"
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
EOF
