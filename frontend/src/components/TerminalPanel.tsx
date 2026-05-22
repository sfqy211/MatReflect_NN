import { useEffect, useRef, useState, useCallback, useImperativeHandle, forwardRef } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import { BACKEND_ORIGIN } from '../lib/api'

export type TerminalPanelHandle = {
  /** 向终端发送一条命令 */
  sendCommand: (cmd: string) => void
}

type TerminalPanelProps = {
  sessionId: string | null
  onClose?: () => void
  condaEnv?: string
  workingDir?: string
}

export const TerminalPanel = forwardRef<TerminalPanelHandle, TerminalPanelProps>(
  function TerminalPanel({ sessionId, onClose, condaEnv, workingDir }, ref) {
  const termRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const termInstanceRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [inputValue, setInputValue] = useState('')
  const [connected, setConnected] = useState(false)
  const historyRef = useRef<string[]>([])
  const historyIndexRef = useRef(-1)

  // Create terminal instance + resize observer
  useEffect(() => {
    if (!termRef.current) return

    const term = new Terminal({
      cursorBlink: false,
      fontSize: 13,
      fontFamily: 'Cascadia Code, Fira Code, Consolas, monospace',
      disableStdin: true,
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
    term.open(termRef.current)

    requestAnimationFrame(() => {
      try { fitAddon.fit() } catch { /* ignore */ }
    })

    termInstanceRef.current = term
    fitAddonRef.current = fitAddon

    const resizeObserver = new ResizeObserver(() => {
      try { fitAddon.fit() } catch { /* ignore */ }
    })
    resizeObserver.observe(termRef.current)

    return () => {
      resizeObserver.disconnect()
      term.dispose()
      termInstanceRef.current = null
      fitAddonRef.current = null
    }
  }, [])

  // WebSocket connection
  useEffect(() => {
    if (!sessionId) return
    const term = termInstanceRef.current
    if (!term) return

    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      wsRef.current.close()
      wsRef.current = null
    }

    let disposed = false

    const wsProtocol = BACKEND_ORIGIN.startsWith('https') ? 'wss' : 'ws'
    const wsHost = new URL(BACKEND_ORIGIN).host
    const params = new URLSearchParams()
    if (condaEnv) params.set('conda_env', condaEnv)
    if (workingDir) params.set('working_dir', workingDir)
    const qs = params.toString()
    const wsUrl = `${wsProtocol}://${wsHost}/ws/pty/${sessionId}${qs ? '?' + qs : ''}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (disposed) return
      setConnected(true)
    }

    ws.onmessage = (event) => {
      if (disposed) return
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'output' && msg.data) {
          term.write(msg.data)
        }
        // 'ready' type is only for signaling; the actual "已就绪" message
        // comes through the output queue from the backend.
      } catch {
        term.write(event.data)
      }
    }

    ws.onclose = () => {
      if (disposed) return
      setConnected(false)
      term.write('\r\n[终端] 连接已断开\r\n')
    }

    ws.onerror = () => {
      if (disposed) return
      setConnected(false)
      term.write('\r\n[终端] 连接错误\r\n')
    }

    return () => {
      disposed = true
      ws.onclose = null
      ws.onerror = null
      ws.close()
      wsRef.current = null
      setConnected(false)
    }
  }, [sessionId])

  const sendCommand = useCallback((cmd: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    // Send to backend — cmd.exe will echo the command in its output
    ws.send(JSON.stringify({ type: 'input', data: cmd + '\r' }))

    // Save to history
    if (cmd.trim()) {
      historyRef.current.push(cmd)
      if (historyRef.current.length > 100) historyRef.current.shift()
    }
    historyIndexRef.current = -1
  }, [])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const cmd = inputValue.trim()
      if (cmd) {
        sendCommand(cmd)
      } else {
        // Empty Enter — just send \r
        const ws = wsRef.current
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'input', data: '\r' }))
        }
      }
      setInputValue('')
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const history = historyRef.current
      if (history.length === 0) return
      const idx = historyIndexRef.current
      const newIdx = idx < 0 ? history.length - 1 : Math.max(0, idx - 1)
      historyIndexRef.current = newIdx
      setInputValue(history[newIdx])
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      const history = historyRef.current
      const idx = historyIndexRef.current
      if (idx < 0) return
      const newIdx = idx + 1
      if (newIdx >= history.length) {
        historyIndexRef.current = -1
        setInputValue('')
      } else {
        historyIndexRef.current = newIdx
        setInputValue(history[newIdx])
      }
    }
  }, [inputValue, sendCommand])

  // Expose sendCommand for programmatic use via ref
  useImperativeHandle(ref, () => ({
    sendCommand,
  }), [sendCommand])

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        minHeight: 200,
      }}
    >
      {/* Terminal output area (read-only) */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
        <div ref={termRef} style={{ width: '100%', height: '100%' }} />
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
              zIndex: 10,
            }}
            title="关闭终端"
          >
            ✕
          </button>
        ) : null}
      </div>

      {/* Input bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 8px',
          background: '#1E293B',
          borderTop: '1px solid #334155',
          flexShrink: 0,
        }}
      >
        <span
          style={{
            color: '#06B6D4',
            fontFamily: 'Cascadia Code, Fira Code, Consolas, monospace',
            fontSize: 13,
            whiteSpace: 'nowrap',
            userSelect: 'none',
          }}
        >
          {condaEnv ? `(${condaEnv})` : '>'}
        </span>
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!connected}
          placeholder={connected ? '输入命令...' : '等待连接...'}
          spellCheck={false}
          autoComplete="off"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#F8FAFC',
            fontFamily: 'Cascadia Code, Fira Code, Consolas, monospace',
            fontSize: 13,
            padding: '2px 0',
          }}
        />
      </div>
    </div>
  )
})
