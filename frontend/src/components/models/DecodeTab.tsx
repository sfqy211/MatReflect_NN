import type { FileListItem, TrainModelItem } from '../../types/api'
import { MaterialSelector } from '../MaterialSelector'
import { Button } from '../ui/Button'
import { Field } from '../ui/Field'

export type DecodeTabProps = {
  activeModel: TrainModelItem
  ptDir: string
  setPtDir: (v: string) => void
  fullbinOutputDir: string
  setFullbinOutputDir: (v: string) => void
  condaEnv: string
  setCondaEnv: (v: string) => void
  cudaDevice: string
  setCudaDevice: (v: string) => void
  dataset: 'MERL' | 'EPFL'
  setDataset: (v: 'MERL' | 'EPFL') => void
  selectedPts: string[]
  setSelectedPts: (v: string[]) => void
  ptItems: FileListItem[]
  ptFilesQueryError: Error | null
  startDecode: () => void
}

export function DecodeTab(props: DecodeTabProps) {
  const {
    ptDir, setPtDir,
    fullbinOutputDir, setFullbinOutputDir,
    condaEnv, setCondaEnv,
    cudaDevice, setCudaDevice,
    dataset, setDataset,
    selectedPts, setSelectedPts,
    ptItems, ptFilesQueryError,
    startDecode,
  } = props

  return (
    <section className="models-section">
      <div className="detail-board__lead">
        <h3>潜向量解码</h3>
      </div>
      <div className="render-form-grid">
        <Field label="潜向量目录">
          <input value={ptDir} onChange={(event) => setPtDir(event.target.value)} />
        </Field>
        <Field label="HyperBRDF 输出目录">
          <input value={fullbinOutputDir} onChange={(event) => setFullbinOutputDir(event.target.value)} />
        </Field>
        <Field label="Conda 环境">
          <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
        </Field>
        <Field label="CUDA 设备">
          <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
        </Field>
        <Field label="数据集">
          <select value={dataset} onChange={(event) => setDataset(event.target.value as 'MERL' | 'EPFL')}>
            <option value="MERL">MERL</option>
            <option value="EPFL">EPFL</option>
          </select>
        </Field>
      </div>
      <div style={{ marginTop: 16 }}>
        <Field label="潜向量文件">
          <MaterialSelector
            title="选择潜向量文件"
            items={ptItems}
            selectedItems={selectedPts}
            onSelectionChange={setSelectedPts}
            error={ptFilesQueryError}
            emptyMessage="请先完成参数提取，或检查潜向量目录是否正确。"
            searchPlaceholder="搜索已提取的 .pt 文件"
            formatName={(name) => name.replace(/\.pt$/i, '')}
          />
        </Field>
      </div>
      <div className="render-actions">
        <Button type="button" variant="primary" onClick={() => void startDecode()} disabled={selectedPts.length === 0}>
          执行 HyperBRDF 解码
        </Button>
      </div>
    </section>
  )
}
