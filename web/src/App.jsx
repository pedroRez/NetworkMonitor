import { useEffect, useMemo, useState } from "react";
import {
  getDevices,
  getHealth,
  getRouterConfig,
  getRouterMetrics,
  getTraffic,
  saveRouterConfig
} from "./api";

const emptyConfig = {
  router_ip: "",
  access_mode: "local_admin",
  snmp_enabled: false,
  snmp_community: "",
  snmp_port: 161,
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

const statusClass = (value) => {
  if (value === "up" || value === "online") {
    return "ok";
  }
  if (value === "down" || value === "offline") {
    return "error";
  }
  return "warn";
};

const statusLabel = (value) => {
  if (!value) {
    return "—";
  }
  return String(value).replace(/_/g, " ");
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
  const [routerMetrics, setRouterMetrics] = useState(null);
  const [routerMetricsStatus, setRouterMetricsStatus] = useState({
    type: "idle",
    message: ""
  });
  const [filterDevice, setFilterDevice] = useState("all");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const fetchRouterMetrics = async () => {
    setRouterMetricsStatus({ type: "loading", message: "Coletando metricas..." });
    try {
      const data = await getRouterMetrics();
      setRouterMetrics(data);
      if (data?.monitoring_mode === "snmp") {
        if (data?.snmp_limited) {
          setRouterMetricsStatus({
            type: "warn",
            message: "SNMP limitado. Usando ping."
          });
        } else {
          setRouterMetricsStatus({ type: "success", message: "SNMP ativo." });
        }
      } else if (data?.monitoring_mode === "passive") {
        setRouterMetricsStatus({
          type: "warn",
          message: data?.snmp_error
            ? "SNMP falhou. Monitoramento passivo."
            : "Monitoramento passivo."
        });
      } else {
        setRouterMetricsStatus({ type: "idle", message: "" });
      }
    } catch (error) {
      setRouterMetrics(null);
      setRouterMetricsStatus({
        type: "error",
        message: error?.message ?? "Erro ao coletar metricas."
      });
    }
  };

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
        const nextConfig = { ...emptyConfig, ...routerResult.value };
        setRouterConfig(nextConfig);
        await fetchRouterMetrics();
      } else {
        setRouterConfig(emptyConfig);
        setRouterMetrics(null);
        setRouterMetricsStatus({ type: "idle", message: "" });
      }
    } else {
      setRouterConfig(emptyConfig);
      setRouterMetrics(null);
      setRouterMetricsStatus({ type: "error", message: "Router config indisponivel." });
      nextErrors.router = "Nao foi possivel carregar a configuracao.";
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

  const requiresCredentials = routerConfig.access_mode === "local_admin";
  const snmpConfigured = routerConfig.snmp_enabled && routerConfig.snmp_community;
  const routerInterfaces = routerMetrics?.interfaces ?? [];

  const routes = [
    {
      id: "router-config",
      label: "Configurar roteador",
      description: "Modo de acesso e SNMP"
    },
    {
      id: "router-monitor",
      label: "Monitoramento",
      description: "Uptime, status e trafego"
    },
    {
      id: "devices",
      label: "Dispositivos",
      description: "Inventario da rede"
    },
    {
      id: "traffic",
      label: "Trafego",
      description: "Amostras por dispositivo"
    }
  ];

  const scrollToSection = (sectionId) => {
    const section = document.getElementById(sectionId);
    if (section) {
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const handleRouterChange = (event) => {
    const { name, value, type, checked } = event.target;
    setRouterConfig((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value
    }));
  };

  const handleRouterSubmit = async (event) => {
    event.preventDefault();
    setRouterStatus({ type: "loading", message: "Salvando configuracao..." });
    const snmpPort = Number(routerConfig.snmp_port) || 161;
    const payload = {
      router_ip: routerConfig.router_ip,
      access_mode: routerConfig.access_mode,
      snmp_enabled: routerConfig.snmp_enabled,
      snmp_community: routerConfig.snmp_enabled ? routerConfig.snmp_community : null,
      snmp_port: routerConfig.snmp_enabled ? snmpPort : 161,
      username: requiresCredentials ? routerConfig.username : null,
      password: requiresCredentials ? routerConfig.password : null
    };
    try {
      const saved = await saveRouterConfig(payload);
      setRouterConfig({ ...emptyConfig, ...(saved ?? routerConfig) });
      setRouterStatus({ type: "success", message: "Configuracao salva com sucesso." });
      await fetchRouterMetrics();
    } catch (error) {
      setRouterStatus({
        type: "error",
        message: error?.message ?? "Erro ao salvar configuracao."
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

      <section className="route-cards">
        {routes.map((route) => (
          <button
            className="route-card"
            key={route.id}
            type="button"
            onClick={() => scrollToSection(route.id)}
          >
            <span className="route-label">{route.label}</span>
            <span className="route-description">{route.description}</span>
          </button>
        ))}
      </section>

      <section className="grid">
        <div className="panel" id="router-config">
          <div className="panel-header">
            <div>
              <h2>Acesso ao roteador</h2>
              <p>Informe o IP, modo de acesso e configuracao SNMP.</p>
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
                Modo de acesso
                <select
                  name="access_mode"
                  value={routerConfig.access_mode}
                  onChange={handleRouterChange}
                >
                  <option value="local_admin">Local admin</option>
                  <option value="cloud_only">Cloud-only</option>
                  <option value="isp_managed">ISP managed</option>
                </select>
              </label>
              <label className="toggle">
                SNMP habilitado
                <input
                  type="checkbox"
                  name="snmp_enabled"
                  checked={routerConfig.snmp_enabled}
                  onChange={handleRouterChange}
                />
              </label>
              {routerConfig.snmp_enabled ? (
                <>
                  <label>
                    Comunidade SNMP
                    <input
                      name="snmp_community"
                      value={routerConfig.snmp_community}
                      onChange={handleRouterChange}
                      placeholder="public"
                      required={routerConfig.snmp_enabled}
                    />
                  </label>
                  <label>
                    Porta SNMP
                    <input
                      type="number"
                      min="1"
                      max="65535"
                      name="snmp_port"
                      value={routerConfig.snmp_port}
                      onChange={handleRouterChange}
                      required={routerConfig.snmp_enabled}
                    />
                  </label>
                </>
              ) : null}
              {requiresCredentials ? (
                <>
                  <label>
                    Usuario
                    <input
                      name="username"
                      value={routerConfig.username}
                      onChange={handleRouterChange}
                      placeholder="admin"
                      required={requiresCredentials}
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
                      required={requiresCredentials}
                    />
                  </label>
                </>
              ) : null}
            </div>
            {!requiresCredentials ? (
              <p className="hint">
                Credenciais locais nao sao necessarias neste modo. O monitoramento
                usa SNMP read-only (se disponivel) ou coleta passiva via agente local.
              </p>
            ) : null}
            {routerConfig.snmp_enabled ? (
              <p className="hint">
                SNMP read-only ativo. Garanta que o roteador permita consultas na rede local.
              </p>
            ) : (
              <p className="hint">SNMP desativado. Ative para coletar metricas.</p>
            )}
            <div className="form-actions">
              <button className="primary" type="submit">
                Salvar configuracoes
              </button>
              <span className={`hint ${routerStatus.type}`}>{routerStatus.message}</span>
            </div>
            {errors.router ? <p className="hint error">{errors.router}</p> : null}
          </form>
        </div>

        <div className="panel" id="router-monitor">
          <div className="panel-header">
            <div>
              <h2>Monitoramento do roteador</h2>
              <p>Coleta via SNMP read-only quando habilitado.</p>
            </div>
            <button
              className="ghost"
              type="button"
              onClick={fetchRouterMetrics}
              disabled={routerMetricsStatus.type === "loading" || !routerConfig.router_ip}
            >
              {routerMetricsStatus.type === "loading" ? "Coletando..." : "Coletar agora"}
            </button>
          </div>
          {routerMetrics ? (
            <>
              <div className="stats-grid">
                <div className="stat-card">
                  <span>Status</span>
                  <strong className={`status-text ${statusClass(routerMetrics.status)}`}>
                    {statusLabel(routerMetrics.status)}
                  </strong>
                </div>
                <div className="stat-card">
                  <span>Modo</span>
                  <strong>{routerMetrics.monitoring_mode ?? "—"}</strong>
                </div>
                <div className="stat-card">
                  <span>Uptime</span>
                  <strong>{routerMetrics.uptime ?? "—"}</strong>
                </div>
                <div className="stat-card">
                  <span>Interfaces</span>
                  <strong>
                    {routerMetrics.interfaces_up ?? 0}/{routerMetrics.interface_count ?? 0}
                  </strong>
                </div>
                <div className="stat-card">
                  <span>Trafego total</span>
                  <strong>
                    {formatBytes(routerMetrics.total_in_octets)} /{" "}
                    {formatBytes(routerMetrics.total_out_octets)}
                  </strong>
                </div>
              </div>
              <div className="status-row">
                {routerMetrics.wan_status !== undefined && routerMetrics.wan_status !== null ? (
                  <span className={`status-pill ${statusClass(routerMetrics.wan_status)}`}>
                    WAN {statusLabel(routerMetrics.wan_status)}
                  </span>
                ) : null}
                {routerMetrics.lan_status !== undefined && routerMetrics.lan_status !== null ? (
                  <span className={`status-pill ${statusClass(routerMetrics.lan_status)}`}>
                    LAN {statusLabel(routerMetrics.lan_status)}
                  </span>
                ) : null}
                {routerMetrics.reachable !== undefined ? (
                  <span className={`status-pill ${routerMetrics.reachable ? "ok" : "error"}`}>
                    Ping {routerMetrics.reachable ? "ok" : "falhou"}
                  </span>
                ) : null}
                {routerMetrics.latency_ms !== null && routerMetrics.latency_ms !== undefined ? (
                  <span className="status-pill warn">
                    Latencia {Number(routerMetrics.latency_ms).toFixed(0)} ms
                  </span>
                ) : null}
              </div>
              {routerMetrics.snmp_error ? (
                <p className="hint error">SNMP erro: {routerMetrics.snmp_error}</p>
              ) : null}
              {routerMetrics.snmp_limited ? (
                <p className="hint warn">
                  SNMP limitado ao system MIB. Interfaces nao expostas.
                </p>
              ) : null}
              {routerMetrics.monitoring_mode === "snmp" ? (
                routerInterfaces.length === 0 ? (
                  <p className="empty">Nenhuma interface SNMP encontrada.</p>
                ) : (
                  <div className="table table-interfaces">
                    <div className="table-row header">
                      <span>Interface</span>
                      <span>Status</span>
                      <span>Entrada</span>
                      <span>Saida</span>
                    </div>
                    {routerInterfaces.slice(0, 8).map((iface) => (
                      <div className="table-row" key={iface.index ?? iface.name}>
                        <span>{iface.name}</span>
                        <span className={`status-pill ${statusClass(iface.oper_status)}`}>
                          {statusLabel(iface.oper_status)}
                        </span>
                        <span>{formatBytes(iface.in_octets)}</span>
                        <span>{formatBytes(iface.out_octets)}</span>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                <p className="hint">
                  Monitoramento passivo ativo. Sem interfaces SNMP disponiveis.
                </p>
              )}
              {routerMetrics.collected_at ? (
                <p className="hint">Ultima coleta: {formatDateTime(routerMetrics.collected_at)}</p>
              ) : null}
            </>
          ) : (
            <p className="empty">
              {snmpConfigured
                ? "Sem dados de monitoramento. Tente coletar novamente."
                : "SNMP desativado ou nao configurado."}
            </p>
          )}
          {routerMetricsStatus.message ? (
            <p className={`hint ${routerMetricsStatus.type}`}>{routerMetricsStatus.message}</p>
          ) : null}
        </div>

        <div className="panel" id="devices">
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

        <div className="panel wide" id="traffic">
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
