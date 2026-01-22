from __future__ import annotations

from datetime import datetime, timezone
import re
import subprocess
import sys
from typing import Any

try:
    from pysnmp.hlapi import (
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        getCmd,
        nextCmd,
    )
except Exception as exc:  # pragma: no cover - import guard
    SnmpEngine = None  # type: ignore[assignment]
    _pysnmp_import_error = exc
else:
    _pysnmp_import_error = None


SYS_UPTIME_OID = "1.3.6.1.2.1.1.3.0"
SYS_NAME_OID = "1.3.6.1.2.1.1.5.0"
SYS_DESCR_OID = "1.3.6.1.2.1.1.1.0"
IF_NAME_OID = "1.3.6.1.2.1.31.1.1.1.1"
IF_DESCR_OID = "1.3.6.1.2.1.2.2.1.2"
IF_HC_IN_OID = "1.3.6.1.2.1.31.1.1.1.6"
IF_HC_OUT_OID = "1.3.6.1.2.1.31.1.1.1.10"
IF_IN_OID = "1.3.6.1.2.1.2.2.1.10"
IF_OUT_OID = "1.3.6.1.2.1.2.2.1.16"
IF_OPER_OID = "1.3.6.1.2.1.2.2.1.8"

OPER_STATUS = {
    1: "up",
    2: "down",
    3: "testing",
    4: "unknown",
    5: "dormant",
    6: "not_present",
    7: "lower_layer_down",
}


class SnmpError(RuntimeError):
    pass


def _snmp_session(router_ip: str, community: str, port: int, timeout: int, retries: int):
    if SnmpEngine is None:
        raise SnmpError(f"pysnmp is not available: {_pysnmp_import_error}")
    engine = SnmpEngine()
    auth = CommunityData(community, mpModel=1)
    target = UdpTransportTarget((router_ip, port), timeout=timeout, retries=retries)
    context = ContextData()
    return engine, auth, target, context


def _snmp_get(engine, auth, target, context, oid: str):
    iterator = getCmd(engine, auth, target, context, ObjectType(ObjectIdentity(oid)))
    error_indication, error_status, error_index, var_binds = next(iterator)
    if error_indication:
        raise SnmpError(str(error_indication))
    if error_status:
        location = ""
        if error_index and var_binds:
            location = f" at {var_binds[int(error_index) - 1][0]}"
        raise SnmpError(f"{error_status.prettyPrint()}{location}")
    if not var_binds:
        raise SnmpError("Empty SNMP response")
    return var_binds[0][1]


def _snmp_get_optional(engine, auth, target, context, oid: str):
    try:
        return _snmp_get(engine, auth, target, context, oid)
    except SnmpError:
        return None


