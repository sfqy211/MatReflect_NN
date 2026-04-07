import { useState } from 'react';
import { FeedbackPanel } from './FeedbackPanel';

type TerminalDrawerProps = {
  taskId: string | null;
  status: string;
  progress: number;
  logs: string[];
  error?: Error | null;
  onStop?: () => void;
  taskStateMessage?: string | null;
};

export function TerminalDrawer({ taskId, status, progress, logs, error, onStop, taskStateMessage }: TerminalDrawerProps) {
  const [expanded, setExpanded] = useState(false);
  const latestLog = logs.length > 0 ? logs[logs.length - 1] : 'Waiting for tasks...';

  if (!taskId && !expanded && logs.length === 0) {
    return null;
  }

  return (
    <div className={`terminal-drawer ${expanded ? 'terminal-drawer--expanded' : ''}`}>
      <div className="terminal-drawer__header" onClick={() => setExpanded(!expanded)}>
        <div className="terminal-drawer__status">
          <span className={`status-dot status-${status}`} />
          <strong>{taskId ? `[${status}]` : '[Idle]'}</strong>
          <span className="terminal-drawer__latest-log">{latestLog}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {onStop && taskId && ['pending', 'running'].includes(status) && (
            <button 
              className="theme-toggle render-actions--danger" 
              style={{ padding: '2px 8px', fontSize: '11px', minHeight: '24px' }}
              onClick={(e) => {
                e.stopPropagation();
                onStop();
              }}
            >
              停止任务
            </button>
          )}
          <button className="terminal-drawer__toggle">{expanded ? '▼' : '▲'}</button>
        </div>
        {progress > 0 && progress < 100 && (
          <div className="terminal-drawer__progress" style={{ width: `${progress}%` }} />
        )}
      </div>
      
      {expanded && (
        <div className="terminal-drawer__body">
          {taskStateMessage && (
            <FeedbackPanel
              title={status === 'failed' ? '任务失败' : '任务已结束'}
              message={taskStateMessage}
              tone={status === 'failed' ? 'error' : 'info'}
              compact
            />
          )}
          {error && <FeedbackPanel title="操作失败" message={error.message} tone="error" compact />}
          <div className="log-panel">
            {logs.length > 0 ? (
              logs.map((line, index) => (
                <div key={`${index}-${line.slice(0, 16)}`} className="log-line">
                  {line}
                </div>
              ))
            ) : (
              <FeedbackPanel title="等待任务日志" message="启动任务后，这里会持续显示执行输出。" tone="empty" compact />
            )}
          </div>
        </div>
      )}
    </div>
  );
}