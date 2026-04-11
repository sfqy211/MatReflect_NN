import { useEffect, useState } from "react";

import { ModuleRail } from "./components/ModuleRail";
import { WorkspaceCanvas } from "./components/WorkspaceCanvas";
import {
  useRenderGallery,
  useSystemSummary,
} from "./features/system/useSystemSummary";
import { StatusBar } from "./components/StatusBar";
import type { ModuleKey } from "./types/api";

export type ThemeMode = "dark" | "light";

const THEME_STORAGE_KEY = "matreflect-theme";
const FONT_SIZE_STORAGE_KEY = "matreflect-font-size";
const DEFAULT_FONT_SIZE = 13;
const MIN_FONT_SIZE = 11;
const MAX_FONT_SIZE = 20;

function clampFontSize(value: number) {
  if (Number.isNaN(value)) {
    return DEFAULT_FONT_SIZE;
  }
  return Math.min(MAX_FONT_SIZE, Math.max(MIN_FONT_SIZE, value));
}

export type AnalysisSubView = 'evaluate' | 'compare' | 'grid' | 'compare-grid'
export type ModelsSubView = string

export function App() {
  const [activeModule, setActiveModule] = useState<ModuleKey>("render");
  const [activeAnalysisSubView, setActiveAnalysisSubView] = useState<AnalysisSubView>('evaluate');
  const [activeModelsSubView, setActiveModelsSubView] = useState<ModelsSubView>('');
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") {
      return "dark";
    }

    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") {
      return stored;
    }

    return window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  });
  const [fontSize, setFontSize] = useState<number>(() => {
    if (typeof window === "undefined") {
      return DEFAULT_FONT_SIZE;
    }

    const stored = window.localStorage.getItem(FONT_SIZE_STORAGE_KEY);
    if (!stored) {
      return DEFAULT_FONT_SIZE;
    }

    return clampFontSize(Number.parseFloat(stored));
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
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    const normalizedFontSize = clampFontSize(fontSize);
    document.documentElement.style.setProperty(
      "--app-font-size",
      `${normalizedFontSize}px`,
    );
    window.localStorage.setItem(
      FONT_SIZE_STORAGE_KEY,
      normalizedFontSize.toString(),
    );
  }, [fontSize]);

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
            theme={theme}
            onThemeChange={setTheme}
            fontSize={fontSize}
            onFontSizeChange={setFontSize}
          />
        </main>
      </div>
      <StatusBar />
    </div>
  );
}
