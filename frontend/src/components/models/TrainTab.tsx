import type { FileListItem, TrainModelItem, TrainRunSummary } from '../../types/api'
import { TEST_SET_20 } from '../../lib/materials'
import { FeedbackPanel } from '../FeedbackPanel'
import { ModelParameterForm } from '../ModelParameterForm'
import { MaterialSelector } from '../MaterialSelector'
import { Button } from '../ui/Button'
import { CheckboxField } from '../ui/CheckboxField'
import { Field } from '../ui/Field'
import { normalizeBinaryName } from './utils'

export type TrainTabProps = {
  activeModel: TrainModelItem | null
  merlDir: string
  setMerlDir: (v: string) => void
  dataset: 'MERL' | 'EPFL'
  setDataset: (v: 'MERL' | 'EPFL') => void
  epochs: number
  setEpochs: (v: number) => void
  neuralDevice: 'cpu' | 'cuda'
  setNeuralDevice: (v: 'cpu' | 'cuda') => void
  cudaDevice: string
  setCudaDevice: (v: string) => void
  condaEnv: string
  setCondaEnv: (v: string) => void
  neuralOutputDir: string
  setNeuralOutputDir: (v: string) => void
  kerasH5Dir: string
  setKerasH5Dir: (v: string) => void
  kerasNpyDir: string
  setKerasNpyDir: (v: string) => void
  trainOutputDir: string
  setTrainOutputDir: (v: string) => void
  extractOutputDir: string
  setExtractOutputDir: (v: string) => void
  ptDir: string
  setPtDir: (v: string) => void
  checkpointPath: string
  setCheckpointPath: (v: string) => void
  fullbinOutputDir: string
  setFullbinOutputDir: (v: string) => void
  sparseSamples: number
  setSparseSamples: (v: number) => void
  klWeight: number
  setKlWeight: (v: number) => void
  fwWeight: number
  setFwWeight: (v: number) => void
  lr: number
  setLr: (v: number) => void
  trainSubset: number
  setTrainSubset: (v: number) => void
  trainSeed: number
  setTrainSeed: (v: number) => void
  keepon: boolean
  setKeepon: (v: boolean) => void
  parameterValues: Record<string, unknown>
  setParameterValues: React.Dispatch<React.SetStateAction<Record<string, unknown>>>
  selectedMaterials: string[]
  setSelectedMaterials: (v: string[]) => void
  selectedH5Files: string[]
  setSelectedH5Files: (v: string[]) => void
  selectedPts: string[]
  setSelectedPts: (v: string[]) => void
  materialItems: FileListItem[]
  h5Items: FileListItem[]
  ptItems: FileListItem[]
  runs: TrainRunSummary[]
  materialsQueryError: Error | null
  h5FilesQueryError: Error | null
  ptFilesQueryError: Error | null
  runsQueryError: Error | null
  startTraining: () => void
  startH5Convert: () => void
  startExtract: () => void
  startDecode: () => void
  applyRun: (run: TrainRunSummary) => void
}

