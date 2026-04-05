import { useEffect, useMemo, useState } from 'react'

import type { FileListItem, ModuleKey } from '../types/api'

type WorkspaceCanvasProps = {
  activeModule: ModuleKey
  galleryItems: FileListItem[]
}

type ActionSpec = {
  key: string
  label: string
  detail: string
  settings: string[]
  note: string
}

type ModuleMeta = {
  title: string
  description: string
  accent: string
  workflow: Array<{ title: string; detail: string }>
  surfaces: Array<{ label: string; value: string }>
  actions: ActionSpec[]
}

const moduleMeta: Record<ModuleKey, ModuleMeta> = {
  render: {
    title: '渲染可视化工作台',
    description: 'V2 首个主线模块。这里会承接场景、材质、采样和输出转换，并把当前同步渲染流程替换成后端任务驱动。',
    accent: 'Render / Scene / Output',
    workflow: [
      { title: 'Scene Setup', detail: '选择 XML 场景与输入来源，锁定材质集合。' },
      { title: 'Task Dispatch', detail: '把渲染参数包装成后台任务，推送日志和状态。' },
      { title: 'Output Review', detail: '自动刷新 PNG 画廊，并保留 EXR 转换入口。' },
    ],
    surfaces: [
      { label: '输入类型', value: 'brdfs / fullbin / npy' },
      { label: '主画布', value: 'Gallery + Compare + Logs' },
      { label: '右侧上下文', value: 'Task status / Runtime detail' },
    ],
    actions: [
      {
        key: 'scene',
        label: '场景与输入配置',
        detail: '先确定 XML 场景、输入目录与单材质/批量模式，这是后续真正对接渲染 API 的第一块表单。',
        settings: ['Scene XML selector', 'Input mode switch', 'Selected file list', 'Skip existing / auto convert'],
        note: '下一阶段会把这个按钮接到 `GET /render/scenes` 与 `POST /render/batch`。',
      },
      {
        key: 'quality',
        label: '采样与渲染参数',
        detail: '集中设置 integrator、sample count、输出目录和自定义命令，保持实验过程可复现。',
        settings: ['Integrator type', 'Sample count', 'Output routing', 'Custom render command'],
        note: '这里会成为渲染参数的主编辑器，而不是分散在很多 Streamlit 小控件里。',
      },
      {
        key: 'review',
        label: '输出转换与结果查看',
        detail: '渲染完成后在同一工作区查看输出、转换 EXR 到 PNG，并进入后续分析流程。',
        settings: ['EXR -> PNG convert', 'Recent output gallery', 'Task log snapshot', 'Open in analysis'],
        note: '目标是让“渲染完成后下一步做什么”在 UI 上一眼可见。',
      },
    ],
  },
  analysis: {
    title: '材质表达结果分析',
    description: '这一页将承接现有预览、量化评估、网格拼图和对比拼图能力，改造成更适合实验流程的分析界面。',
    accent: 'Metrics / Compare / Report',
    workflow: [
      { title: 'Reference Selection', detail: '选择 GT、Fullbin、NPY 或 checkpoint 输出。' },
      { title: 'Metric Evaluate', detail: '触发量化评估，输出误差和核心指标。' },
      { title: 'Comparison Publish', detail: '生成对照滑块、拼图和汇总报告。' },
    ],
    surfaces: [
      { label: '输入对象', value: 'GT / Fullbin / NPY / Render outputs' },
      { label: '分析方式', value: 'Evaluate / Grid / Compare' },
      { label: '结果呈现', value: 'Metric board / Slider / Montage' },
    ],
    actions: [
      {
        key: 'metrics',
        label: '表达结果对比',
        detail: '围绕同一材质的多种表达结果建立对照集合，统一入口管理比较对象和度量方式。',
        settings: ['Reference set', 'Compared outputs', 'Error metric selection', 'Batch evaluation'],
        note: '后续会直接接 `POST /analysis/evaluate`。',
      },
      {
        key: 'slider',
        label: '图像滑块与细节检视',
        detail: '把对照滑块作为主体验之一，让你在分析页而不是渲染页里做细节确认。',
        settings: ['Before / after pair', 'Region zoom', 'Linked cursor', 'Channel emphasis'],
        note: '这部分适合放在主画布中部，右侧保留指标和说明。',
      },
      {
        key: 'report',
        label: '拼图与报告生成',
        detail: '把多图拼接和报告导出作为统一动作，而不是分散在多个临时脚本入口。',
        settings: ['Grid montage', 'Comparison board', 'Summary annotation', 'Export snapshot'],
        note: '这里会成为分析结果的最终整理区。',
      },
    ],
  },
  models: {
    title: '网络模型管理',
    description: '模型管理不是简单列表页，而是训练入口、运行记录、checkpoint 和导出动作的统一控制台。',
    accent: 'Train / Run / Export',
    workflow: [
      { title: 'Preset Build', detail: '建立训练任务预设与参数模板。' },
      { title: 'Run Tracking', detail: '查看训练状态、loss 曲线与运行记录。' },
      { title: 'Artifact Export', detail: '抽取参数并输出 checkpoint、pt 或 fullbin。' },
    ],
    surfaces: [
      { label: '模型类型', value: 'Neural / Hyper / Decoupled' },
      { label: '主操作', value: 'Train / Extract / Decode' },
      { label: '资产区', value: 'Runs / Checkpoints / Exports' },
    ],
    actions: [
      {
        key: 'preset',
        label: '新建训练方案',
        detail: '把模型类型切换、数据源和训练参数组织成真正的计划面板，而不是多个散乱 tab。',
        settings: ['Model family', 'Dataset routing', 'Training hyper-params', 'Launch command'],
        note: '这里会接到 `/train/*` 系列接口。',
      },
      {
        key: 'runs',
        label: '运行记录与 checkpoint',
        detail: '集中查看最近训练、失败任务和关键 checkpoint，减少来回切目录的成本。',
        settings: ['Run list', 'Latest checkpoints', 'Failure note', 'Resume action'],
        note: '右侧上下文面板可以长期保留运行状态和日志摘要。',
      },
      {
        key: 'export',
        label: '参数提取与导出',
        detail: '把 `.pt -> .fullbin`、hyper 参数抽取等后处理操作纳入统一的资产出口。',
        settings: ['Extract weights', 'Decode material', 'Export fullbin', 'Output verification'],
        note: '这部分决定模型管理页是否真正可用于实验闭环。',
      },
    ],
  },
}

