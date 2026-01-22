import logging
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.db import engine, get_db, test_db_connection
from app.snmp import SnmpError, collect_snmp_metrics, passive_probe

logger = logging.getLogger(__name__)

app = FastAPI(title="Network Monitor API")

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    test_db_connection()
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception:
        logger.exception("Failed to create database tables on startup.")
        raise


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
        access_mode=payload.access_mode,
        snmp_enabled=payload.snmp_enabled,
        snmp_community=payload.snmp_community,
        snmp_port=payload.snmp_port,
        username=payload.username,
        password=payload.password,
    )
    return crud.upsert_router_config(db, config)


@app.get("/router-metrics")
def get_router_metrics(db: Session = Depends(get_db)):
    config = crud.get_router_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="Router config not set")
    if config.snmp_enabled and config.snmp_community:
        try:
            metrics = collect_snmp_metrics(
                router_ip=config.router_ip,
                community=config.snmp_community,
                port=config.snmp_port or 161,
            )
        except SnmpError as exc:
            fallback = passive_probe(config.router_ip, reason="snmp_error")
            fallback["snmp_error"] = str(exc)
            return fallback
        passive = passive_probe(config.router_ip, reason="snmp_enabled")
        metrics["reachable"] = passive.get("reachable")
        metrics["latency_ms"] = passive.get("latency_ms")
        metrics["passive_status"] = passive.get("status")
        return metrics
    return passive_probe(config.router_ip, reason="snmp_disabled")


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
          <label>Modo de acesso<br />
            <select name="access_mode">
              <option value="local_admin">Local admin</option>
              <option value="cloud_only">Cloud-only</option>
              <option value="isp_managed">ISP managed</option>
            </select>
          </label><br /><br />
          <div id="credentials">
            <label>Usuario<br /><input name="username" /></label><br /><br />
            <label>Senha<br /><input type="password" name="password" /></label><br /><br />
          </div>
          <div id="snmp">
            <label><input type="checkbox" name="snmp_enabled" /> SNMP habilitado</label><br /><br />
            <div id="snmp-fields">
              <label>Comunidade<br /><input name="snmp_community" placeholder="public" /></label><br /><br />
              <label>Porta<br /><input name="snmp_port" type="number" min="1" max="65535" value="161" /></label><br /><br />
            </div>
          </div>
          <button type="submit">Salvar</button>
        </form>
        <p id="status"></p>
        <script>
          function updateAccessMode(form) {
            const requiresCredentials = form.access_mode.value === 'local_admin';
            const credentials = document.getElementById("credentials");
            credentials.style.display = requiresCredentials ? 'block' : 'none';
            form.username.required = requiresCredentials;
            form.password.required = requiresCredentials;
          }

          function updateSnmp(form) {
            const snmpFields = document.getElementById("snmp-fields");
            const snmpEnabled = form.snmp_enabled.checked;
            snmpFields.style.display = snmpEnabled ? 'block' : 'none';
            form.snmp_community.required = snmpEnabled;
          }

          async function submitForm(event) {
            event.preventDefault();
            const form = event.target;
            const accessMode = form.access_mode.value;
            const snmpEnabled = form.snmp_enabled.checked;
            const snmpPort = Number(form.snmp_port.value || 161);
            const payload = {
              router_ip: form.router_ip.value,
              access_mode: accessMode,
              snmp_enabled: snmpEnabled,
              snmp_community: snmpEnabled ? form.snmp_community.value : null,
              snmp_port: snmpEnabled ? snmpPort : 161,
              username: accessMode === 'local_admin' ? form.username.value : null,
              password: accessMode === 'local_admin' ? form.password.value : null
            };
            const response = await fetch('/router-config', {
              method: 'PUT',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify(payload)
            });
            const status = document.getElementById("status");
            if (response.ok) {
              status.textContent = 'Configuracao salva com sucesso.';
            } else {
              status.textContent = 'Erro ao salvar configuracao.';
            }
            return false;
          }

          const form = document.querySelector("form");
          if (form) {
            form.access_mode.addEventListener("change", () => updateAccessMode(form));
            form.snmp_enabled.addEventListener("change", () => updateSnmp(form));
            updateAccessMode(form);
            updateSnmp(form);
          }
        </script>
      </body>
    </html>
    """
