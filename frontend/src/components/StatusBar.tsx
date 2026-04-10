import { useEffect, useState } from "react";
import { BACKEND_ORIGIN } from "../lib/api";

type GpuMetric = {
  id: number;
  name: string;
  utilization: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
};

type ActiveTask = {
  task_id: string;
  task_type: string;
  status: string;
  progress: number;
  message: string;
};

type SystemMetrics = {
  cpu: { percent: number };
  memory: { percent: number; used_gb: number; total_gb: number };
  gpus: GpuMetric[];
  active_tasks: ActiveTask[];
};

export function StatusBar() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    let isMounted = true;
    let reconnectTimer: number;

    const connect = () => {
      const wsUrl = BACKEND_ORIGIN.replace(/^http/, "ws") + "/ws/system/metrics";
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data) as SystemMetrics;
          setMetrics(data);
        } catch (e) {
          console.error("Failed to parse metrics", e);
        }
      };

      ws.onclose = () => {
        if (isMounted) {
          reconnectTimer = window.setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  return (
    <footer className="status-bar">
      <div className="status-bar__left">
        <span className="status-bar__item">MatReflect_NN Workspace</span>
        {metrics && metrics.active_tasks && metrics.active_tasks.length > 0 && (
          <div className="status-bar__tasks">
            {metrics.active_tasks.map((task) => (
              <div key={task.task_id} className="status-bar__task-badge">
                <span className="task-type">{task.task_type}</span>
                <span className="task-progress">{task.progress}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="status-bar__right">
        {metrics ? (
          <>
            <div className="status-bar__metric">
              <span className="metric-label">CPU</span>
              <span className="metric-value">{metrics.cpu.percent.toFixed(1)}%</span>
            </div>
            <div className="status-bar__metric">
              <span className="metric-label">RAM</span>
              <span className="metric-value">
                {metrics.memory.used_gb.toFixed(1)} / {metrics.memory.total_gb.toFixed(1)} GB
              </span>
            </div>
            {metrics.gpus.map((gpu) => (
              <div key={gpu.id} className="status-bar__metric" title={gpu.name}>
                <span className="metric-label">GPU {gpu.id}</span>
                <span className="metric-value">{gpu.utilization}%</span>
                <span className="metric-value">
                  {gpu.memory_used_gb.toFixed(1)} / {gpu.memory_total_gb.toFixed(1)} GB
                </span>
              </div>
            ))}
          </>
        ) : (
          <div className="status-bar__item">Connecting to metrics...</div>
        )}
      </div>
    </footer>
  );
}
