import { useEffect, useState } from "react";

import { GalleryPreview } from "./components/GalleryPreview";
import { ModuleRail } from "./components/ModuleRail";
import { StatusPanel } from "./components/StatusPanel";
import { WorkspaceCanvas } from "./components/WorkspaceCanvas";
import {
  useRenderGallery,
  useSystemSummary,
} from "./features/system/useSystemSummary";
import type { ModuleKey } from "./types/api";

type ThemeMode = "dark" | "light";

export function App() {
  const [activeModule, setActiveModule] = useState<ModuleKey>("render");
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
      <div className="workspace-grid">
        <ModuleRail activeModule={activeModule} onChange={setActiveModule} />
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
          {activeModule === "render" ? (
            <GalleryPreview
              items={galleryItems}
              isLoading={galleryQuery.isLoading}
            />
          ) : null}
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
  );
}
