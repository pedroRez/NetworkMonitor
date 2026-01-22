from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, index=True)
    mac_address: Mapped[str] = mapped_column(String(17), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    traffic_samples: Mapped[list["TrafficSample"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )


class TrafficSample(Base):
    __tablename__ = "traffic_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    bytes_in: Mapped[int] = mapped_column(Integer, default=0)
    bytes_out: Mapped[int] = mapped_column(Integer, default=0)

    device: Mapped[Device] = relationship(back_populates="traffic_samples")
