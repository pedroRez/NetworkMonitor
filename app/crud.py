from sqlalchemy.orm import Session

from app import models


def get_devices(db: Session) -> list[models.Device]:
    return db.query(models.Device).order_by(models.Device.id).all()


def create_device(db: Session, device: models.Device) -> models.Device:
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def get_device(db: Session, device_id: int) -> models.Device | None:
    return db.query(models.Device).filter(models.Device.id == device_id).first()


def update_device_name(db: Session, device: models.Device, name: str | None) -> models.Device:
    device.name = name
    db.commit()
    db.refresh(device)
    return device


def create_traffic_sample(db: Session, sample: models.TrafficSample) -> models.TrafficSample:
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


def get_traffic_samples(db: Session, device_id: int | None = None) -> list[models.TrafficSample]:
    query = db.query(models.TrafficSample).order_by(models.TrafficSample.timestamp.desc())
    if device_id:
        query = query.filter(models.TrafficSample.device_id == device_id)
    return query.all()


def get_router_config(db: Session) -> models.RouterConfig | None:
    return db.query(models.RouterConfig).first()


def upsert_router_config(db: Session, config: models.RouterConfig) -> models.RouterConfig:
    existing = get_router_config(db)
    if existing:
        existing.router_ip = config.router_ip
        existing.access_mode = config.access_mode
        existing.snmp_enabled = config.snmp_enabled
        existing.snmp_community = config.snmp_community
        existing.snmp_port = config.snmp_port
        existing.username = config.username
        existing.password = config.password
        db.commit()
        db.refresh(existing)
        return existing
    db.add(config)
    db.commit()
    db.refresh(config)
    return config
