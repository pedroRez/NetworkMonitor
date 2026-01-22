import { useEffect, useMemo, useState } from "react";
import {
  getDevices,
  getHealth,
  getRouterConfig,
  getTraffic,
  saveRouterConfig
} from "./api";

const emptyConfig = {
  router_ip: "",
  username: "",
  password: ""
};

const numberFormat = new Intl.NumberFormat("pt-BR");

const formatBytes = (value) => {
  if (value === null || value === undefined) {
    return "—";
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return "—";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = numeric;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const digits = size >= 10 || unitIndex === 0 ? 0 : 1;
  return `${numberFormat.format(size.toFixed(digits))} ${units[unitIndex]}`;
};

const formatDateTime = (value) => {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleString("pt-BR");
};

const lastUpdatedLabel = (value) => {
  if (!value) {
    return "—";
  }
  return value.toLocaleTimeString("pt-BR");
};

export default function App() {
  const [health, setHealth] = useState({ status: "carregando" });
  const [devices, setDevices] = useState([]);
  const [traffic, setTraffic] = useState([]);
  const [routerConfig, setRouterConfig] = useState(emptyConfig);
  const [routerStatus, setRouterStatus] = useState({
    type: "idle",
    message: ""
  });
  const [filterDevice, setFilterDevice] = useState("all");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const refreshData = async () => {
    setLoading(true);
    const nextErrors = {};

    const results = await Promise.allSettled([
      getHealth(),
      getDevices(),
      getTraffic(),
      getRouterConfig()
    ]);

    const [healthResult, devicesResult, trafficResult, routerResult] = results;

    if (healthResult.status === "fulfilled") {
      setHealth(healthResult.value);
    } else {
      setHealth({ status: "offline" });
      nextErrors.health = "API indisponível.";
    }

    if (devicesResult.status === "fulfilled") {
      setDevices(devicesResult.value);
    } else {
      setDevices([]);
      nextErrors.devices = "Não foi possível carregar os dispositivos.";
    }

    if (trafficResult.status === "fulfilled") {
      setTraffic(trafficResult.value);
    } else {
      setTraffic([]);
      nextErrors.traffic = "Não foi possível carregar o tráfego.";
    }

    if (routerResult.status === "fulfilled") {
      if (routerResult.value) {
        setRouterConfig(routerResult.value);
      } else {
        setRouterConfig(emptyConfig);
      }
    } else {
      setRouterConfig(emptyConfig);
      nextErrors.router = "Não foi possível carregar as credenciais.";
    }

    setErrors(nextErrors);
    setLastUpdated(new Date());
    setLoading(false);
  };

  useEffect(() => {
    refreshData();
  }, []);

  const filteredTraffic = useMemo(() => {
    if (filterDevice === "all") {
      return traffic;
    }
    return traffic.filter((sample) => String(sample.device_id) === filterDevice);
  }, [traffic, filterDevice]);

  const trafficTotals = useMemo(() => {
    return filteredTraffic.reduce(
      (acc, sample) => {
        acc.in += sample.bytes_in ?? 0;
        acc.out += sample.bytes_out ?? 0;
        return acc;
      },
      { in: 0, out: 0 }
    );
  }, [filteredTraffic]);

  const handleRouterChange = (event) => {
    const { name, value } = event.target;
    setRouterConfig((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleRouterSubmit = async (event) => {
    event.preventDefault();
    setRouterStatus({ type: "loading", message: "Salvando credenciais..." });
    const payload = {
      router_ip: routerConfig.router_ip,
      username: routerConfig.username,
      password: routerConfig.password
    };
    try {
      const saved = await saveRouterConfig(payload);
      setRouterConfig(saved ?? routerConfig);
      setRouterStatus({ type: "success", message: "Configuração salva com sucesso." });
    } catch (error) {
      setRouterStatus({
        type: "error",
        message: error?.message ?? "Erro ao salvar configuração."
      });
    }
  };

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-text">
          <span className="eyebrow">Monitoramento local</span>
          <h1>Network Monitor</h1>
          <p>
            Painel de visibilidade para a rede local com cadastro de dispositivos,
            amostras SNMP e controle seguro das credenciais do roteador.
          </p>
          <div className="hero-actions">
            <button className="primary" type="button" onClick={refreshData} disabled={loading}>
              {loading ? "Atualizando..." : "Atualizar agora"}
            </button>
            <div className="status">
              <span className={`dot ${health.status === "ok" ? "ok" : "warn"}`} />
              <span>API {health.status === "ok" ? "online" : "offline"}</span>
            </div>
          </div>
          {errors.health ? <p className="hint error">{errors.health}</p> : null}
        </div>
        <div className="hero-card">
          <div className="metric">
            <span>Dispositivos monitorados</span>
            <strong>{numberFormat.format(devices.length)}</strong>
          </div>
          <div className="metric">
            <span>Amostras carregadas</span>
            <strong>{numberFormat.format(traffic.length)}</strong>
          </div>
          <div className="metric">
            <span>Última atualização</span>
            <strong>{lastUpdatedLabel(lastUpdated)}</strong>
          </div>
          <div className="metric">
            <span>Tráfego total (seleção)</span>
            <strong>
              {formatBytes(trafficTotals.in)} / {formatBytes(trafficTotals.out)}
            </strong>
          </div>
        </div>
      </header>

      <section className="grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Credenciais do roteador</h2>
              <p>Informe o IP e as credenciais para autenticação SNMP ou web.</p>
            </div>
          </div>
          <form className="form" onSubmit={handleRouterSubmit}>
            <div className="form-grid">
              <label>
                IP do roteador
                <input
                  name="router_ip"
                  value={routerConfig.router_ip}
                  onChange={handleRouterChange}
                  placeholder="192.168.0.1"
                  required
                />
              </label>
              <label>
                Usuário
                <input
                  name="username"
                  value={routerConfig.username}
                  onChange={handleRouterChange}
                  placeholder="admin"
                  required
                />
              </label>
              <label>
                Senha
                <input
                  type="password"
                  name="password"
                  value={routerConfig.password}
                  onChange={handleRouterChange}
                  placeholder="••••••••"
                  required
                />
              </label>
            </div>
            <div className="form-actions">
              <button className="primary" type="submit">
                Salvar configurações
              </button>
              <span className={`hint ${routerStatus.type}`}>{routerStatus.message}</span>
            </div>
            {errors.router ? <p className="hint error">{errors.router}</p> : null}
          </form>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Dispositivos cadastrados</h2>
              <p>Inventário com IP, MAC e nome amigável.</p>
            </div>
          </div>
          {devices.length === 0 ? (
            <p className="empty">Nenhum dispositivo cadastrado ainda.</p>
          ) : (
            <div className="table">
              <div className="table-row header">
                <span>IP</span>
                <span>MAC</span>
                <span>Nome</span>
              </div>
              {devices.map((device) => (
                <div className="table-row" key={device.id}>
                  <span>{device.ip_address}</span>
                  <span>{device.mac_address}</span>
                  <span>{device.name || "Sem nome"}</span>
                </div>
              ))}
            </div>
          )}
          {errors.devices ? <p className="hint error">{errors.devices}</p> : null}
        </div>

        <div className="panel wide">
          <div className="panel-header">
            <div>
              <h2>Amostras de tráfego</h2>
              <p>Últimas leituras por dispositivo com bytes de entrada/saída.</p>
            </div>
            <label className="select">
              Filtrar por dispositivo
              <select value={filterDevice} onChange={(event) => setFilterDevice(event.target.value)}>
                <option value="all">Todos</option>
                {devices.map((device) => (
                  <option key={device.id} value={String(device.id)}>
                    {device.name ? `${device.name} (${device.ip_address})` : device.ip_address}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {filteredTraffic.length === 0 ? (
            <p className="empty">Nenhuma amostra registrada no momento.</p>
          ) : (
            <div className="table">
              <div className="table-row header">
                <span>Dispositivo</span>
                <span>Entrada</span>
                <span>Saída</span>
                <span>Data/hora</span>
              </div>
              {filteredTraffic.slice(0, 8).map((sample) => (
                <div className="table-row" key={sample.id}>
                  <span>#{sample.device_id}</span>
                  <span>{formatBytes(sample.bytes_in)}</span>
                  <span>{formatBytes(sample.bytes_out)}</span>
                  <span>{formatDateTime(sample.timestamp)}</span>
                </div>
              ))}
            </div>
          )}
          {errors.traffic ? <p className="hint error">{errors.traffic}</p> : null}
        </div>
      </section>
    </div>
  );
}
