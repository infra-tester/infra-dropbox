"""Best-effort detection of this machine's LAN IPv4 addresses."""

import socket


def detect_lan_ips() -> list:
    """Return non-loopback IPv4 addresses, default-route interface first.

    The UDP-connect trick asks the kernel which source address it would
    use for outbound traffic; it sends no packets. Falls back to resolving
    the hostname. Returns an empty list when nothing usable is found.
    """
    ips = []

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            primary = probe.getsockname()[0]
        finally:
            probe.close()
        if primary and not primary.startswith("127."):
            ips.append(primary)
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if address and not address.startswith("127.") and address not in ips:
                ips.append(address)
    except OSError:
        pass

    return ips
