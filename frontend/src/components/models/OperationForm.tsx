import type { FileListItem, OperationDef, OperationField } from '../../types/api'
import { TEST_SET_20 } from '../../lib/materials'
import { Button } from '../ui/Button'
import { CheckboxField } from '../ui/CheckboxField'
import { Field } from '../ui/Field'
import { MaterialSelector } from '../MaterialSelector'
import { FeedbackPanel } from '../FeedbackPanel'
import { escapeRegex, normalizeBinaryName } from './utils'

type OperationFormProps = {
  operation: OperationDef
  values: Record<string, unknown>
  onChange: (key: string, value: unknown) => void
  onExecute: (values: Record<string, unknown>) => void
  onPreview: (values: Record<string, unknown>) => void
  isExecuting: boolean
  isPreviewing: boolean
  /** file_picker 字段的数据源，key 为 file_source 值 */
  fileItemsMap?: Record<string, FileListItem[]>
  fileErrorsMap?: Record<string, Error | null>
  executeLabel?: string
  previewLabel?: string
}

export function OperationForm({
  operation,
  values,
  onChange,
  onExecute,
  onPreview,
  isExecuting,
  isPreviewing,
  fileItemsMap = {},
  fileErrorsMap = {},
  executeLabel = '开始执行',
  previewLabel = '预览命令',
}: OperationFormProps) {
  const fields = operation.form?.fields ?? []
  const visibleFields = fields.filter((f) => !f.hidden)

  /** 合并所有字段默认值（含隐藏字段）到提交参数 */
  const mergeDefaults = (vals: Record<string, unknown>): Record<string, unknown> => {
    const merged = { ...vals }
    for (const f of fields) {
      if (merged[f.key] === undefined || merged[f.key] === null || merged[f.key] === '') {
        merged[f.key] = f.default
      }
    }
    return merged
  }

  if (visibleFields.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <FeedbackPanel
          title={`操作 "${operation.label}" 无输入字段`}
          message="点击执行按钮直接运行。"
          tone="info"
          compact
        />
        <div className="render-actions">
          <Button type="button" variant="primary" onClick={() => onExecute(mergeDefaults(values))} disabled={isExecuting}>
            {isExecuting ? '执行中...' : executeLabel}
          </Button>
          <Button type="button" onClick={() => onPreview(mergeDefaults(values))} disabled={isPreviewing}>
            {isPreviewing ? '生成中...' : previewLabel}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {visibleFields.map((field) => {
        const fieldValue = values[field.key] ?? field.default
        return (
          <OperationFieldInput
            key={field.key}
            field={field}
            value={fieldValue}
            onChange={(v) => onChange(field.key, v)}
            fileItems={field.type === 'file_picker' ? fileItemsMap[field.file_source ?? ''] : undefined}
            fileError={field.type === 'file_picker' ? fileErrorsMap[field.file_source ?? ''] ?? undefined : undefined}
          />
        )
      })}
      <div className="render-actions">
        <Button type="button" variant="primary" onClick={() => onExecute(mergeDefaults(values))} disabled={isExecuting}>
          {isExecuting ? '执行中...' : executeLabel}
        </Button>
        <Button type="button" onClick={() => onPreview(mergeDefaults(values))} disabled={isPreviewing}>
          {isPreviewing ? '生成中...' : previewLabel}
        </Button>
      </div>
    </div>
  )
}

// ── Field-level input ──

type OperationFieldInputProps = {
  field: OperationField
  value: unknown
  onChange: (value: unknown) => void
  fileItems?: FileListItem[]
  fileError?: Error | null
}

function OperationFieldInput({ field, value, onChange, fileItems, fileError }: OperationFieldInputProps) {
  switch (field.type) {
    case 'bool':
      return (
        <CheckboxField
          label={field.label}
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
      )

    case 'file_picker': {
      const items = fileItems ?? []
      const selected = Array.isArray(value) ? value as string[] : []
      return (
        <>
          <Field label={field.label}>
            <MaterialSelector
              title={`选择 ${field.label}`}
              items={items}
              selectedItems={selected}
              onSelectionChange={(sel) => onChange(sel)}
              error={fileError ?? undefined}
              emptyMessage="目录中暂无匹配文件。"
              searchPlaceholder={`搜索 ${field.label}`}
              formatName={(name) => {
                const filters = field.file_filter ?? []
                let result = name
                for (const ext of filters) {
                  result = result.replace(new RegExp(`${escapeRegex(ext)}$`, 'i'), '')
                }
                return result
              }}
              presets={
                field.file_source === 'materials'
                  ? [
                      {
                        label: '预设 20',
                        filter: (fileItems) =>
                          fileItems
                            .filter((item) => TEST_SET_20.includes(normalizeBinaryName(item.name)))
                            .map((item) => item.name),
                      },
                    ]
                  : []
              }
            />
          </Field>
          {items.length === 0 && !fileError && (
            <span className="muted" style={{ fontSize: '0.8rem' }}>
              目录中暂无匹配文件，请检查数据目录是否正确。
            </span>
          )}
        </>
      )
    }

    case 'int':
      return (
        <Field label={field.label}>
          <input
            type="number"
            min={field.min ?? undefined}
            max={field.max ?? undefined}
            step={1}
            value={Number(value ?? field.default ?? 0) || 0}
            onChange={(e) => {
              const v = e.target.value === '' ? 0 : Number(e.target.value)
              onChange(field.min !== null && field.min !== undefined && v < field.min ? field.min : v)
            }}
            placeholder={field.placeholder ?? ''}
          />
        </Field>
      )

    case 'float':
      return (
        <Field label={field.label}>
          <input
            type="number"
            min={field.min ?? undefined}
            max={field.max ?? undefined}
            step="any"
            value={Number(value ?? field.default ?? 0) || 0}
            onChange={(e) => onChange(Number(e.target.value) || 0)}
            placeholder={field.placeholder ?? ''}
          />
        </Field>
      )

    case 'select':
      return (
        <Field label={field.label}>
          <select
            value={String(value ?? field.default ?? '')}
            onChange={(e) => onChange(e.target.value)}
          >
            {(field.options ?? []).map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </Field>
      )

    case 'path':
      return (
        <Field label={field.label}>
          <input
            type="text"
            value={String(value ?? field.default ?? '')}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder ?? '输入路径...'}
            readOnly={field.readonly}
            style={field.readonly ? { backgroundColor: 'var(--bg-secondary, #f5f5f5)', color: 'var(--text-secondary, #888)', cursor: 'not-allowed' } : undefined}
          />
        </Field>
      )

    // str / default
    default:
      return (
        <Field label={field.label}>
          <input
            type="text"
            value={String(value ?? field.default ?? '')}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder ?? ''}
          />
        </Field>
      )
  }
}
