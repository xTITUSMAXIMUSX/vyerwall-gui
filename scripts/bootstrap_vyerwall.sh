#!/bin/vbash
source /opt/vyatta/etc/functions/script-template

#set -o pipefail

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
echo " DHCP Router:         ${DHCP_ROUTER}"
echo " DHCP DNS Server:     ${DHCP_DNS}"
echo " DHCP Range Start:    ${DHCP_START}"
echo " DHCP Range Stop:     ${DHCP_STOP}"
echo " DHCP Domain:         ${DHCP_DOMAIN}"
echo "=========================================="
read -rp "Proceed with configuration? (y/n): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "❌ Setup cancelled. No changes made."
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
API_KEY_FILE="/config/vyerwallgui_api.key"
echo "vyerwallgui:${API_KEY}" > "${API_KEY_FILE}"
chmod 600 "${API_KEY_FILE}"

ENV_FILE="/config/.env"
if [[ -f "${ENV_FILE}" ]]; then
    if grep -q '^VYDEVICE_APIKEY=' "${ENV_FILE}"; then
        sed -i "s/^VYDEVICE_APIKEY=.*/VYDEVICE_APIKEY=\"${API_KEY}\"/" "${ENV_FILE}"
    else
        echo "VYDEVICE_APIKEY=\"${API_KEY}\"" >> "${ENV_FILE}"
    fi
else
    echo "VYDEVICE_APIKEY=\"${API_KEY}\"" > "${ENV_FILE}"
fi
chmod 600 "${ENV_FILE}"

# Commit
commit
save
exit

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
echo "------------------------------------"
echo " API Key ID: vyerwallgui"
echo " API Key: ${API_KEY}"
echo " Saved to: ${API_KEY_FILE}"
echo " ENV File: ${ENV_FILE}"
echo "------------------------------------"
echo "You can now connect your VyOS frontend using the API key above."

exit 0
