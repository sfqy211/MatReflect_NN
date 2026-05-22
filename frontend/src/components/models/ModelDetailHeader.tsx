import type { TrainModelItem, ModelEnvStatusResponse } from '../../types/api'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'

type ModelDetailHeaderProps = {
  model: TrainModelItem
  onBack: () => void
  showCommandsDoc: boolean
  onToggleCommandsDoc: () => void
  onSetupEnv: () => void
  setupEnvPending: boolean
  envStatus?: ModelEnvStatusResponse | null
}

export function ModelDetailHeader({
  model,
  onBack,
  showCommandsDoc,
  onToggleCommandsDoc,
  onSetupEnv,
  setupEnvPending,
  envStatus,
}: ModelDetailHeaderProps) {
  return (
    <div className="model-detail-header">
      <div className="model-detail-header__left">
        <button
          type="button"
          className="model-detail-header__back"
          onClick={onBack}
          title="返回模型列表"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <h2 className="model-detail-header__name">{model.label}</h2>
        <Badge variant="detail">{model.adapter}</Badge>
        <Badge variant="detail">{model.category}</Badge>
      </div>
      <div className="model-detail-header__right">
        {envStatus && !envStatus.env_exists && (
          <Button type="button" onClick={onSetupEnv} disabled={setupEnvPending} style={{ fontSize: '0.8rem' }}>
            {setupEnvPending ? '创建环境中...' : '创建虚拟环境'}
          </Button>
        )}
        {model.commands_doc && (
          <Button type="button" onClick={onToggleCommandsDoc} style={{ fontSize: '0.8rem' }}>
            {showCommandsDoc ? '关闭文档' : '命令文档'}
          </Button>
        )}
      </div>
    </div>
  )
}
