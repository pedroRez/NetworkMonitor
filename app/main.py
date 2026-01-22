from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.db import SessionLocal, engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Network Monitor API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/devices", response_model=list[schemas.Device])
def list_devices(db: Session = Depends(get_db)):
    return crud.get_devices(db)


@app.post("/devices", response_model=schemas.Device, status_code=201)
def create_device(payload: schemas.DeviceCreate, db: Session = Depends(get_db)):
    device = models.Device(
        ip_address=payload.ip_address,
        mac_address=payload.mac_address,
        name=payload.name,
    )
    return crud.create_device(db, device)


@app.patch("/devices/{device_id}", response_model=schemas.Device)
def update_device(device_id: int, payload: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return crud.update_device_name(db, device, payload.name)


@app.get("/traffic", response_model=list[schemas.TrafficSample])
def list_traffic(device_id: int | None = None, db: Session = Depends(get_db)):
    return crud.get_traffic_samples(db, device_id=device_id)


@app.post("/traffic", response_model=schemas.TrafficSample, status_code=201)
def create_traffic(payload: schemas.TrafficSampleCreate, db: Session = Depends(get_db)):
    device = crud.get_device(db, payload.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    sample = models.TrafficSample(
        device_id=payload.device_id,
        bytes_in=payload.bytes_in,
        bytes_out=payload.bytes_out,
    )
    return crud.create_traffic_sample(db, sample)
