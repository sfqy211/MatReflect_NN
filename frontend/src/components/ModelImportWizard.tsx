import { useState } from 'react'
import type { ModelImportRequest } from '../types/api'
import { Button } from './ui/Button'
import { Field } from './ui/Field'

type ModelImportWizardProps = {
  onImport: (request: ModelImportRequest) => void
  onCancel: () => void
  isPending: boolean
}

export function ModelImportWizard({ onImport, onCancel, isPending }: ModelImportWizardProps) {
  const [sourceDir, setSourceDir] = useState('')
  const [modelKey, setModelKey] = useState('')
  const [label, setLabel] = useState('')
  const [description, setDescription] = useState('')
  const [trainScript, setTrainScript] = useState('')
  const [trainArgsTemplate, setTrainArgsTemplate] = useState('')
  const [reconstructScript, setReconstructScript] = useState('')
  const [reconstructArgsTemplate, setReconstructArgsTemplate] = useState('')
  const [supportsTraining, setSupportsTraining] = useState(true)
  const [supportsReconstruction, setSupportsReconstruction] = useState(false)
  const [renderModes, setRenderModes] = useState('npy')

  const handleSubmit = () => {
    onImport({
      source_dir: sourceDir,
      model_key: modelKey,
      label: label || modelKey,
      description,
      commands_doc_filename: 'COMMANDS.md',
      train_script: trainScript,
      train_args_template: trainArgsTemplate,
      reconstruct_script: reconstructScript,
      reconstruct_args_template: reconstructArgsTemplate,
      supports_training: supportsTraining,
      supports_reconstruction: supportsReconstruction,
      supports_extract: false,
      supports_decode: false,
      supports_runs: false,
      render_modes: renderModes.split(',').map((s) => s.trim()).filter(Boolean),
      parameters: [],
    })
  }

  const canSubmit = sourceDir.trim() && modelKey.trim() && label.trim()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '12px 0' }}>
      <h3 style={{ margin: 0 }}>导入自定义模型</h3>
      <p className="muted" style={{ margin: 0 }}>
        导入包含 requirements.txt 的模型目录，系统将自动创建对应的虚拟环境。
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
        <Field label="模型目录路径">
          <input value={sourceDir} onChange={(e) => setSourceDir(e.target.value)} placeholder="models/my-custom-model" />
        </Field>
        <Field label="模型 Key（英文标识，仅限小写字母、数字、连字符）">
          <input value={modelKey} onChange={(e) => setModelKey(e.target.value.replace(/[^a-z0-9-]/g, '-').toLowerCase())} placeholder="my-custom-model" />
        </Field>
        <Field label="显示名称">
          <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="My Custom Model" />
        </Field>
        <Field label="描述">
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="自定义模型说明" />
        </Field>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
        <Field label="训练脚本路径（相对于模型目录）">
          <input value={trainScript} onChange={(e) => setTrainScript(e.target.value)} placeholder="train.py" />
        </Field>
        <Field label="训练参数模板">
          <input value={trainArgsTemplate} onChange={(e) => setTrainArgsTemplate(e.target.value)} placeholder="--data {data_dir} --epochs {epochs} --output {output_dir}" />
        </Field>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
        <Field label="重建脚本路径（可选）">
          <input value={reconstructScript} onChange={(e) => setReconstructScript(e.target.value)} placeholder="reconstruct.py" />
        </Field>
        <Field label="重建参数模板">
          <input value={reconstructArgsTemplate} onChange={(e) => setReconstructArgsTemplate(e.target.value)} placeholder="--checkpoint {checkpoint} --input {input} --output {output_dir}" />
        </Field>
      </div>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input type="checkbox" checked={supportsTraining} onChange={(e) => setSupportsTraining(e.target.checked)} />
          <span>支持训练</span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input type="checkbox" checked={supportsReconstruction} onChange={(e) => setSupportsReconstruction(e.target.checked)} />
          <span>支持重建</span>
        </label>
      </div>

      <Field label="渲染模式（逗号分隔）">
        <input value={renderModes} onChange={(e) => setRenderModes(e.target.value)} placeholder="npy, fullbin" />
      </Field>

      <div style={{ display: 'flex', gap: 12 }}>
        <Button type="button" variant="primary" onClick={handleSubmit} disabled={!canSubmit || isPending}>
          {isPending ? '导入中...' : '导入模型'}
        </Button>
        <Button type="button" onClick={onCancel}>
          取消
        </Button>
      </div>
    </div>
  )
}
