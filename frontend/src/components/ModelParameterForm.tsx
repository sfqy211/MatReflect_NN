import type { ModelParameter } from '../types/api'
import { Field } from './ui/Field'

type ModelParameterFormProps = {
  parameters: ModelParameter[]
  values: Record<string, unknown>
  onChange: (key: string, value: unknown) => void
}

export function ModelParameterForm({ parameters, values, onChange }: ModelParameterFormProps) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
      {parameters.map((param) => (
        <Field key={param.key} label={param.label}>
          <ParameterInput
            param={param}
            value={values[param.key] ?? param.default}
            onChange={(v) => onChange(param.key, v)}
          />
        </Field>
      ))}
    </div>
  )
}

function ParameterInput({
  param,
  value,
  onChange,
}: {
  param: ModelParameter
  value: unknown
  onChange: (value: unknown) => void
}) {
  if (param.type === 'bool') {
    return (
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          {value ? '是' : '否'}
        </span>
      </label>
    )
  }

  if (param.type === 'select' && param.options) {
    return (
      <select value={String(value)} onChange={(e) => onChange(e.target.value)}>
        {param.options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    )
  }

  if (param.type === 'int') {
    return (
      <input
        type="number"
        min={param.min ?? undefined}
        max={param.max ?? undefined}
        step={1}
        value={Number(value ?? param.default ?? 0)}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
      />
    )
  }

  if (param.type === 'float') {
    return (
      <input
        type="number"
        min={param.min ?? undefined}
        max={param.max ?? undefined}
        step="any"
        value={Number(value ?? param.default ?? 0)}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
      />
    )
  }

  // type === 'str' or default
  return (
    <input
      type="text"
      value={String(value ?? param.default ?? '')}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

/** Helper: 初始化参数表单默认值 */
export function initParameterValues(parameters: ModelParameter[]): Record<string, unknown> {
  const values: Record<string, unknown> = {}
  for (const param of parameters) {
    values[param.key] = param.default
  }
  return values
}