def _snmp_walk(engine, auth, target, context, base_oid: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for error_indication, error_status, error_index, var_binds in nextCmd(
        engine,
        auth,
        target,
        context,
        ObjectType(ObjectIdentity(base_oid)),
        lexicographicMode=False,
    ):
        if error_indication:
            raise SnmpError(str(error_indication))
        if error_status:
            location = ""
            if error_index and var_binds:
                location = f" at {var_binds[int(error_index) - 1][0]}"
            raise SnmpError(f"{error_status.prettyPrint()}{location}")
        for name, value in var_binds:
            name_str = name.prettyPrint()
            if not name_str.startswith(f"{base_oid}."):
                continue
            index = name_str[len(base_oid) + 1 :]
            results[index] = value
    return results


def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _format_uptime(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02}:{minutes:02}:{secs:02}"
    return f"{hours:02}:{minutes:02}:{secs:02}"


def _match_interface(interfaces: list[dict[str, Any]], keywords: list[str]):
    for interface in interfaces:
        name = str(interface.get("name", "")).lower()
        for keyword in keywords:
            if keyword in name:
                if keyword == "lan" and "wlan" in name:
                    continue
                return interface
    return None


def collect_snmp_metrics(
    router_ip: str,
    community: str,
    port: int = 161,
    timeout: int = 2,
    retries: int = 1,
) -> dict[str, Any]:
    engine, auth, target, context = _snmp_session(router_ip, community, port, timeout, retries)
    uptime_ticks = _snmp_get(engine, auth, target, context, SYS_UPTIME_OID)
    uptime_seconds = _safe_int(uptime_ticks)
    sys_name = _snmp_get_optional(engine, auth, target, context, SYS_NAME_OID)
    sys_descr = _snmp_get_optional(engine, auth, target, context, SYS_DESCR_OID)

    names = _snmp_walk(engine, auth, target, context, IF_NAME_OID)
    if not names:
        names = _snmp_walk(engine, auth, target, context, IF_DESCR_OID)

    in_octets = _snmp_walk(engine, auth, target, context, IF_HC_IN_OID)
    out_octets = _snmp_walk(engine, auth, target, context, IF_HC_OUT_OID)
    counter_bits = 64
    if not in_octets or not out_octets:
        in_octets = _snmp_walk(engine, auth, target, context, IF_IN_OID)
        out_octets = _snmp_walk(engine, auth, target, context, IF_OUT_OID)
        counter_bits = 32

    oper_status = _snmp_walk(engine, auth, target, context, IF_OPER_OID)
    indices = set(names) | set(in_octets) | set(out_octets) | set(oper_status)

    interfaces: list[dict[str, Any]] = []
    total_in = 0
    total_out = 0

    def index_key(value: str):
        try:
            return int(value)
        except ValueError:
            return value

    for index in sorted(indices, key=index_key):
        name = names.get(index)
        name_str = str(name) if name is not None else f"if{index}"
        in_value = _safe_int(in_octets.get(index))
        out_value = _safe_int(out_octets.get(index))
        status_value = _safe_int(oper_status.get(index))
        status = OPER_STATUS.get(status_value or 0, "unknown")
        if in_value is not None:
            total_in += in_value
        if out_value is not None:
            total_out += out_value
        interfaces.append(
            {
                "index": _safe_int(index),
                "name": name_str,
                "oper_status": status,
                "in_octets": in_value,
                "out_octets": out_value,
            }
        )

    interfaces_up = sum(1 for iface in interfaces if iface.get("oper_status") == "up")
    snmp_limited = len(interfaces) == 0
    wan_iface = _match_interface(interfaces, ["wan"])
    lan_iface = _match_interface(interfaces, ["lan"])

    collected_at = datetime.now(timezone.utc).isoformat()

    return {
        "monitoring_mode": "snmp",
        "router_ip": router_ip,
        "status": "online",
        "sys_name": str(sys_name) if sys_name is not None else None,
        "sys_descr": str(sys_descr) if sys_descr is not None else None,
        "uptime_seconds": uptime_seconds,
        "uptime": _format_uptime(uptime_seconds or 0),
        "interface_count": len(interfaces),
        "interfaces_up": interfaces_up,
        "wan_status": wan_iface.get("oper_status") if wan_iface else "unknown",
        "lan_status": lan_iface.get("oper_status") if lan_iface else "unknown",
        "total_in_octets": total_in,
        "total_out_octets": total_out,
        "counter_bits": counter_bits,
        "interfaces": interfaces,
        "snmp_limited": snmp_limited,
        "snmp_message": "SNMP limited to system MIB" if snmp_limited else None,
        "collected_at": collected_at,
    }


def _parse_latency_ms(output: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*ms", output)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def passive_probe(router_ip: str, reason: str) -> dict[str, Any]:
    if sys.platform.startswith("win"):
        command = ["ping", "-n", "1", "-w", "1200", router_ip]
    else:
        command = ["ping", "-c", "1", "-W", "1", router_ip]
    reachable = False
    latency = None
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        reachable = result.returncode == 0
        latency = _parse_latency_ms(output)
    except Exception:
        reachable = False
        latency = None
    collected_at = datetime.now(timezone.utc).isoformat()
    return {
        "monitoring_mode": "passive",
        "router_ip": router_ip,
        "status": "online" if reachable else "offline",
        "reachable": reachable,
        "latency_ms": latency,
        "passive_reason": reason,
        "collected_at": collected_at,
    }
