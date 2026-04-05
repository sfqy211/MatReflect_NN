import { useEffect, useState } from 'react'

import { GalleryPreview } from './components/GalleryPreview'
import { ModuleRail } from './components/ModuleRail'
import { StatusPanel } from './components/StatusPanel'
import { WorkspaceCanvas } from './components/WorkspaceCanvas'
import { useRenderGallery, useSystemSummary } from './features/system/useSystemSummary'
import type { ModuleKey } from './types/api'

type ThemeMode = 'dark' | 'light'

export function App() {
  const [activeModule, setActiveModule] = useState<ModuleKey>('render')
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') {
      return 'dark'
    }

    const stored = window.localStorage.getItem('matreflect-theme')
    if (stored === 'light' || stored === 'dark') {
      return stored
    }

    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  })
  const systemQuery = useSystemSummary()
  const galleryQuery = useRenderGallery()
  const galleryItems = galleryQuery.data?.items ?? []
  const galleryCount = galleryQuery.data?.total ?? galleryItems.length

  const statusError =
    systemQuery.error instanceof Error ? systemQuery.error.message : systemQuery.error ? 'Unknown error' : undefined
  const backendLabel = statusError ? 'Backend Error' : systemQuery.isLoading ? 'Backend Syncing' : 'Backend Online'

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('matreflect-theme', theme)
  }, [theme])

  return (
    <div className="app-shell">
      <div className="ambient-orb ambient-orb--a" />
      <div className="ambient-orb ambient-orb--b" />

      <header className="top-bar">
        <div className="top-bar__identity">
          <span className="eyebrow">MatReflect_NN / V2 Lab</span>
          <h1>Material Intelligence Workbench</h1>
          <p>面向渲染、分析与模型管理的实验工作台。当前阶段先重建工作流骨架，再逐步替换旧版 Streamlit 页面。</p>
        </div>
        <div className="top-bar__actions">
          <div className="chip-group">
            <span className="chip">{backendLabel}</span>
            <span className="chip">{systemQuery.data?.mitsuba_exists ? 'Mitsuba Ready' : 'Mitsuba Pending'}</span>
            <span className="chip">{galleryCount} outputs indexed</span>
          </div>
          <button type="button" className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? '切换浅色' : '切换深色'}
          </button>
        </div>
      </header>

      <div className="workspace-grid">
        <ModuleRail activeModule={activeModule} onChange={setActiveModule} />
        <main className="center-stack">
          <WorkspaceCanvas activeModule={activeModule} galleryItems={galleryItems} />
          <GalleryPreview items={galleryItems} isLoading={galleryQuery.isLoading} />
        </main>
        <StatusPanel
          activeModule={activeModule}
          galleryCount={galleryCount}
          system={systemQuery.data}
          isLoading={systemQuery.isLoading}
          error={statusError}
        />
      </div>
    </div>
  )
}
