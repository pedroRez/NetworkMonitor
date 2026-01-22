from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class DeviceBase(BaseModel):
    ip_address: str
    mac_address: str
    name: str | None = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: str | None = None


class Device(DeviceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TrafficSampleBase(BaseModel):
    device_id: int
    bytes_in: int
    bytes_out: int


class TrafficSampleCreate(TrafficSampleBase):
    pass


class TrafficSample(TrafficSampleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime


RouterAccessMode = Literal["local_admin", "cloud_only", "isp_managed"]


class RouterConfigBase(BaseModel):
    router_ip: str
    access_mode: RouterAccessMode = "local_admin"
    username: str | None = None
    password: str | None = None
    snmp_enabled: bool = False
    snmp_community: str | None = None
    snmp_port: int = 161


class RouterConfigCreate(RouterConfigBase):
    @model_validator(mode="before")
    @classmethod
    def validate_access_mode(cls, values):
        if not isinstance(values, dict):
            return values
        access_mode = values.get("access_mode") or "local_admin"
        values["access_mode"] = access_mode
        if access_mode == "local_admin":
            if not values.get("username") or not values.get("password"):
                raise ValueError("username and password are required for local_admin")
        else:
            values["username"] = None
            values["password"] = None
        if values.get("snmp_enabled"):
            if not values.get("snmp_community"):
                raise ValueError("snmp_community is required when snmp_enabled is true")
            snmp_port = values.get("snmp_port", 161)
            try:
                snmp_port = int(snmp_port)
            except (TypeError, ValueError):
                raise ValueError("snmp_port must be between 1 and 65535") from None
            if not (1 <= snmp_port <= 65535):
                raise ValueError("snmp_port must be between 1 and 65535")
            values["snmp_port"] = snmp_port
        else:
            values["snmp_community"] = None
        return values


class RouterConfig(RouterConfigBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DiscoveryRequest(BaseModel):
    mode: Literal["arp_only", "ping_sweep"] = "ping_sweep"
    subnet_cidr: str | None = None
