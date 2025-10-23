#!/bin/vbash
source /opt/vyatta/etc/functions/script-template

#set -o pipefail

CONTAINER_DIR="/config/containers/vyerwall-gui"
ENV_FILE="${CONTAINER_DIR}/.env"
API_KEY_FILE="${CONTAINER_DIR}/api.key"
CONTAINER_IMAGE_DEFAULT="xtitusmaximusx/vyerwall-gui:latest"

mkdir -p "${CONTAINER_DIR}"

ip_to_int() {
    local ip=$1 extra
    local o1 o2 o3 o4
    IFS=. read -r o1 o2 o3 o4 extra <<< "$ip"
    if [[ -n $extra || -z $o4 ]]; then
        return 1
    fi
    for octet in "$o1" "$o2" "$o3" "$o4"; do
        if [[ ! $octet =~ ^[0-9]+$ ]] || (( octet < 0 || octet > 255 )); then
            return 1
        fi
    done
    printf '%u' $(( (o1 << 24) | (o2 << 16) | (o3 << 8) | o4 ))
}

int_to_ip() {
    local value=$(( $1 & 0xFFFFFFFF ))
    printf '%d.%d.%d.%d' $(((value >> 24) & 255)) $(((value >> 16) & 255)) $(((value >> 8) & 255)) $((value & 255))
}