export function TrainTab(props: TrainTabProps) {
  const {
    activeModel,
    merlDir, setMerlDir,
    dataset, setDataset,
    epochs, setEpochs,
    neuralDevice, setNeuralDevice,
    cudaDevice, setCudaDevice,
    condaEnv, setCondaEnv,
    neuralOutputDir, setNeuralOutputDir,
    kerasH5Dir, setKerasH5Dir,
    kerasNpyDir, setKerasNpyDir,
    trainOutputDir, setTrainOutputDir,
    extractOutputDir, setExtractOutputDir,
    ptDir, setPtDir,
    checkpointPath, setCheckpointPath,
    fullbinOutputDir, setFullbinOutputDir,
    sparseSamples, setSparseSamples,
    klWeight, setKlWeight,
    fwWeight, setFwWeight,
    lr, setLr,
    trainSubset, setTrainSubset,
    trainSeed, setTrainSeed,
    keepon, setKeepon,
    parameterValues, setParameterValues,
    selectedMaterials, setSelectedMaterials,
    selectedH5Files, setSelectedH5Files,
    selectedPts, setSelectedPts,
    materialItems, h5Items, ptItems,
    runs,
    materialsQueryError, h5FilesQueryError, ptFilesQueryError, runsQueryError,
    startTraining, startH5Convert, startExtract, startDecode, applyRun,
  } = props

  return (
    <>
      {/* Keras intermediate format conversion */}
      {activeModel?.adapter === 'neural-keras' ? (
        <section className="models-section">
          <div className="detail-board__lead">
            <h3>Keras 中间格式转换</h3>
          </div>
          <div className="render-form-grid">
            <Field label="Keras 权重目录">
              <input value={kerasH5Dir} onChange={(event) => setKerasH5Dir(event.target.value)} />
            </Field>
            <Field label="NPY 输出目录">
              <input value={kerasNpyDir} onChange={(event) => setKerasNpyDir(event.target.value)} />
            </Field>
            <Field label="Conda 环境">
              <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
            </Field>
          </div>
          <div className="render-form-grid" style={{ marginTop: '16px' }}>
            <Field label="Keras 权重文件">
              <MaterialSelector
                title="选择 Keras 权重文件"
                items={h5Items}
                selectedItems={selectedH5Files}
                onSelectionChange={setSelectedH5Files}
                error={h5FilesQueryError}
                emptyMessage="请先完成 Keras 训练，或检查权重目录是否正确。"
                searchPlaceholder="搜索 .h5 文件"
                formatName={(name) => name.replace(/\.h5$/i, '')}
              />
            </Field>
          </div>
          <div className="render-actions">
            <Button type="button" variant="primary" onClick={() => void startH5Convert()} disabled={selectedH5Files.length === 0}>
              执行 Keras→NPY 转换
            </Button>
          </div>
        </section>
      ) : null}

      <section className="models-section">
        <div className="detail-board__lead">
          <h3>MERL 材质库</h3>
        </div>
        <div className="render-form-grid" style={{ marginTop: '16px' }}>
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
      </section>

      <section className="models-section">
        <div className="detail-board__lead">
          <h3>训练入口</h3>
        </div>
        <div className="render-form-grid">
          <Field label="材质目录">
            <input value={merlDir} onChange={(event) => setMerlDir(event.target.value)} />
          </Field>
          <Field label="数据集">
            <select value={dataset} onChange={(event) => setDataset(event.target.value as 'MERL' | 'EPFL')} disabled={activeModel?.category === 'neural'}>
              <option value="MERL">MERL</option>
              <option value="EPFL">EPFL</option>
            </select>
          </Field>
          <Field label="Epochs">
            <input type="number" value={epochs} onChange={(event) => setEpochs(Number(event.target.value) || 1)} />
          </Field>
          <Field label={activeModel?.category === 'neural' && activeModel?.adapter === 'neural-pytorch' ? '训练设备' : 'Conda 环境'}>
            {activeModel?.adapter === 'neural-pytorch' ? (
              <select value={neuralDevice} onChange={(event) => setNeuralDevice(event.target.value as 'cpu' | 'cuda')}>
                <option value="cpu">cpu</option>
                <option value="cuda">cuda</option>
              </select>
            ) : (
              <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
            )}
          </Field>
        </div>
        {activeModel?.adapter === 'neural-pytorch' ? (
          <div className="render-form-grid">
            <Field label="NPY 输出目录">
              <input value={neuralOutputDir} onChange={(event) => setNeuralOutputDir(event.target.value)} />
            </Field>
          </div>
        ) : null}
        {activeModel?.adapter === 'neural-keras' ? (
          <div className="render-form-grid">
            <Field label="CUDA 设备">
              <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
            </Field>
            <Field label="H5 输出目录">
              <input value={kerasH5Dir} onChange={(event) => setKerasH5Dir(event.target.value)} />
            </Field>
            <Field label="NPY 输出目录">
              <input value={kerasNpyDir} onChange={(event) => setKerasNpyDir(event.target.value)} />
            </Field>
          </div>
        ) : null}
        {/* Custom model parameters */}
        {activeModel?.adapter === 'custom-cli' && activeModel.parameters && activeModel.parameters.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <ModelParameterForm
              parameters={activeModel.parameters}
              values={parameterValues}
              onChange={(key, value) => setParameterValues((prev) => ({ ...prev, [key]: value }))}
            />
          </div>
        )}
        {activeModel?.adapter === 'hyper-family' ? (
          <>
            <div className="render-form-grid">
              <Field label="训练结果目录">
                <input value={trainOutputDir} onChange={(event) => setTrainOutputDir(event.target.value)} />
              </Field>
              <Field label="稀疏采样点数">
                <input type="number" value={sparseSamples} onChange={(event) => setSparseSamples(Number(event.target.value) || 1)} />
              </Field>
              <Field label="KL 权重">
                <input type="number" step="0.01" value={klWeight} onChange={(event) => setKlWeight(Number(event.target.value) || 0)} />
              </Field>
              <Field label="FW 权重">
                <input type="number" step="0.01" value={fwWeight} onChange={(event) => setFwWeight(Number(event.target.value) || 0)} />
              </Field>
              <Field label="学习率">
                <input type="number" step="0.00001" value={lr} onChange={(event) => setLr(Number(event.target.value) || 0.00001)} />
              </Field>
              <Field label="训练材质数">
                <input type="number" value={trainSubset} onChange={(event) => setTrainSubset(Number(event.target.value) || 0)} />
              </Field>
            </div>
            <div className="render-toggle-row" style={{ marginTop: '8px' }}>
              <CheckboxField label="继续训练" checked={keepon} onChange={(event) => setKeepon(event.target.checked)} />
            </div>
            <div className="render-actions" style={{ marginTop: '12px' }}>
              <Button
                type="button"
                variant="primary"
                onClick={() => void startTraining()}
                disabled={!activeModel || (activeModel.category === 'neural' && selectedMaterials.length === 0)}
              >
                启动训练
              </Button>
            </div>
          </>
        ) : (
          <div className="render-actions" style={{ marginTop: '12px' }}>
            <Button
              type="button"
              variant="primary"
              onClick={() => void startTraining()}
              disabled={!activeModel || (activeModel.category === 'neural' && selectedMaterials.length === 0)}
            >
              启动训练
            </Button>
          </div>
        )}
      </section>

      <section className="models-section">
        <div className="detail-board__lead">
          <h3>运行记录</h3>
        </div>
        <div className="runs-list">
          {!activeModel?.supports_runs ? (
            <FeedbackPanel title="当前模型无运行记录" message="该模型未启用 supports_runs，因此不会显示其它模型的训练记录。" tone="empty" compact />
          ) : null}
          {runsQueryError instanceof Error ? (
            <FeedbackPanel title="运行记录读取失败" message={runsQueryError.message} tone="error" compact />
          ) : null}
          {runs.map((run) => (
            <article key={`${run.model_key}-${run.run_dir}`} className="run-card">
              <strong>{run.label}</strong>
              <span>{run.run_name}</span>
              <span>{run.dataset} / 已训练 {run.completed_epochs} epochs</span>
              <div className="render-actions">
                <Button type="button" onClick={() => applyRun(run)} disabled={!run.has_checkpoint}>
                  应用 Checkpoint
                </Button>
              </div>
            </article>
          ))}
          {!runsQueryError && activeModel?.supports_runs && runs.length === 0 ? (
            <FeedbackPanel title="当前没有运行记录" message="该模型尚未产出可扫描的结果目录，或未启用 supports_runs。" tone="empty" compact />
          ) : null}
        </div>
      </section>

      {/* Hyper-family extract/decode sections only in train tab */}
      {activeModel?.adapter === 'hyper-family' ? (
        <>
          {activeModel.supports_extract ? (
            <section className="models-section">
              <div className="detail-board__lead">
                <h3>参数提取</h3>
              </div>
              <div className="render-form-grid">
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
                <Field label="随机种子">
                  <input type="number" value={trainSeed} onChange={(event) => setTrainSeed(Number(event.target.value) || 0)} />
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
          ) : null}
          {activeModel.supports_decode ? (
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
                <Field label="CUDA 设备">
                  <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
                </Field>
              </div>
              <div className="render-form-grid" style={{ marginTop: '16px' }}>
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
          ) : null}
        </>
      ) : null}
    </>
  )
}
