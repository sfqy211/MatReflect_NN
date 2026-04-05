import { useEffect, useState } from "react";

import { ModuleRail } from "./components/ModuleRail";
import { WorkspaceCanvas } from "./components/WorkspaceCanvas";
import {
  useRenderGallery,
  useSystemSummary,
} from "./features/system/useSystemSummary";
import type { ModuleKey } from "./types/api";

type ThemeMode = "dark" | "light";

export function App() {
  const [activeModule, setActiveModule] = useState<ModuleKey>("render");
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
          collapsed={railCollapsed}
          onToggleCollapse={() => setRailCollapsed((current) => !current)}
        />
        <main className="center-stack">
          <WorkspaceCanvas
            activeModule={activeModule}
            galleryItems={galleryItems}
            galleryCount={galleryCount}
            theme={theme}
            onThemeChange={setTheme}
            system={systemQuery.data}
            systemError={statusError}
            systemLoading={systemQuery.isLoading}
          />
        </main>
      </div>
    </div>
  );
}
