import { useState } from 'react'

import { FileSelectionModal } from './FileSelectionModal'
import type { FileListItem } from '../types/api'

type MaterialSelectorProps = {
  title?: string
  items: FileListItem[] | string[]
  selectedItems: string[]
  onSelectionChange: (selected: string[]) => void
  multiSelect?: boolean
  error?: Error | null
  emptyMessage?: string
  searchPlaceholder?: string
  formatName?: (name: string) => string
  presets?: Array<{ label: string; filter: (items: FileListItem[]) => string[] }>
  disabled?: boolean
}

export function MaterialSelector({
  title = '选择材质',
  items,
  selectedItems,
  onSelectionChange,
  multiSelect = true,
  error,
  emptyMessage = '没有可用的材质。',
  searchPlaceholder = '搜索材质...',
  formatName = (name) => name,
  presets = [],
  disabled = false,
}: MaterialSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)

  const normalizedItems: FileListItem[] = items.length > 0 && typeof items[0] === 'string'
    ? (items as string[]).map((name) => ({ name: name as string, path: name as string, is_dir: false, size: 0, modified_at: '' }))
    : (items as FileListItem[])

  const displayCount = selectedItems.length
  const previewText =
    displayCount === 0
      ? '未选择材质'
      : displayCount <= 3
        ? selectedItems.join(', ')
        : `${selectedItems.slice(0, 3).join(', ')} 等 ${displayCount} 项`

  return (
    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flex: 1, minWidth: 0 }}>
      <button
        type="button"
        className="theme-toggle"
        onClick={() => setIsOpen(true)}
        disabled={disabled}
        style={{ flexShrink: 0, whiteSpace: 'nowrap' }}
      >
        {multiSelect ? `${title} (${displayCount})` : displayCount > 0 ? selectedItems[0] : `-- ${title} --`}
      </button>
      {multiSelect && (
        <span className="muted" style={{ fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {previewText}
        </span>
      )}

      <FileSelectionModal
        title={title}
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        items={normalizedItems}
        selectedItems={selectedItems}
        onSelectionChange={onSelectionChange}
        error={error}
        emptyMessage={emptyMessage}
        searchPlaceholder={searchPlaceholder}
        formatName={formatName}
        presets={presets}
        multiSelect={multiSelect}
      />
    </div>
  )
}
