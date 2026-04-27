import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

type CommandsDocPanelProps = {
  docPath: string | null
  onClose: () => void
}

export function CommandsDocPanel({ docPath, onClose }: CommandsDocPanelProps) {
  const [isOpen, setIsOpen] = useState(true)

  const docQuery = useQuery({
    queryKey: ['commands-doc', docPath],
    queryFn: async () => {
      if (!docPath) return ''
      try {
        const res = await fetch(`/media/outputs/${docPath}`)
        if (!res.ok) return ''
        return await res.text()
      } catch {
        return ''
      }
    },
    enabled: Boolean(docPath),
  })

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          background: 'var(--surface-soft)',
          border: '1px solid var(--border)',
          borderRadius: '4px 0 0 4px',
          padding: '6px 10px',
          cursor: 'pointer',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
        }}
        title="显示命令文档"
      >
        📋 命令
      </button>
    )
  }

  return (
    <div
      style={{
        position: 'absolute',
        right: 0,
        top: 0,
        bottom: 0,
        width: 280,
        background: 'var(--surface-base)',
        borderLeft: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
        <strong style={{ fontSize: '0.85rem' }}>命令参考</strong>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.8rem' }}
            title="关闭浮窗"
          >
            ✕
          </button>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.8rem' }}
            title="折叠"
          >
            ◁
          </button>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '8px 12px', fontSize: '0.82rem', lineHeight: 1.6 }}>
        {docPath ? (
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0, color: 'var(--text-muted)' }}>
            {docQuery.data || '加载中...'}
          </pre>
        ) : (
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>
            当前模型没有配置命令文档。请在模型目录下创建 COMMANDS.md 文件。
          </p>
        )}
      </div>
    </div>
  )
}
