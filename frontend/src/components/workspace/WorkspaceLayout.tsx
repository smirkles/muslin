"use client";

import { useWizardStore } from "../../store/wizard";
import { TopBar } from "./TopBar";
import { LeftNav } from "./LeftNav";
import { PatternCanvas } from "./PatternCanvas";
import { RightPanel } from "./RightPanel";
import { MeasurementsPanel } from "../panels/MeasurementsPanel";
import { PhotosPanel } from "../panels/PhotosPanel";
import { DiagnosisPanel } from "../panels/DiagnosisPanel";
import { CascadePanel } from "../panels/CascadePanel";
import { DownloadPanel } from "../panels/DownloadPanel";
import type { ToolId } from "../../lib/tools";

const PANELS: Record<ToolId, React.ComponentType> = {
  measurements: MeasurementsPanel,
  photos: PhotosPanel,
  diagnosis: DiagnosisPanel,
  cascade: CascadePanel,
  download: DownloadPanel,
};

export function WorkspaceLayout() {
  const activeTool = useWizardStore((s) => s.activeTool);
  const ActivePanel = activeTool ? PANELS[activeTool] : null;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-white">
      <TopBar />

      <div className="flex flex-1 overflow-hidden relative">
        {/* Left icon nav */}
        <LeftNav />

        {/* Fly-out panel — absolutely positioned, floats over canvas */}
        {ActivePanel && (
          <div className="absolute left-14 top-0 bottom-0 w-[300px] z-10 border-r border-gray-100">
            <ActivePanel />
          </div>
        )}

        {/* Pattern canvas — always full width, panel floats over it */}
        <PatternCanvas />

        {/* Right panel — body viewer + contextual info */}
        <RightPanel />
      </div>
    </div>
  );
}
