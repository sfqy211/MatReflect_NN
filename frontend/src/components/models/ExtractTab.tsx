import type { FileListItem, TrainModelItem } from '../../types/api'
import { MaterialSelector } from '../MaterialSelector'
import { Button } from '../ui/Button'
import { Field } from '../ui/Field'
import { normalizeBinaryName } from './utils'

export type ExtractTabProps = {
  activeModel: TrainModelItem
  merlDir: string
  setMerlDir: (v: string) => void
  checkpointPath: string
  setCheckpointPath: (v: string) => void
  extractOutputDir: string
  setExtractOutputDir: (v: string) => void
  setPtDir: (v: string) => void
  condaEnv: string
  setCondaEnv: (v: string) => void
  dataset: 'MERL' | 'EPFL'
  setDataset: (v: 'MERL' | 'EPFL') => void
  sparseSamples: number
  setSparseSamples: (v: number) => void
  trainSeed: number
  setTrainSeed: (v: number) => void
  selectedMaterials: string[]
  setSelectedMaterials: (v: string[]) => void
  materialItems: FileListItem[]
  materialsQueryError: Error | null
  startExtract: () => void
}

export function ExtractTab(props: ExtractTabProps) {
  const {
    merlDir, setMerlDir,
    checkpointPath, setCheckpointPath,
    extractOutputDir, setExtractOutputDir,
    setPtDir,
    condaEnv, setCondaEnv,
    dataset, setDataset,
    sparseSamples, setSparseSamples,
    trainSeed, setTrainSeed,
    selectedMaterials, setSelectedMaterials,
    materialItems, materialsQueryError,
    startExtract,
  } = props

  return (
    <section className="models-section">
      <div className="detail-board__lead">
        <h3>参数提取</h3>
      </div>
      <div className="render-form-grid">
        <Field label="材质目录">
          <input value={merlDir} onChange={(event) => setMerlDir(event.target.value)} />
        </Field>
        <Field label="Checkpoint">
          <input value={checkpointPath} onChange={(event) => setCheckpointPath(event.target.value)} />
        </Field>
        <Field label="PT 输出目录">
          <input
            value={extractOutputDir}
            onChange={(event) => {
              setExtractOutputDir(event.target.value)
              setPtDir(event.target.value)
            }}
          />
        </Field>
        <Field label="Conda 环境">
          <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
        </Field>
        <Field label="数据集">
          <select value={dataset} onChange={(event) => setDataset(event.target.value as 'MERL' | 'EPFL')}>
            <option value="MERL">MERL</option>
            <option value="EPFL">EPFL</option>
          </select>
        </Field>
        <Field label="稀疏采样点数">
          <input type="number" value={sparseSamples} onChange={(event) => setSparseSamples(Number(event.target.value) || 1)} />
        </Field>
        <Field label="随机种子">
          <input type="number" value={trainSeed} onChange={(event) => setTrainSeed(Number(event.target.value) || 0)} />
        </Field>
      </div>
      <div style={{ marginTop: 16 }}>
        <Field label="材质选择">
          <MaterialSelector
            title="选择固定材质"
            items={materialItems}
            selectedItems={selectedMaterials}
            onSelectionChange={setSelectedMaterials}
            error={materialsQueryError}
            emptyMessage="请检查 data/inputs/binary 下是否存在 .binary 文件。"
            searchPlaceholder="搜索 MERL 材质"
            formatName={normalizeBinaryName}
          />
        </Field>
      </div>
      <div className="render-actions">
        <Button
          type="button"
          variant="primary"
          onClick={() => void startExtract()}
          disabled={dataset === 'MERL' && selectedMaterials.length === 0}
        >
          启动参数提取
        </Button>
      </div>
    </section>
  )
}
