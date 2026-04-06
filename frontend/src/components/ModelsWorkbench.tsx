import { useEffect, useMemo, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { BACKEND_ORIGIN } from '../lib/api'
import type {
  NeuralTrainEngine,
  TaskEvent,
  TrainProjectVariant,
  TrainRunSummary,
} from '../types/api'
import { FeedbackPanel } from './FeedbackPanel'
import {
  useExtractedPtFiles,
  useMaterialsDirectory,
  useStartHyperDecode,
  useStartHyperExtract,
  useStartHyperRun,
  useStartNeuralKeras,
  useStartNeuralPytorch,
  useStopTrainTask,
  useTrainModels,
  useTrainRuns,
  useTrainTaskDetail,
} from '../features/models/useModelsWorkbench'


const TEST_SET_20 = [
  'alum-bronze',
  'beige-fabric',
  'black-obsidian',
  'blue-acrylic',
  'chrome',
  'chrome-steel',
  'dark-red-paint',
  'dark-specular-fabric',
  'delrin',
  'green-metallic-paint',
  'natural-209',
  'nylon',
  'polyethylene',
  'pure-rubber',
  'silicon-nitrade',
  'teflon',
  'violet-rubber',
  'white-diffuse-bball',
  'white-fabric',
  'yellow-paint',
]

type WorkbenchMode = 'neural' | TrainProjectVariant

function normalizeBinaryName(name: string) {
  return name.replace(/\.binary$/i, '')
}

function getDefaultPath(
  models: ReturnType<typeof useTrainModels>['data'],
  key: string,
  field: string,
  fallback: string,
) {
  return models?.items.find((item) => item.key === key)?.default_paths[field] ?? fallback
}

export function ModelsWorkbench() {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<WorkbenchMode>('hyperbrdf')
  const [neuralEngine, setNeuralEngine] = useState<NeuralTrainEngine>('pytorch')
  const [search, setSearch] = useState('')
  const [ptSearch, setPtSearch] = useState('')
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([])
  const [selectedPts, setSelectedPts] = useState<string[]>([])
  const [dataset, setDataset] = useState<'MERL' | 'EPFL'>('MERL')
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<string[]>([])

  const modelQuery = useTrainModels()
  const materialsQuery = useMaterialsDirectory(search)
  const runsQuery = useTrainRuns(mode === 'neural' ? null : mode)
  const ptFilesQuery = useExtractedPtFiles(mode === 'neural' ? 'hyperbrdf' : mode, ptSearch)
  const taskDetailQuery = useTrainTaskDetail(activeTaskId)

  const startNeuralPytorch = useStartNeuralPytorch()
  const startNeuralKeras = useStartNeuralKeras()
  const startHyperRun = useStartHyperRun()
  const startHyperExtract = useStartHyperExtract()
  const startHyperDecode = useStartHyperDecode()
  const stopTrainTask = useStopTrainTask()

  const [merlDir, setMerlDir] = useState('')
  const [neuralOutputDir, setNeuralOutputDir] = useState('')
  const [kerasH5Dir, setKerasH5Dir] = useState('')
  const [kerasNpyDir, setKerasNpyDir] = useState('')
  const [neuralDevice, setNeuralDevice] = useState<'cpu' | 'cuda'>('cpu')
  const [cudaDevice, setCudaDevice] = useState('0')
  const [condaEnv, setCondaEnv] = useState('')
  const [checkpointPath, setCheckpointPath] = useState('')
  const [trainOutputDir, setTrainOutputDir] = useState('')
  const [extractOutputDir, setExtractOutputDir] = useState('')
  const [ptDir, setPtDir] = useState('')
  const [fullbinOutputDir, setFullbinOutputDir] = useState('data/inputs/fullbin')
  const [teacherDir, setTeacherDir] = useState('')
  const [baselineCheckpoint, setBaselineCheckpoint] = useState('')
  const [epochs, setEpochs] = useState(100)
  const [sparseSamples, setSparseSamples] = useState(4000)
  const [klWeight, setKlWeight] = useState(0.1)
  const [fwWeight, setFwWeight] = useState(0.1)
  const [lr, setLr] = useState(0.00005)
  const [trainSubset, setTrainSubset] = useState(80)
  const [trainSeed, setTrainSeed] = useState(42)
  const [keepon, setKeepon] = useState(false)
  const [modelType, setModelType] = useState<'baseline' | 'decoupled'>('decoupled')
  const [samplingMode, setSamplingMode] = useState<'random' | 'hybrid'>('hybrid')
  const [analyticLobes, setAnalyticLobes] = useState<1 | 2>(1)
  const [analyticLossWeight, setAnalyticLossWeight] = useState(0.1)
  const [residualLossWeight, setResidualLossWeight] = useState(0.1)
  const [specLossWeight, setSpecLossWeight] = useState(0.2)
  const [gateRegWeight, setGateRegWeight] = useState(0.05)
  const [specPercentile, setSpecPercentile] = useState(0.9)
  const [gateBiasInit, setGateBiasInit] = useState(-2)
  const [stageAEpochs, setStageAEpochs] = useState(10)
  const [stageBRampEpochs, setStageBRampEpochs] = useState(20)

  const materialItems = materialsQuery.data?.items ?? []
  const ptItems = ptFilesQuery.data?.items ?? []
  const taskDetail = taskDetailQuery.data
  const taskRecord = taskDetail?.record

  useEffect(() => {
    if (!merlDir) {
      setMerlDir(getDefaultPath(modelQuery.data, 'neural-pytorch', 'materials_dir', 'data/inputs/binary'))
    }
    if (!neuralOutputDir) {
      setNeuralOutputDir(getDefaultPath(modelQuery.data, 'neural-pytorch', 'output_dir', 'data/inputs/npy'))
    }
    if (!kerasH5Dir) {
      setKerasH5Dir(getDefaultPath(modelQuery.data, 'neural-keras', 'h5_output_dir', 'Neural-BRDF/data/merl_nbrdf'))
    }
    if (!kerasNpyDir) {
      setKerasNpyDir(getDefaultPath(modelQuery.data, 'neural-keras', 'npy_output_dir', 'data/inputs/npy'))
    }
  }, [kerasH5Dir, kerasNpyDir, merlDir, modelQuery.data, neuralOutputDir])

  useEffect(() => {
    if (mode === 'hyperbrdf') {
      setTrainOutputDir(getDefaultPath(modelQuery.data, 'hyperbrdf', 'results_dir', 'HyperBRDF/results'))
      setExtractOutputDir(getDefaultPath(modelQuery.data, 'hyperbrdf', 'extract_dir', 'HyperBRDF/results/extracted_pts'))
      setPtDir(getDefaultPath(modelQuery.data, 'hyperbrdf', 'extract_dir', 'HyperBRDF/results/extracted_pts'))
      setCheckpointPath(getDefaultPath(modelQuery.data, 'hyperbrdf', 'checkpoint', 'HyperBRDF/results/test/MERL/checkpoint.pt'))
      setCondaEnv('hyperbrdf')
    }
    if (mode === 'decoupled') {
      setTrainOutputDir(getDefaultPath(modelQuery.data, 'decoupled', 'results_dir', 'DecoupledHyperBRDF/results'))
      setExtractOutputDir(getDefaultPath(modelQuery.data, 'decoupled', 'extract_dir', 'DecoupledHyperBRDF/results/extracted_pts'))
      setPtDir(getDefaultPath(modelQuery.data, 'decoupled', 'extract_dir', 'DecoupledHyperBRDF/results/extracted_pts'))
      setCheckpointPath(getDefaultPath(modelQuery.data, 'decoupled', 'checkpoint', 'DecoupledHyperBRDF/results/test/MERL/checkpoint.pt'))
      setTeacherDir('DecoupledHyperBRDF/data/analytic_teacher')
      setBaselineCheckpoint('')
      setCondaEnv('decoupledhyperbrdf')
    }
  }, [mode, modelQuery.data])

  useEffect(() => {
    const available = new Set(materialItems.map((item) => item.name))
    setSelectedMaterials((current) => current.filter((name) => available.has(name)))
  }, [materialItems])

  useEffect(() => {
    const available = new Set(ptItems.map((item) => item.name))
    setSelectedPts((current) => current.filter((name) => available.has(name)))
  }, [ptItems])

  useEffect(() => {
    if (!taskDetail) {
      return
    }
    setLiveLogs(taskDetail.logs.slice(-160))
  }, [taskDetail?.record.task_id, taskDetail?.logs])

  useEffect(() => {
    if (!activeTaskId) {
      return
    }
    const wsProtocol = BACKEND_ORIGIN.startsWith('https') ? 'wss' : 'ws'
    const socket = new WebSocket(`${wsProtocol}://${new URL(BACKEND_ORIGIN).host}/ws/tasks/${activeTaskId}`)

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as TaskEvent
      if (payload.message) {
        setLiveLogs((current) => {
          if (current[current.length - 1] === payload.message) {
            return current
          }
          return [...current, payload.message].slice(-160)
        })
      }
      queryClient.invalidateQueries({ queryKey: ['train-task-detail', activeTaskId] })
      queryClient.invalidateQueries({ queryKey: ['train-runs'] })
      queryClient.invalidateQueries({ queryKey: ['train-extracted-pts'] })
    }

    return () => {
      socket.close()
    }
  }, [activeTaskId, queryClient])

  const summaryChips = useMemo(
    () => [
      `模式: ${mode === 'neural' ? `Neural-BRDF / ${neuralEngine}` : mode === 'hyperbrdf' ? 'HyperBRDF' : 'DecoupledHyperBRDF'}`,
      `材质数: ${materialItems.length}`,
      `已选材质: ${selectedMaterials.length}`,
      `运行记录: ${runsQuery.data?.total ?? 0}`,
      `PT 文件: ${ptItems.length}`,
    ],
    [materialItems.length, mode, neuralEngine, ptItems.length, runsQuery.data?.total, selectedMaterials.length],
  )

  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const currentStatus = taskRecord?.status ?? 'idle'
  const progressValue = taskRecord?.progress ?? 0
  const taskError =
    startNeuralPytorch.error ??
    startNeuralKeras.error ??
    startHyperRun.error ??
    startHyperExtract.error ??
    startHyperDecode.error ??
    stopTrainTask.error
  const taskStateMessage =
    taskRecord?.status === 'failed'
      ? taskRecord.message || '训练任务执行失败，请检查环境、路径和日志输出。'
      : taskRecord?.status === 'cancelled'
        ? taskRecord.message || '训练任务已取消。'
        : null

  const toggleMaterial = (name: string, event?: React.MouseEvent) => {
    setSelectedMaterials((current) => {
      const currentIndex = materialItems.findIndex(f => f.name === name);
      if (event?.shiftKey && current.length > 0 && currentIndex !== -1) {
        const lastSelectedName = current[current.length - 1];
        const lastSelectedIndex = materialItems.findIndex(f => f.name === lastSelectedName);
        if (lastSelectedIndex !== -1) {
          const start = Math.min(lastSelectedIndex, currentIndex);
          const end = Math.max(lastSelectedIndex, currentIndex);
          const namesToSelect = materialItems.slice(start, end + 1).map(f => f.name);
          const newSelection = [...current];
          for (const n of namesToSelect) {
            if (!newSelection.includes(n)) {
              newSelection.push(n);
            }
          }
          return newSelection;
        }
      }
      return current.includes(name) ? current.filter((item) => item !== name) : [...current, name];
    })
  }

  const togglePt = (name: string, event?: React.MouseEvent) => {
    setSelectedPts((current) => {
      const currentIndex = ptItems.findIndex(f => f.name === name);
      if (event?.shiftKey && current.length > 0 && currentIndex !== -1) {
        const lastSelectedName = current[current.length - 1];
        const lastSelectedIndex = ptItems.findIndex(f => f.name === lastSelectedName);
        if (lastSelectedIndex !== -1) {
          const start = Math.min(lastSelectedIndex, currentIndex);
          const end = Math.max(lastSelectedIndex, currentIndex);
          const namesToSelect = ptItems.slice(start, end + 1).map(f => f.name);
          const newSelection = [...current];
          for (const n of namesToSelect) {
            if (!newSelection.includes(n)) {
              newSelection.push(n);
            }
          }
          return newSelection;
        }
      }
      return current.includes(name) ? current.filter((item) => item !== name) : [...current, name];
    })
  }

  const applyPreset = () => {
    const selected = materialItems
      .filter((item) => TEST_SET_20.includes(normalizeBinaryName(item.name)))
      .map((item) => item.name)
    setSelectedMaterials(selected)
  }

  const applyRun = (run: TrainRunSummary) => {
    setMode(run.project_variant)
    setCheckpointPath(run.checkpoint_path)
    setDataset(run.dataset === 'EPFL' ? 'EPFL' : 'MERL')
  }

  const startTraining = async () => {
    setLiveLogs([])
    if (mode === 'neural') {
      if (neuralEngine === 'pytorch') {
        const response = await startNeuralPytorch.mutateAsync({
          merl_dir: merlDir,
          selected_materials: selectedMaterials,
          epochs,
          output_dir: neuralOutputDir,
          device: neuralDevice,
        })
        setActiveTaskId(response.task_id)
        return
      }
      const response = await startNeuralKeras.mutateAsync({
        merl_dir: merlDir,
        selected_materials: selectedMaterials,
        cuda_device: cudaDevice,
        h5_output_dir: kerasH5Dir,
        npy_output_dir: kerasNpyDir,
      })
      setActiveTaskId(response.task_id)
      return
    }

    const response = await startHyperRun.mutateAsync({
      project_variant: mode,
      merl_dir: merlDir,
      output_dir: trainOutputDir,
      conda_env: condaEnv,
      dataset,
      epochs,
      sparse_samples: sparseSamples,
      kl_weight: klWeight,
      fw_weight: fwWeight,
      lr,
      keepon,
      train_subset: trainSubset,
      train_seed: trainSeed,
      model_type: modelType,
      sampling_mode: samplingMode,
      teacher_dir: teacherDir,
      analytic_lobes: analyticLobes,
      baseline_checkpoint: baselineCheckpoint.trim(),
      analytic_loss_weight: analyticLossWeight,
      residual_loss_weight: residualLossWeight,
      spec_loss_weight: specLossWeight,
      gate_reg_weight: gateRegWeight,
      spec_percentile: specPercentile,
      gate_bias_init: gateBiasInit,
      stage_a_epochs: stageAEpochs,
      stage_b_ramp_epochs: stageBRampEpochs,
    })
    setActiveTaskId(response.task_id)
  }

  const startExtract = async () => {
    if (mode === 'neural') {
      return
    }
    setLiveLogs([])
    const response = await startHyperExtract.mutateAsync({
      project_variant: mode,
      merl_dir: merlDir,
      selected_materials: selectedMaterials,
      model_path: checkpointPath,
      output_dir: extractOutputDir,
      conda_env: condaEnv,
      dataset,
      sparse_samples: sparseSamples,
    })
    setActiveTaskId(response.task_id)
  }

  const startDecode = async () => {
    if (mode === 'neural') {
      return
    }
    setLiveLogs([])
    const response = await startHyperDecode.mutateAsync({
      project_variant: mode,
      pt_dir: ptDir,
      selected_pts: selectedPts,
      output_dir: fullbinOutputDir,
      conda_env: condaEnv,
      dataset,
      cuda_device: cudaDevice,
    })
    setActiveTaskId(response.task_id)
  }

  const stopTask = async () => {
    if (!activeTaskId) {
      return
    }
    await stopTrainTask.mutateAsync(activeTaskId)
    queryClient.invalidateQueries({ queryKey: ['train-task-detail', activeTaskId] })
  }

  return (
    <section className="workspace-canvas">
      <div className="workspace-hero">
        <div>
          <h2>网络模型管理</h2>
        </div>
      </div>

      <div className="detail-pill-grid">
        {summaryChips.map((chip) => (
          <span key={chip} className="detail-pill">
            {chip}
          </span>
        ))}
      </div>

      <div className="action-grid">
        <button type="button" className={mode === 'neural' ? 'action-tile action-tile--active' : 'action-tile'} onClick={() => setMode('neural')}>
          <span className="action-tile__label">Neural-BRDF</span>
        </button>
        <button
          type="button"
          className={mode === 'hyperbrdf' ? 'action-tile action-tile--active' : 'action-tile'}
          onClick={() => setMode('hyperbrdf')}
        >
          <span className="action-tile__label">HyperBRDF</span>
        </button>
        <button
          type="button"
          className={mode === 'decoupled' ? 'action-tile action-tile--active' : 'action-tile'}
          onClick={() => setMode('decoupled')}
        >
          <span className="action-tile__label">DecoupledHyperBRDF</span>
        </button>
      </div>

      <div className="models-layout">
        <section className="models-section">
          <div className="detail-board__lead">
            <h3>训练入口</h3>
          </div>

          {mode === 'neural' ? (
            <div className="render-toggle-row">
              <label className="toggle-field">
                <input type="radio" checked={neuralEngine === 'pytorch'} onChange={() => setNeuralEngine('pytorch')} />
                <span>PyTorch</span>
              </label>
              <label className="toggle-field">
                <input type="radio" checked={neuralEngine === 'keras'} onChange={() => setNeuralEngine('keras')} />
                <span>Keras + h5 to npy</span>
              </label>
            </div>
          ) : null}

          <div className="render-form-grid">
            <label className="field">
              <span>材质目录</span>
              <input value={merlDir} onChange={(event) => setMerlDir(event.target.value)} />
            </label>
            <label className="field">
              <span>数据集</span>
              <select value={dataset} onChange={(event) => setDataset(event.target.value as 'MERL' | 'EPFL')} disabled={mode === 'neural'}>
                <option value="MERL">MERL</option>
                <option value="EPFL">EPFL</option>
              </select>
            </label>
            <label className="field">
              <span>Epochs</span>
              <input type="number" value={epochs} onChange={(event) => setEpochs(Number(event.target.value) || 1)} />
            </label>
            <label className="field">
              <span>{mode === 'neural' ? '设备 / CUDA' : 'Conda 环境'}</span>
              {mode === 'neural' && neuralEngine === 'pytorch' ? (
                <select value={neuralDevice} onChange={(event) => setNeuralDevice(event.target.value as 'cpu' | 'cuda')}>
                  <option value="cpu">cpu</option>
                  <option value="cuda">cuda</option>
                </select>
              ) : mode === 'neural' ? (
                <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
              ) : (
                <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
              )}
            </label>
          </div>

          {mode === 'neural' ? (
            <div className="render-form-grid">
              {neuralEngine === 'pytorch' ? (
                <label className="field">
                  <span>输出目录</span>
                  <input value={neuralOutputDir} onChange={(event) => setNeuralOutputDir(event.target.value)} />
                </label>
              ) : (
                <>
                  <label className="field">
                    <span>H5 目录</span>
                    <input value={kerasH5Dir} onChange={(event) => setKerasH5Dir(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>NPY 目录</span>
                    <input value={kerasNpyDir} onChange={(event) => setKerasNpyDir(event.target.value)} />
                  </label>
                </>
              )}
            </div>
          ) : (
            <>
              <div className="render-form-grid">
                <label className="field">
                  <span>训练输出目录</span>
                  <input value={trainOutputDir} onChange={(event) => setTrainOutputDir(event.target.value)} />
                </label>
                <label className="field">
                  <span>稀疏采样点数</span>
                  <input type="number" value={sparseSamples} onChange={(event) => setSparseSamples(Number(event.target.value) || 1)} />
                </label>
                <label className="field">
                  <span>KL 权重</span>
                  <input type="number" step="0.01" value={klWeight} onChange={(event) => setKlWeight(Number(event.target.value) || 0)} />
                </label>
                <label className="field">
                  <span>FW 权重</span>
                  <input type="number" step="0.01" value={fwWeight} onChange={(event) => setFwWeight(Number(event.target.value) || 0)} />
                </label>
                <label className="field">
                  <span>学习率</span>
                  <input type="number" step="0.00001" value={lr} onChange={(event) => setLr(Number(event.target.value) || 0.00001)} />
                </label>
                <label className="field">
                  <span>训练材质数</span>
                  <input type="number" value={trainSubset} onChange={(event) => setTrainSubset(Number(event.target.value) || 0)} />
                </label>
              </div>
              <div className="render-toggle-row">
                <label className="toggle-field">
                  <input type="checkbox" checked={keepon} onChange={(event) => setKeepon(event.target.checked)} />
                  <span>继续训练</span>
                </label>
              </div>

              {mode === 'decoupled' ? (
                <div className="render-form-grid">
                  <label className="field">
                    <span>模型类型</span>
                    <select value={modelType} onChange={(event) => setModelType(event.target.value as 'baseline' | 'decoupled')}>
                      <option value="decoupled">decoupled</option>
                      <option value="baseline">baseline</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>采样策略</span>
                    <select value={samplingMode} onChange={(event) => setSamplingMode(event.target.value as 'random' | 'hybrid')}>
                      <option value="hybrid">hybrid</option>
                      <option value="random">random</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>教师缓存目录</span>
                    <input value={teacherDir} onChange={(event) => setTeacherDir(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>基线 Checkpoint</span>
                    <input value={baselineCheckpoint} onChange={(event) => setBaselineCheckpoint(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>解析 lobe 数</span>
                    <select value={analyticLobes} onChange={(event) => setAnalyticLobes(Number(event.target.value) as 1 | 2)}>
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>高光阈值</span>
                    <input type="number" step="0.01" value={specPercentile} onChange={(event) => setSpecPercentile(Number(event.target.value) || 0.9)} />
                  </label>
                  <label className="field">
                    <span>解析损失权重</span>
                    <input type="number" step="0.01" value={analyticLossWeight} onChange={(event) => setAnalyticLossWeight(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>残差损失权重</span>
                    <input type="number" step="0.01" value={residualLossWeight} onChange={(event) => setResidualLossWeight(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>高光损失权重</span>
                    <input type="number" step="0.01" value={specLossWeight} onChange={(event) => setSpecLossWeight(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>门控正则权重</span>
                    <input type="number" step="0.01" value={gateRegWeight} onChange={(event) => setGateRegWeight(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>门控 Bias 初值</span>
                    <input type="number" step="0.1" value={gateBiasInit} onChange={(event) => setGateBiasInit(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>阶段 A Epochs</span>
                    <input type="number" value={stageAEpochs} onChange={(event) => setStageAEpochs(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>阶段 B Ramp Epochs</span>
                    <input type="number" value={stageBRampEpochs} onChange={(event) => setStageBRampEpochs(Number(event.target.value) || 0)} />
                  </label>
                </div>
              ) : null}
            </>
          )}

          <div className="render-actions">
            <button
              type="button"
              className="theme-toggle"
              onClick={startTraining}
              disabled={mode === 'neural' && selectedMaterials.length === 0}
            >
              启动训练
            </button>
          </div>
        </section>

        <section className="models-section">
          <div className="detail-board__lead">
            <h3>材质选择</h3>
          </div>
          <div className="file-toolbar">
            <input
              type="search"
              className="search-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索 binary 材质"
            />
            <div className="file-toolbar__actions">
              <button type="button" className="theme-toggle" onClick={() => setSelectedMaterials(materialItems.map((item) => item.name))}>
                全选
              </button>
              <button type="button" className="theme-toggle" onClick={applyPreset}>
                预设20
              </button>
              <button type="button" className="theme-toggle" onClick={() => setSelectedMaterials([])}>
                清空
              </button>
            </div>
          </div>
          <div className="file-list">
            {materialsQuery.error instanceof Error ? (
              <FeedbackPanel
                title="材质目录读取失败"
                message={materialsQuery.error.message}
                tone="error"
                actionLabel="重新加载"
                onAction={() => {
                  void materialsQuery.refetch()
                }}
                compact
              />
            ) : null}
            {materialItems.map((item) => (
              <label key={item.path} className="file-item" onClick={(e) => {
                e.preventDefault();
                toggleMaterial(item.name, e);
              }}>
                <input type="checkbox" checked={selectedMaterials.includes(item.name)} readOnly />
                <span>{item.name}</span>
              </label>
            ))}
            {!materialsQuery.error && materialItems.length === 0 ? (
              <FeedbackPanel title="当前没有可训练材质" message="请检查 `data/inputs/binary` 下是否已有 `.binary` 文件。" tone="empty" compact />
            ) : null}
          </div>
        </section>

        <section className="models-section">
          <div className="detail-board__lead">
            <h3>运行记录</h3>
          </div>
          <div className="runs-list">
            {runsQuery.error instanceof Error ? (
              <FeedbackPanel
                title="运行记录读取失败"
                message={runsQuery.error.message}
                tone="error"
                actionLabel="重新加载"
                onAction={() => {
                  void runsQuery.refetch()
                }}
                compact
              />
            ) : null}
            {(runsQuery.data?.items ?? []).map((run) => (
              <article key={`${run.project_variant}-${run.run_dir}`} className="run-card">
                <strong>{run.label}</strong>
                <span>{run.run_name}</span>
                <span>{run.dataset} / 已训练 {run.completed_epochs} epochs</span>
                <button type="button" className="theme-toggle" onClick={() => applyRun(run)} disabled={!run.has_checkpoint}>
                  应用 Checkpoint
                </button>
              </article>
            ))}
            {!runsQuery.error && (runsQuery.data?.items ?? []).length === 0 ? (
              <FeedbackPanel title="当前没有运行记录" message="启动一次训练后，这里会显示 checkpoint 和 run 信息。" tone="empty" compact />
            ) : null}
          </div>
        </section>

        {mode !== 'neural' ? (
          <>
            <section className="models-section">
              <div className="detail-board__lead">
                <h3>参数提取</h3>
              </div>
              <div className="render-form-grid">
                <label className="field">
                  <span>Checkpoint</span>
                  <input value={checkpointPath} onChange={(event) => setCheckpointPath(event.target.value)} />
                </label>
                <label className="field">
                  <span>输出 PT 目录</span>
                  <input
                    value={extractOutputDir}
                    onChange={(event) => {
                      setExtractOutputDir(event.target.value)
                      setPtDir(event.target.value)
                    }}
                  />
                </label>
                <label className="field">
                  <span>随机种子</span>
                  <input type="number" value={trainSeed} onChange={(event) => setTrainSeed(Number(event.target.value) || 0)} />
                </label>
              </div>
              <div className="render-actions">
                <button
                  type="button"
                  className="theme-toggle"
                  onClick={startExtract}
                  disabled={dataset === 'MERL' && selectedMaterials.length === 0}
                >
                  启动参数提取
                </button>
              </div>
            </section>

            <section className="models-section">
              <div className="detail-board__lead">
                <h3>完整重建</h3>
              </div>
              <div className="render-form-grid">
                <label className="field">
                  <span>PT 目录</span>
                  <input value={ptDir} onChange={(event) => setPtDir(event.target.value)} />
                </label>
                <label className="field">
                  <span>FullBin 输出目录</span>
                  <input value={fullbinOutputDir} onChange={(event) => setFullbinOutputDir(event.target.value)} />
                </label>
                <label className="field">
                  <span>CUDA 设备</span>
                  <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
                </label>
              </div>
              <div className="file-toolbar">
                <input
                  type="search"
                  className="search-input"
                  value={ptSearch}
                  onChange={(event) => setPtSearch(event.target.value)}
                  placeholder="搜索已提取 pt 文件"
                />
                <div className="file-toolbar__actions">
                  <button type="button" className="theme-toggle" onClick={() => setSelectedPts(ptItems.map((item) => item.name))}>
                    全选
                  </button>
                  <button type="button" className="theme-toggle" onClick={() => setSelectedPts([])}>
                    清空
                  </button>
                </div>
              </div>
              <div className="file-list">
                {ptFilesQuery.error instanceof Error ? (
                  <FeedbackPanel
                    title="PT 列表读取失败"
                    message={ptFilesQuery.error.message}
                    tone="error"
                    actionLabel="重新加载"
                    onAction={() => {
                      void ptFilesQuery.refetch()
                    }}
                    compact
                  />
                ) : null}
                {ptItems.map((item) => (
                  <label key={item.path} className="file-item" onClick={(e) => {
                    e.preventDefault();
                    togglePt(item.name, e);
                  }}>
                    <input type="checkbox" checked={selectedPts.includes(item.name)} readOnly />
                    <span>{item.name}</span>
                  </label>
                ))}
                {!ptFilesQuery.error && ptItems.length === 0 ? (
                  <FeedbackPanel title="当前没有可解码的 PT 文件" message="请先完成参数提取，或确认输出目录中已有 `.pt` 文件。" tone="empty" compact />
                ) : null}
              </div>
              <div className="render-actions">
                <button type="button" className="theme-toggle" onClick={startDecode} disabled={selectedPts.length === 0}>
                  执行 fullbin 解码
                </button>
              </div>
            </section>
          </>
        ) : null}

        <section className="models-section models-section--wide">
          <div className="detail-board__lead">
            <h3>任务状态 / 日志</h3>
          </div>
          <div className="task-summary">
            <div className="settings-row">
              <span>Task ID</span>
              <strong>{activeTaskId ?? '-'}</strong>
            </div>
            <div className="settings-row">
              <span>Status</span>
              <strong>{currentStatus}</strong>
            </div>
            <div className="settings-row">
              <span>Progress</span>
              <strong>{progressValue}%</strong>
            </div>
          </div>
          <div className="progress-bar">
            <div className="progress-bar__fill" style={{ width: `${progressValue}%` }} />
          </div>
          {taskStateMessage ? (
            <FeedbackPanel
              title={taskRecord?.status === 'failed' ? '训练任务失败' : '训练任务已取消'}
              message={taskStateMessage}
              tone={taskRecord?.status === 'failed' ? 'error' : 'info'}
              compact
            />
          ) : null}
          <div className="render-actions">
            <button type="button" className="theme-toggle" onClick={stopTask} disabled={!activeTaskId}>
              停止任务
            </button>
          </div>
          <div className="log-panel">
            {logs.length > 0 ? (
              logs.map((line, index) => (
                <div key={`${index}-${line.slice(0, 16)}`} className="log-line">
                  {line}
                </div>
              ))
            ) : (
              <FeedbackPanel title="等待训练日志" message="启动训练、提取或解码后，这里会持续显示运行输出。" tone="empty" compact />
            )}
          </div>
          {taskError instanceof Error ? <FeedbackPanel title="操作提交失败" message={taskError.message} tone="error" compact /> : null}
        </section>
      </div>
    </section>
  )
}
