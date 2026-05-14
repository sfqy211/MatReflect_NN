import type { FileListItem, TrainModelItem } from '../../types/api'
import { TEST_SET_20 } from '../../lib/materials'
import { ModelParameterForm } from '../ModelParameterForm'
import { MaterialSelector } from '../MaterialSelector'
import { Button } from '../ui/Button'
import { Field } from '../ui/Field'
import { normalizeBinaryName } from './utils'

export type ReconstructTabProps = {
  activeModel: TrainModelItem
  merlDir: string
  setMerlDir: (v: string) => void
  dataset: 'MERL' | 'EPFL'
  setDataset: (v: 'MERL' | 'EPFL') => void
  condaEnv: string
  reconstructCondaEnv: string
  setReconstructCondaEnv: (v: string) => void
  reconstructOutputDir: string
  setReconstructOutputDir: (v: string) => void
  reconstructCheckpoint: string
  setReconstructCheckpoint: (v: string) => void
  neuralDevice: 'cpu' | 'cuda'
  setNeuralDevice: (v: 'cpu' | 'cuda') => void
  epochs: number
  setEpochs: (v: number) => void
  cudaDevice: string
  setCudaDevice: (v: string) => void
  sparseSamples: number
  setSparseSamples: (v: number) => void
  parameterValues: Record<string, unknown>
  setParameterValues: React.Dispatch<React.SetStateAction<Record<string, unknown>>>
  reconstructSelectedMaterials: string[]
  setReconstructSelectedMaterials: (v: string[]) => void
  materialItems: FileListItem[]
  materialsQueryError: Error | null
  startReconstruct: () => void
  isReconstructPending: boolean
}

export function ReconstructTab(props: ReconstructTabProps) {
  const {
    activeModel,
    merlDir, setMerlDir,
    dataset, setDataset,
    condaEnv,
    reconstructCondaEnv, setReconstructCondaEnv,
    reconstructOutputDir, setReconstructOutputDir,
    reconstructCheckpoint, setReconstructCheckpoint,
    neuralDevice, setNeuralDevice,
    epochs, setEpochs,
    cudaDevice, setCudaDevice,
    sparseSamples, setSparseSamples,
    parameterValues, setParameterValues,
    reconstructSelectedMaterials, setReconstructSelectedMaterials,
    materialItems, materialsQueryError,
    startReconstruct, isReconstructPending,
  } = props

  return (
    <section className="models-section">
      <div className="detail-board__lead">
        <h3>重建</h3>
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '0 0 12px' }}>
        从训练 Checkpoint 重建材质输出文件，重建完成后可前往渲染模块进行可视化。
      </p>
      <div className="render-form-grid">
        <Field label="材质目录">
          <input value={merlDir} onChange={(e) => setMerlDir(e.target.value)} />
        </Field>
        <Field label="数据集">
          <select value={dataset} onChange={(e) => setDataset(e.target.value as 'MERL' | 'EPFL')}>
            <option value="MERL">MERL</option>
            <option value="EPFL">EPFL</option>
          </select>
        </Field>
        <Field label="Conda 环境">
          <input value={reconstructCondaEnv} onChange={(e) => setReconstructCondaEnv(e.target.value)} placeholder={condaEnv || '自动检测'} />
        </Field>
        <Field label="输出目录">
          <input value={reconstructOutputDir} onChange={(e) => setReconstructOutputDir(e.target.value)} placeholder="默认由模型配置决定" />
        </Field>
      </div>

      {/* Adapter-specific fields */}
      {activeModel.adapter === 'neural-pytorch' && (
        <div className="render-form-grid" style={{ marginTop: 12 }}>
          <Field label="训练设备">
            <select value={neuralDevice} onChange={(e) => setNeuralDevice(e.target.value as 'cpu' | 'cuda')}>
              <option value="cpu">cpu</option>
              <option value="cuda">cuda</option>
            </select>
          </Field>
          <Field label="Epochs">
            <input type="number" value={epochs} onChange={(e) => setEpochs(Number(e.target.value) || 1)} />
          </Field>
        </div>
      )}
      {activeModel.adapter === 'hyper-family' && (
        <div className="render-form-grid" style={{ marginTop: 12 }}>
          <Field label="Checkpoint">
            <input value={reconstructCheckpoint} onChange={(e) => setReconstructCheckpoint(e.target.value)} />
          </Field>
          <Field label="CUDA 设备">
            <input value={cudaDevice} onChange={(e) => setCudaDevice(e.target.value)} />
          </Field>
          <Field label="稀疏采样点数">
            <input type="number" value={sparseSamples} onChange={(e) => setSparseSamples(Number(e.target.value) || 1)} />
          </Field>
        </div>
      )}
      {activeModel.adapter === 'custom-cli' && (
        <div className="render-form-grid" style={{ marginTop: 12 }}>
          <Field label="Checkpoint">
            <input value={reconstructCheckpoint} onChange={(e) => setReconstructCheckpoint(e.target.value)} />
          </Field>
          {activeModel.parameters && activeModel.parameters.length > 0 && (
            <ModelParameterForm
              parameters={activeModel.parameters}
              values={parameterValues}
              onChange={(key, value) => setParameterValues((prev) => ({ ...prev, [key]: value }))}
            />
          )}
        </div>
      )}

      {/* Material selection */}
      <div style={{ marginTop: 16 }}>
        <Field label="重建材质">
          <MaterialSelector
            title="选择需要重建的材质"
            items={materialItems}
            selectedItems={reconstructSelectedMaterials}
            onSelectionChange={setReconstructSelectedMaterials}
            error={materialsQueryError}
            emptyMessage="请检查 data/inputs/binary 下是否存在 .binary 文件。"
            searchPlaceholder="搜索 MERL 材质"
            formatName={normalizeBinaryName}
            presets={[
              {
                label: '预设 20',
                filter: (items) =>
                  items
                    .filter((item) => TEST_SET_20.includes(normalizeBinaryName(item.name)))
                    .map((item) => item.name)
              }
            ]}
          />
        </Field>
      </div>

      <div className="render-actions" style={{ marginTop: 12 }}>
        <Button
          type="button"
          variant="primary"
          onClick={() => void startReconstruct()}
          disabled={reconstructSelectedMaterials.length === 0 || isReconstructPending}
        >
          {isReconstructPending ? '重建中...' : '启动重建'}
        </Button>
      </div>
    </section>
  )
}
