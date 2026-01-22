from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class RouterConfigBase(BaseModel):
    router_ip: str
    username: str
    password: str


class RouterConfigCreate(RouterConfigBase):
    pass


class RouterConfig(RouterConfigBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
