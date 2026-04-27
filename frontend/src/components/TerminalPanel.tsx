import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

type TerminalPanelProps = {
  sessionId: string | null
  onClose?: () => void
}

export function TerminalPanel({ sessionId, onClose }: TerminalPanelProps) {
  const terminalRef = useRef<HTMLDivElement>(null)
  const termInstanceRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!terminalRef.current) return

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: 'Cascadia Code, Fira Code, Consolas, monospace',
      theme: {
        background: '#0F172A',
        foreground: '#F8FAFC',
        cursor: '#06B6D4',
        selectionBackground: '#334155',
      },
    })

    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()

    term.loadAddon(fitAddon)
    term.loadAddon(webLinksAddon)
    term.open(terminalRef.current)
    fitAddon.fit()

    termInstanceRef.current = term
    fitAddonRef.current = fitAddon

    const resizeObserver = new ResizeObserver(() => {
      try {
        fitAddon.fit()
      } catch {
        // ignore fit errors during unmount
      }
    })
    resizeObserver.observe(terminalRef.current)

    return () => {
      resizeObserver.disconnect()
      term.dispose()
      termInstanceRef.current = null
      fitAddonRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!sessionId) return
    const term = termInstanceRef.current
    if (!term) return

    // Close previous connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/pty/${sessionId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'output' && msg.data) {
          term.write(msg.data)
        } else if (msg.type === 'ready') {
          term.write(`\r\n[终端] 会话 ${msg.session_id} 已就绪\r\n`)
        }
      } catch {
        // plain text
        term.write(event.data)
      }
    }

    ws.onclose = () => {
      term.write('\r\n[终端] 连接已断开\r\n')
    }

    ws.onerror = () => {
      term.write('\r\n[终端] 连接错误\r\n')
    }

    // Send user input to WebSocket
    const disposable = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'input', data }))
      }
    })

    return () => {
      disposable.dispose()
      ws.close()
      wsRef.current = null
    }
  }, [sessionId])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 200 }}>
      <div ref={terminalRef} style={{ width: '100%', height: '100%' }} />
      {onClose ? (
        <button
          type="button"
          onClick={onClose}
          style={{
            position: 'absolute',
            top: 4,
            right: 8,
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '1.1rem',
            lineHeight: 1,
            padding: '4px',
          }}
          title="关闭终端"
        >
          ✕
        </button>
      ) : null}
    </div>
  )
}
