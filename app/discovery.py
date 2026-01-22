from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import re
import subprocess
import sys
from typing import Iterable


class DiscoveryError(RuntimeError):
    pass


def _normalize_mac(value: str) -> str | None:
    mac = value.strip().lower().replace("-", ":")
    if re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", mac) is None:
        return None
    if mac in {"00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"}:
        return None
    return mac


def _resolve_network(router_ip: str | None, subnet_cidr: str | None) -> ipaddress.IPv4Network:
    if subnet_cidr:
        network = ipaddress.ip_network(subnet_cidr, strict=False)
    elif router_ip:
        network = ipaddress.ip_network(f"{router_ip}/24", strict=False)
    else:
        raise DiscoveryError("router_ip or subnet_cidr is required")
    if not isinstance(network, ipaddress.IPv4Network):
        raise DiscoveryError("Only IPv4 networks are supported")
    if network.num_addresses > 1024:
        raise DiscoveryError("Subnet too large. Use a /24 or smaller.")
    return network


def _ping_host(host: str, timeout_ms: int) -> None:
    if sys.platform.startswith("win"):
        command = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        timeout_s = max(1, int(round(timeout_ms / 1000)))
        command = ["ping", "-c", "1", "-W", str(timeout_s), host]
    try:
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(1, int(round(timeout_ms / 1000)) + 1),
            check=False,
        )
    except Exception:
        return


def _ping_sweep(network: ipaddress.IPv4Network, timeout_ms: int = 400, workers: int = 64) -> None:
    hosts = [str(ip) for ip in network.hosts()]
    if not hosts:
        return
    with ThreadPoolExecutor(max_workers=min(workers, len(hosts))) as executor:
        futures = [executor.submit(_ping_host, host, timeout_ms) for host in hosts]
        for future in as_completed(futures):
            future.result()


def _read_arp_table() -> list[tuple[str, str]]:
    try:
        result = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except Exception as exc:
        raise DiscoveryError(f"Failed to read ARP table: {exc}") from exc
    output = (result.stdout or "") + (result.stderr or "")
    ip_regex = re.compile(r"(?:\\d{1,3}\\.){3}\\d{1,3}")
    mac_regex = re.compile(r"[0-9a-fA-F]{2}(?:[:-][0-9a-fA-F]{2}){5}")
    entries: list[tuple[str, str]] = []
    for line in output.splitlines():
        ip_match = ip_regex.search(line)
        mac_match = mac_regex.search(line)
        if not ip_match or not mac_match:
            continue
        mac = _normalize_mac(mac_match.group(0))
        if not mac:
            continue
        entries.append((ip_match.group(0), mac))
    return entries


def discover_devices(
    router_ip: str | None,
    subnet_cidr: str | None = None,
    mode: str = "ping_sweep",
) -> list[tuple[str, str]]:
    network = _resolve_network(router_ip, subnet_cidr)
    if mode not in {"arp_only", "ping_sweep"}:
        raise DiscoveryError("Invalid discovery mode. Use arp_only or ping_sweep.")
    if mode == "ping_sweep":
        _ping_sweep(network)
    entries = _read_arp_table()
    discovered: dict[str, str] = {}
    for ip_str, mac in entries:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip not in network:
            continue
        discovered[ip_str] = mac
    return [(ip, mac) for ip, mac in discovered.items()]