function formatOutputMeta(item: FileListItem) {
  const modifiedAt = new Date(item.modified_at)
  const label = Number.isNaN(modifiedAt.getTime())
    ? '更新时间未知'
    : modifiedAt.toLocaleString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })

  return `${Math.max(1, Math.round(item.size / 1024))} KB · ${label}`
}

export function WorkspaceCanvas({ activeModule, galleryItems }: WorkspaceCanvasProps) {
  const meta = moduleMeta[activeModule]
  const [selectedAction, setSelectedAction] = useState<string>(meta.actions[0].key)

  useEffect(() => {
    setSelectedAction(moduleMeta[activeModule].actions[0].key)
  }, [activeModule])

  const activeAction = useMemo(
    () => meta.actions.find((action) => action.key === selectedAction) ?? meta.actions[0],
    [meta.actions, selectedAction],
  )
  const previewItems = galleryItems.slice(0, 3)

  return (
    <section className="workspace-canvas">
      <div className="workspace-hero">
        <div>
          <span className="eyebrow">{meta.accent}</span>
          <h2>{meta.title}</h2>
          <p>{meta.description}</p>
        </div>
        <div className="workspace-hero__aside">
          <span>当前交互</span>
          <strong>先以按钮入口表达模块结构，再逐步接入真实 API 与任务流。</strong>
        </div>
      </div>

      <div className="action-grid">
        {meta.actions.map((action) => (
          <button
            key={action.key}
            type="button"
            className={action.key === activeAction.key ? 'action-tile action-tile--active' : 'action-tile'}
            onClick={() => setSelectedAction(action.key)}
          >
            <span className="action-tile__label">{action.label}</span>
            <span className="action-tile__detail">{action.detail}</span>
          </button>
        ))}
      </div>

      <div className="detail-board">
        <div className="detail-board__lead">
          <h3>{activeAction.label}</h3>
          <p>{activeAction.detail}</p>
        </div>
        <div className="detail-pill-grid">
          {activeAction.settings.map((setting) => (
            <span key={setting} className="detail-pill">
              {setting}
            </span>
          ))}
        </div>
        <p className="detail-note">{activeAction.note}</p>
      </div>

      <div className="pipeline-grid">
        {meta.workflow.map((step) => (
          <article key={step.title} className="pipeline-card">
            <span className="pipeline-card__index">{step.title}</span>
            <p>{step.detail}</p>
          </article>
        ))}
      </div>

      <div className="surface-grid">
        {meta.surfaces.map((surface) => (
          <article key={surface.label} className="surface-card">
            <span className="surface-card__label">{surface.label}</span>
            <strong className="surface-card__value">{surface.value}</strong>
          </article>
        ))}
      </div>

      <div className="mini-output-list">
        {previewItems.length > 0 ? (
          previewItems.map((item) => (
            <article key={item.path} className="mini-output">
              <div className="gallery-item__thumb" />
              <div>
                <strong>{item.name}</strong>
                <span className="mini-output__meta">{formatOutputMeta(item)}</span>
              </div>
            </article>
          ))
        ) : (
          <article className="mini-output mini-output--empty">
            <div className="gallery-item__thumb" />
            <div>
              <strong>等待真实输出进入画廊</strong>
              <span className="mini-output__meta">后续接入渲染任务后，这里会同步展示最近结果。</span>
            </div>
          </article>
        )}
      </div>
    </section>
  )
}
