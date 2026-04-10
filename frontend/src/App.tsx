import { useEffect, useState } from "react";

import { ModuleRail } from "./components/ModuleRail";
import { WorkspaceCanvas } from "./components/WorkspaceCanvas";
import {
  useRenderGallery,
  useSystemSummary,
} from "./features/system/useSystemSummary";
import { StatusBar } from "./components/StatusBar";
import type { ModuleKey } from "./types/api";

type ThemeMode = "dark" | "light";

export type AnalysisSubView = 'preview' | 'evaluate' | 'compare' | 'grid' | 'compare-grid'
export type ModelsSubView = string

export function App() {
  const [activeModule, setActiveModule] = useState<ModuleKey>("render");
  const [activeAnalysisSubView, setActiveAnalysisSubView] = useState<AnalysisSubView>('preview');
  const [activeModelsSubView, setActiveModelsSubView] = useState<ModelsSubView>('');
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") {
      return "dark";
    }

    const stored = window.localStorage.getItem("matreflect-theme");
    if (stored === "light" || stored === "dark") {
      return stored;
    }

    return window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  });
  const systemQuery = useSystemSummary();
  const galleryQuery = useRenderGallery();
  const galleryItems = galleryQuery.data?.items ?? [];
  const galleryCount = galleryQuery.data?.total ?? galleryItems.length;

  const statusError =
    systemQuery.error instanceof Error
      ? systemQuery.error.message
      : systemQuery.error
        ? "Unknown error"
        : undefined;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("matreflect-theme", theme);
  }, [theme]);

  return (
    <div className="app-shell">
      <div className={railCollapsed ? "workspace-grid workspace-grid--collapsed" : "workspace-grid"}>
        <ModuleRail
          activeModule={activeModule}
          onChange={setActiveModule}
          activeAnalysisSubView={activeAnalysisSubView}
          onAnalysisSubViewChange={setActiveAnalysisSubView}
          activeModelsSubView={activeModelsSubView}
          onModelsSubViewChange={setActiveModelsSubView}
          collapsed={railCollapsed}
          onToggleCollapse={() => setRailCollapsed((current) => !current)}
          theme={theme}
          onThemeChange={setTheme}
        />
        <main className="center-stack">
          <WorkspaceCanvas
            activeModule={activeModule}
            activeAnalysisSubView={activeAnalysisSubView}
            onAnalysisSubViewChange={setActiveAnalysisSubView}
            activeModelsSubView={activeModelsSubView}
            onModelsSubViewChange={setActiveModelsSubView}
            galleryItems={galleryItems}
            galleryCount={galleryCount}
            system={systemQuery.data}
            systemError={statusError}
            systemLoading={systemQuery.isLoading}
          />
        </main>
      </div>
      <StatusBar />
    </div>
  );
}
