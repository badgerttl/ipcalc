# --------------------------------------------------------------
# app.py – IPv4 Subnet Calculator
# --------------------------------------------------------------
import os
import ipaddress
from flask import Flask, render_template, request

# ------------------------------------------------------------------
# 1. Create the Flask app **globally** – required by `flask run`
# ------------------------------------------------------------------
root_path = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, root_path=root_path)


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
ITEMS_PER_PAGE = 20
PAGES_BEFORE_AFTER = 10

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------
def parse_input(input_str):
    """Parse input that can be CIDR notation, IP with subnet mask, or IP with wildcard mask.
    
    Accepts:
    - CIDR notation: 192.168.1.1/24
    - IP with subnet mask: 192.168.1.1 255.255.255.0
    - IP with wildcard mask: 192.168.1.1 0.0.0.255
    """
    if not input_str:
        return None
    
    input_str = input_str.strip()
    
    try:
        # Check if it's CIDR notation (contains /)
        if "/" in input_str:
            return ipaddress.IPv4Network(input_str, strict=False)
        
        # Try to parse as IP with mask (space-separated)
        parts = input_str.split()
        if len(parts) == 2:
            ip_part = parts[0].strip()
            mask_part = parts[1].strip()
            
            # First, try to parse as subnet mask (default behavior)
            try:
                return ipaddress.IPv4Network(f"{ip_part}/{mask_part}", strict=False)
            except (ValueError, ipaddress.AddressValueError):
                # If that fails, try to parse as wildcard mask
                try:
                    wildcard = ipaddress.IPv4Address(mask_part)
                    # Convert wildcard mask to subnet mask: subnet = 255.255.255.255 - wildcard
                    subnet_int = 0xFFFFFFFF - int(wildcard)
                    subnet_mask = ipaddress.IPv4Address(subnet_int)
                    # Use the subnet mask to create the network
                    return ipaddress.IPv4Network(f"{ip_part}/{subnet_mask}", strict=False)
                except (ValueError, ipaddress.AddressValueError):
                    return None
        
        # If single value, default to /32
        return ipaddress.IPv4Network(f"{input_str}/32", strict=False)
    except (ValueError, ipaddress.AddressValueError):
        return None


def _get_supernet_to_prefix(net, target_prefix):
    """Get the supernet of a network up to a target prefix length."""
    current = net
    while current.prefixlen > target_prefix:
        try:
            current = current.supernet()
        except ValueError:
            break
    return current


def get_parent_network(net):
    """Determine the parent network based on IP class boundaries.
    
    Uses the network's supernet up to the appropriate class boundary:
    - All classes: /24 if prefixlen > 24, /16 if prefixlen > 16, /8 if prefixlen > 8
    
    Examples:
    - 10.10.10.1/30 -> 10.10.10.0/24 (10.10.10.*)
    - 10.10.10.1/19 -> 10.10.0.0/16 (10.10.*.*)
    - 10.10.10.1/15 -> 10.0.0.0/8 (10.*.*.*)
    - 172.16.10.1/30 -> 172.16.10.0/24 (172.16.10.*)
    - 172.16.10.1/19 -> 172.16.0.0/16 (172.16.*.*)
    - 172.16.1.1/15 -> 172.0.0.0/8 (172.*.*.*)
    - 192.168.10.1/30 -> 192.168.10.0/24 (192.168.10.*)
    - 192.168.10.1/19 -> 192.168.0.0/16 (192.168.*.*)
    - 192.168.1.1/15 -> 192.0.0.0/8 (192.*.*.*)
    """
    first = net.network_address.packed[0]
    
    # Determine target boundaries based on prefix length
    if net.prefixlen > 24:
        return _get_supernet_to_prefix(net, 24)
    elif net.prefixlen > 16:
        return _get_supernet_to_prefix(net, 16)
    elif net.prefixlen > 8:
        return _get_supernet_to_prefix(net, 8)
    else:
        # Prefixlen <= 8, use /8 network
        return ipaddress.IPv4Network(f"{first}.0.0.0/8")


def get_host_range(net):
    """Calculate usable host range for a network."""
    if net.num_addresses > 2:
        return (net.network_address + 1, net.broadcast_address - 1)
    return (net.network_address, net.network_address)


def wildcard_network(net):
    """Generate wildcard network representation (e.g., 10.100.*.*)."""
    octets = net.network_address.exploded.split(".")
    mask_octets = net.netmask.exploded.split(".")
    return ".".join(oct if mask == "255" else "*" for oct, mask in zip(octets, mask_octets))


