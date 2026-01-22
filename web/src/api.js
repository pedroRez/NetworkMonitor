const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const request = async (path, options = {}) => {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = data?.detail ?? "";
    } catch (error) {
      detail = "";
    }
    const message = detail ? `Erro ${response.status}: ${detail}` : `Erro ${response.status}`;
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
};

export const getHealth = () => request("/health");
export const getDevices = () => request("/devices");
export const getTraffic = () => request("/traffic");
export const getRouterConfig = () => request("/router-config");
export const getRouterMetrics = () => request("/router-metrics");
export const saveRouterConfig = (payload) =>
  request("/router-config", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