validate_cidr() {
    local cidr=$1
    local ip prefix extra

    IFS=/ read -r ip prefix extra <<< "$cidr"
    if [[ -n $extra || -z $prefix || -z $ip ]]; then
        return 1
    fi
    if [[ ! $prefix =~ ^[0-9]+$ ]] || (( prefix < 0 || prefix > 32 )); then
        return 1
    fi
    if ! ip_to_int "$ip" >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

update_env_var() {
    local key=$1
    local value=$2
    local escaped=${value//\\/\\\\}
    escaped=${escaped//&/\\&}
    escaped=${escaped//|/\\|}

    if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=\"${escaped}\"|" "${ENV_FILE}"
    else
        echo "${key}=\"${value}\"" >> "${ENV_FILE}"
    fi
}

calc_network_details() {
    local cidr=$1
    local ip prefix extra

    IFS=/ read -r ip prefix extra <<< "$cidr"
    if [[ -n $extra || -z $prefix || -z $ip ]]; then
        return 1
    fi
    if [[ ! $prefix =~ ^[0-9]+$ ]] || (( prefix < 0 || prefix > 32 )); then
        return 1
    fi

    local ip_int
    if ! ip_int=$(ip_to_int "$ip"); then
        return 1
    fi
    ip_int=$(( ip_int & 0xFFFFFFFF ))

    local mask
    if (( prefix == 0 )); then
        mask=0
    else
        mask=$(( (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF ))
    fi

    local network_int=$(( ip_int & mask ))
    local broadcast_int=$(( network_int | (0xFFFFFFFF ^ mask) ))
    local host_total=$(( broadcast_int - network_int + 1 ))

    local start_int stop_int
    if (( host_total <= 2 )); then
        start_int=$network_int
        stop_int=$broadcast_int
    else
        local max_offset=$(( host_total - 2 ))
        local offset=20
        if (( offset > max_offset )); then
            offset=$max_offset
        fi
        start_int=$(( network_int + offset ))
        stop_int=$(( broadcast_int - 1 ))
    fi

    LAN_NETWORK="$(int_to_ip "$network_int")/${prefix}"
    LAN_GATEWAY="$(int_to_ip "$ip_int")"
    DHCP_DEFAULT_START="$(int_to_ip "$start_int")"
    DHCP_DEFAULT_STOP="$(int_to_ip "$stop_int")"
    return 0
}

echo "=========================================="
echo "   Vyerwall-GUI Bootstrap Configuration   "
echo "=========================================="

# ------------------------------------------
# GATHER USER INPUT
# ------------------------------------------

# WAN
echo ""
echo "--- WAN Configuration ---"
read -rp "Enter WAN interface name (e.g., eth0): " WAN_IF
WAN_IF=${WAN_IF:-eth0}

read -rp "Use DHCP for WAN? (y/n): " WAN_DHCP
if [[ "$WAN_DHCP" =~ ^[Yy]$ ]]; then
    WAN_TYPE="DHCP"
else
    WAN_TYPE="Static"
    read -rp "Enter static WAN IP (e.g., 203.0.113.2/24): " WAN_IP
fi

# LAN
echo ""
echo "--- LAN Configuration ---"
read -rp "Enter LAN interface name (e.g., eth1): " LAN_IF
LAN_IF=${LAN_IF:-eth1}

DEFAULT_LAN_CIDR="10.50.50.1/24"
while true; do
    read -rp "Enter LAN IP/subnet (e.g., ${DEFAULT_LAN_CIDR}): " LAN_IP
    LAN_IP=${LAN_IP:-$DEFAULT_LAN_CIDR}
    if calc_network_details "$LAN_IP"; then
        break
    fi
    echo "❌ Invalid CIDR. Please try again."
done

# GUI Dummy Interface
echo ""
echo "--- Vyerwall GUI Web Interface ---"
read -rp "Interface name for the GUI web binding [dum0]: " DUMMY_IF
DUMMY_IF=${DUMMY_IF:-dum0}

DEFAULT_DUMMY_CIDR="192.168.0.1/32"
while true; do
    read -rp "IP/CIDR for the GUI interface (e.g., ${DEFAULT_DUMMY_CIDR}): " DUMMY_CIDR
    DUMMY_CIDR=${DUMMY_CIDR:-${DEFAULT_DUMMY_CIDR}}
    if validate_cidr "${DUMMY_CIDR}"; then
        DUMMY_IP="${DUMMY_CIDR%/*}"
        break
    fi
    echo "Invalid CIDR. Please try again."
done

# API Connectivity
echo ""
echo "--- VyOS API Settings (for GUI .env) ---"
read -rp "VyOS API host reachable from container [127.0.0.1]: " API_HOST
API_HOST=${API_HOST:-127.0.0.1}
read -rp "VyOS API port [443]: " API_PORT
API_PORT=${API_PORT:-443}
read -rp "VyOS API protocol [https]: " API_PROTOCOL
API_PROTOCOL=${API_PROTOCOL:-https}
read -rp "Verify SSL certificates? (true/false) [false]: " API_VERIFY
API_VERIFY=${API_VERIFY:-false}

# GUI Credentials
echo ""
echo "--- Vyerwall GUI Credentials ---"
read -rp "Web UI username [admin]: " GUI_USERNAME
GUI_USERNAME=${GUI_USERNAME:-admin}
read -rp "Web UI password [admin]: " GUI_PASSWORD
GUI_PASSWORD=${GUI_PASSWORD:-admin}

# Container Settings
echo ""
echo "--- Container Settings ---"
read -rp "Container name [vyerwall-gui]: " CONTAINER_NAME
CONTAINER_NAME=${CONTAINER_NAME:-vyerwall-gui}
read -rp "Container image [${CONTAINER_IMAGE_DEFAULT}]: " CONTAINER_IMAGE
CONTAINER_IMAGE=${CONTAINER_IMAGE:-${CONTAINER_IMAGE_DEFAULT}}
read -rp "Container restart policy (no/on-failure/always) [always]: " CONTAINER_RESTART_POLICY
CONTAINER_RESTART_POLICY=${CONTAINER_RESTART_POLICY:-always}

# DHCP
echo ""
echo "--- DHCP Server Configuration ---"
read -rp "Default router [${LAN_GATEWAY}]: " DHCP_ROUTER
DHCP_ROUTER=${DHCP_ROUTER:-${LAN_GATEWAY}}

read -rp "DNS name-server [${LAN_GATEWAY}]: " DHCP_DNS
DHCP_DNS=${DHCP_DNS:-${LAN_GATEWAY}}

read -rp "Start range [${DHCP_DEFAULT_START}]: " DHCP_START
DHCP_START=${DHCP_START:-${DHCP_DEFAULT_START}}

read -rp "End range [${DHCP_DEFAULT_STOP}]: " DHCP_STOP
DHCP_STOP=${DHCP_STOP:-${DHCP_DEFAULT_STOP}}

read -rp "Domain name (default vyos.net): " DHCP_DOMAIN
DHCP_DOMAIN=${DHCP_DOMAIN:-vyos.net}

# ------------------------------------------
# CONFIRMATION PROMPT
# ------------------------------------------
echo ""
echo "=========================================="
echo "         CONFIGURATION SUMMARY            "
echo "=========================================="
echo " WAN Interface:       ${WAN_IF}"
echo " WAN Type:            ${WAN_TYPE}"
if [[ "$WAN_TYPE" = "Static" ]]; then
  echo "   WAN IP:            ${WAN_IP}"
fi
echo ""
echo " LAN Interface:       ${LAN_IF}"
echo " LAN IP/Subnet:       ${LAN_IP}"
echo " LAN Network:         ${LAN_NETWORK}"
echo ""
echo " GUI Web Interface:   ${DUMMY_IF}"
echo " GUI Web Address:     ${DUMMY_CIDR}"
echo ""
echo " Container Name:      ${CONTAINER_NAME}"
echo " Container Image:     ${CONTAINER_IMAGE}"
echo " Restart Policy:      ${CONTAINER_RESTART_POLICY}"
echo ""
echo " DHCP Router:         ${DHCP_ROUTER}"
echo " DHCP DNS Server:     ${DHCP_DNS}"
echo " DHCP Range Start:    ${DHCP_START}"
echo " DHCP Range Stop:     ${DHCP_STOP}"
echo " DHCP Domain:         ${DHCP_DOMAIN}"
echo "=========================================="
read -rp "Proceed with configuration? (y/n): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Setup cancelled. No changes made."
    exit 0
fi

# ------------------------------------------
# APPLY CONFIGURATION
# ------------------------------------------
configure

# WAN
set interfaces ethernet "${WAN_IF}" description "WAN"
if [[ "$WAN_TYPE" = "DHCP" ]]; then
    set interfaces ethernet "${WAN_IF}" address dhcp
else
    set interfaces ethernet "${WAN_IF}" address "${WAN_IP}"
fi

# LAN
set interfaces ethernet "${LAN_IF}" description "LAN"
set interfaces ethernet "${LAN_IF}" address "${LAN_IP}"

# Vyerwall GUI Web interface
if [[ "${DUMMY_IF}" =~ ^dum[0-9]*$ ]]; then
    set interfaces dummy "${DUMMY_IF}" description "Vyerwall GUI Management"
    set interfaces dummy "${DUMMY_IF}" address "${DUMMY_CIDR}"
else
    set interfaces ethernet "${DUMMY_IF}" description "Vyerwall GUI Management"
    set interfaces ethernet "${DUMMY_IF}" address "${DUMMY_CIDR}"
fi

# DHCP Server
set service dhcp-server shared-network-name LAN subnet "${LAN_NETWORK}" option default-router "${DHCP_ROUTER}"
set service dhcp-server shared-network-name LAN subnet "${LAN_NETWORK}" option name-server "${DHCP_DNS}"
set service dhcp-server shared-network-name LAN subnet "${LAN_NETWORK}" option domain-name "${DHCP_DOMAIN}"
set service dhcp-server shared-network-name LAN subnet "${LAN_NETWORK}" lease '86400'
set service dhcp-server shared-network-name LAN subnet "${LAN_NETWORK}" range 0 start "${DHCP_START}"
set service dhcp-server shared-network-name LAN subnet "${LAN_NETWORK}" range 0 stop "${DHCP_STOP}"
set service dhcp-server shared-network-name LAN subnet "${LAN_NETWORK}" subnet-id '1'
set service dhcp-server shared-network-name LAN authoritative

# DNS Forwarding
set service dns forwarding cache-size '0'
set service dns forwarding listen-address "${LAN_GATEWAY}"
set service dns forwarding allow-from "${LAN_NETWORK}"
set service dns forwarding system

# NAT
set nat source rule 100 description "vyergui-iface:${LAN_IF}"
set nat source rule 100 outbound-interface name "${WAN_IF}"
set nat source rule 100 source address "${LAN_NETWORK}"
set nat source rule 100 translation address masquerade

# Firewall Globals
set firewall global-options state-policy established action accept
set firewall global-options state-policy related action accept
set firewall global-options state-policy invalid action drop

# Zones
set firewall zone WAN description "WAN"
set firewall zone WAN default-action drop
set firewall zone WAN member interface "${WAN_IF}"

set firewall zone LAN description "LAN"
set firewall zone LAN default-action drop
set firewall zone LAN member interface "${LAN_IF}"

set firewall zone LOCAL local-zone
set firewall zone LOCAL description "Gateway"
set firewall zone LOCAL default-action drop

# Rule Sets
set firewall ipv4 name LAN-WAN default-action drop
set firewall ipv4 name LAN-WAN rule 10 action accept

set firewall ipv4 name LAN-LOCAL default-action drop
set firewall ipv4 name LAN-LOCAL rule 10 action accept

set firewall ipv4 name WAN-LAN default-action drop
set firewall ipv4 name WAN-LOCAL default-action drop

set firewall ipv4 name LOCAL-WAN default-action drop
set firewall ipv4 name LOCAL-WAN rule 10 action accept

set firewall ipv4 name LOCAL-LAN default-action drop
set firewall ipv4 name LOCAL-LAN rule 10 action accept

# Zone Bindings
set firewall zone WAN from LAN firewall name LAN-WAN
set firewall zone LOCAL from LAN firewall name LAN-LOCAL
set firewall zone LAN from WAN firewall name WAN-LAN
set firewall zone LOCAL from WAN firewall name WAN-LOCAL
set firewall zone LAN from LOCAL firewall name LOCAL-LAN
set firewall zone WAN from LOCAL firewall name LOCAL-WAN

# ------------------------------------------
# API KEY GENERATION
# ------------------------------------------
echo ""
echo "--- Generating API Key for Frontend ---"
API_KEY=$(openssl rand -hex 32)
set service https api keys id vyerwallgui key "${API_KEY}"
set service https api rest

# Persist key for GUI consumption
echo "vyerwallgui:${API_KEY}" > "${API_KEY_FILE}"
chmod 600 "${API_KEY_FILE}"

touch "${ENV_FILE}"
chmod 600 "${ENV_FILE}"
update_env_var "VYDEVICE_HOSTNAME" "${API_HOST}"
update_env_var "VYDEVICE_APIKEY" "${API_KEY}"
update_env_var "VYDEVICE_PORT" "${API_PORT}"
update_env_var "VYDEVICE_PROTOCOL" "${API_PROTOCOL}"
update_env_var "VYDEVICE_VERIFY_SSL" "${API_VERIFY}"
update_env_var "USERNAME" "${GUI_USERNAME}"
update_env_var "PASSWORD" "${GUI_PASSWORD}"

# Container Configuration
delete container name "${CONTAINER_NAME}"
set container name "${CONTAINER_NAME}" image "${CONTAINER_IMAGE}"
set container name "${CONTAINER_NAME}" description "Vyerwall GUI"
set container name "${CONTAINER_NAME}" allow-host-networks
set container name "${CONTAINER_NAME}" restart "${CONTAINER_RESTART_POLICY}"
set container name "${CONTAINER_NAME}" volume envfile source "${ENV_FILE}"
set container name "${CONTAINER_NAME}" volume envfile destination /app/.env
set container name "${CONTAINER_NAME}" volume envfile mode ro

# Commit
commit
save
exit

# ------------------------------------------
# CONTAINER DEPLOYMENT
# ------------------------------------------
echo ""
echo "--- Container Image Deployment ---"
read -rp "Pull image and restart container now? (y/n) [y]: " DEPLOY_NOW
DEPLOY_NOW=${DEPLOY_NOW:-y}

if [[ "${DEPLOY_NOW}" =~ ^[Yy]$ ]]; then
    if ! command -v podman >/dev/null 2>&1; then
        echo "Podman CLI not available. Container will start automatically after next reboot/commit."
    else
        if ! run add container image "${CONTAINER_NAME}"; then
            echo "Failed to pull container image for ${CONTAINER_NAME}. Check connectivity or registry access."
        fi
        if ! run restart container "${CONTAINER_NAME}"; then
            echo "Failed to restart container ${CONTAINER_NAME}. Manual intervention may be required."
        else
            echo "Container ${CONTAINER_NAME} pulled and restarted."
        fi
    fi
else
    echo "Skipping immediate image pull; VyOS will manage the container using the configured image ${CONTAINER_IMAGE}."
fi

# ------------------------------------------
# FINAL OUTPUT
# ------------------------------------------
echo ""
echo " Vyerwall-GUI Bootstrap Complete!"
echo "-----------------------------------"
echo " WAN Interface: ${WAN_IF}"
echo " WAN Type: ${WAN_TYPE}"
if [[ "$WAN_TYPE" = "Static" ]]; then
  echo " WAN IP: ${WAN_IP}"
fi
echo " LAN Interface: ${LAN_IF}"
echo " LAN IP: ${LAN_IP}"
echo " LAN Network: ${LAN_NETWORK}"
echo " DHCP Range: ${DHCP_START} - ${DHCP_STOP}"
echo " Default Router: ${DHCP_ROUTER}"
echo " DNS: ${DHCP_DNS}"
echo " GUI Web Interface: ${DUMMY_IF} (${DUMMY_CIDR})"
echo " Container: ${CONTAINER_NAME}"
echo " Image: ${CONTAINER_IMAGE}"
echo " Restart Policy: ${CONTAINER_RESTART_POLICY}"
echo "------------------------------------"
echo " API Key ID: vyerwallgui"
echo " API Key: ${API_KEY}"
echo " Saved to: ${API_KEY_FILE}"
echo " ENV File: ${ENV_FILE}"
echo "------------------------------------"
echo "GUI URL: http://${DUMMY_IP}:5000/"