def format_ipcalc(net, requested_page=None):
    """Format network information for display.
    
    Args:
        net: IPv4Network object
        requested_page: Optional page number to center the window on
    """
    if not net:
        return None

    # Host calculations
    hosts_total = net.num_addresses
    hosts_usable = max(0, hosts_total - 2)
    host_min, host_max = get_host_range(net)

    # Masks
    wildcard = ipaddress.IPv4Address(int(net.netmask) ^ 0xFFFFFFFF)
    binary_mask = ".".join(f"{b:08b}" for b in net.netmask.packed)

    # Class and type
    first_octet = net.network_address.packed[0]
    ip_class = (
        "A" if first_octet <= 127 else
        "B" if first_octet <= 191 else
        "C" if first_octet <= 223 else
        "D" if first_octet <= 239 else "E"
    )
    ip_type = "Private" if net.is_private else "Public"

    # IDs
    binary_id = ".".join(f"{b:08b}" for b in net.network_address.packed)
    rev_octets = ".".join(str(o) for o in reversed(net.network_address.packed))
    in_addr = f"{rev_octets}.in-addr.arpa"

    # Subnet list with lazy loading (window of pages around current)
    parent = get_parent_network(net)
    show_subnet_list = parent.prefixlen < net.prefixlen
    
    # Initialize defaults
    all_nets = []
    current_index = 0
    current_page = 1
    start_page = 1
    end_page = 1
    total_subnets = 0
    total_pages = 1

    if show_subnet_list:
        try:
            # Calculate total number of subnets (calculate once, reuse)
            prefix_diff = net.prefixlen - parent.prefixlen
            total_subnets = 2 ** prefix_diff if prefix_diff > 0 else 0
            total_pages = max(1, (total_subnets + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            
            # Calculate current network's index directly
            subnet_size = 2 ** (32 - net.prefixlen)
            current_index = (int(net.network_address) - int(parent.network_address)) // subnet_size
            
            # Calculate page window - use requested page if provided, otherwise use current network's page
            if requested_page:
                try:
                    center_page = max(1, min(int(requested_page), total_pages))
                except (ValueError, TypeError):
                    center_page = (current_index // ITEMS_PER_PAGE) + 1
            else:
                center_page = (current_index // ITEMS_PER_PAGE) + 1
            
            # Center window on the requested/current page
            start_page = max(1, center_page - PAGES_BEFORE_AFTER)
            end_page = min(total_pages, center_page + PAGES_BEFORE_AFTER)
            current_page = center_page
            
            # Calculate index range to generate
            start_index = (start_page - 1) * ITEMS_PER_PAGE
            end_index = min(total_subnets, end_page * ITEMS_PER_PAGE)
            
            # Generate only the window of subnets needed using direct calculation
            for idx in range(start_index, end_index):
                network_int = int(parent.network_address) + (idx * subnet_size)
                subnet_addr = ipaddress.IPv4Address(network_int)
                subnet = ipaddress.IPv4Network(f"{subnet_addr}/{net.prefixlen}", strict=False)
                
                sub_min, sub_max = get_host_range(subnet)
                subnet_page = (idx // ITEMS_PER_PAGE) + 1
                all_nets.append({
                    "network": str(subnet.network_address),
                    "range": f"{sub_min} - {sub_max}",
                    "broadcast": str(subnet.broadcast_address),
                    "is_current": subnet == net,
                    "index": idx,
                    "page": subnet_page,
                })
        except (ValueError, MemoryError):
            show_subnet_list = False
            all_nets = []

    if not show_subnet_list:
        # Show only the current network
        all_nets = [{
            "network": str(net.network_address),
            "range": f"{host_min} - {host_max}",
            "broadcast": str(net.broadcast_address),
            "is_current": True,
            "index": 0,
            "page": 1,
        }]

    # Description - use total count, not window count
    if show_subnet_list:
        count = total_subnets
        parent_desc = (
            f"All {count:,} Possible /{net.prefixlen} Networks in {wildcard_network(parent)}"
            if count > 1 else f"Network: {net}"
        )
    else:
        count = len(all_nets)
        parent_desc = (
            f"All {count:,} Possible /{net.prefixlen} Networks in {wildcard_network(net)}"
            if count > 1 else f"Network: {net}"
        )
    
    # Pagination - values already calculated above for show_subnet_list case
    window_start_page = start_page
    window_end_page = end_page

    # ---- copy‑summary (vertical) -------------------------------------------
    vertical = (
        f"Network Address: {net.network_address}\n"
        f"Binary ID: {binary_id}\n"
        f"Subnet Mask: {net.netmask}\n"
        f"Binary Subnet Mask: {binary_mask}\n"
        f"Wildcard Mask: {wildcard}\n"
        f"Broadcast Address: {net.broadcast_address}\n"
        f"CIDR Notation: {net.network_address}/{net.prefixlen}\n"
        f"Usable Host IP Range: {host_min} - {host_max}\n"
        f"Number of Usable Hosts: {hosts_usable:,}\n"
        f"IP Class: {ip_class}\n"
        f"IP Type: {ip_type}\n"
        f"in-addr.arpa: {in_addr}"
    )

    # Return dict for template
    cidr_full = f"{net.network_address}/{net.prefixlen}"
    return {
        "network": str(net.network_address),
        "host_min": str(host_min),
        "host_max": str(host_max),
        "broadcast": str(net.broadcast_address),
        "hosts_usable": f"{hosts_usable:,}",
        "netmask": str(net.netmask),
        "wildcard": str(wildcard),
        "binary_mask": binary_mask,
        "ip_class": ip_class,
        "cidr_full": cidr_full,
        "ip_type": ip_type,
        "binary_id": binary_id,
        "in_addr": in_addr,
        "all_nets": all_nets,
        "parent_desc": parent_desc,
        "show_subnet_list": show_subnet_list,
        "vertical": vertical,
        "items_per_page": ITEMS_PER_PAGE,
        "total_pages": total_pages,
        "current_page": current_page,
        "total_subnets": total_subnets if show_subnet_list else len(all_nets),
        "window_start_page": window_start_page if show_subnet_list else 1,
        "window_end_page": window_end_page if show_subnet_list else 1,
        "current_index": current_index if show_subnet_list else 0,
    }


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    """Main route handler."""
    if request.method == "POST":
        cidr = request.form.get("cidr", "")
        page = request.form.get("page", "")
        
        net = parse_input(cidr)
        if net:
            result = format_ipcalc(net, page)
            error = None
        else:
            result = None
            error = "Invalid IP address or subnet mask."
    else:
        result = None
        error = None
        cidr = ""

    return render_template("index.html", result=result, error=error, cidr=cidr)


# ------------------------------------------------------------------
# Run only when executed directly (python app.py)
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)