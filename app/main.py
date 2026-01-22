from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.db import engine, get_db

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


@app.get("/router-config", response_model=schemas.RouterConfig | None)
def get_router_config(db: Session = Depends(get_db)):
    return crud.get_router_config(db)


@app.put("/router-config", response_model=schemas.RouterConfig)
def upsert_router_config(payload: schemas.RouterConfigCreate, db: Session = Depends(get_db)):
    config = models.RouterConfig(
        router_ip=payload.router_ip,
        username=payload.username,
        password=payload.password,
    )
    return crud.upsert_router_config(db, config)


@app.get("/setup", response_class=HTMLResponse)
def setup_page():
    return """
    <!doctype html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Configuração do roteador</title>
      </head>
      <body>
        <h1>Configurar acesso ao roteador</h1>
        <form method="post" action="/router-config" onsubmit="return submitForm(event)">
          <label>IP do roteador<br /><input name="router_ip" required /></label><br /><br />
          <label>Usuário<br /><input name="username" required /></label><br /><br />
          <label>Senha<br /><input type="password" name="password" required /></label><br /><br />
          <button type="submit">Salvar</button>
        </form>
        <p id="status"></p>
        <script>
          async function submitForm(event) {
            event.preventDefault();
            const form = event.target;
            const payload = {
              router_ip: form.router_ip.value,
              username: form.username.value,
              password: form.password.value
            };
            const response = await fetch('/router-config', {
              method: 'PUT',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify(payload)
            });
            const status = document.getElementById('status');
            if (response.ok) {
              status.textContent = 'Configuração salva com sucesso.';
            } else {
              status.textContent = 'Erro ao salvar configuração.';
            }
            return false;
          }
        </script>
      </body>
    </html>
    """
