"use client";

import { useState } from "react";
import { PanelShell } from "./PanelShell";
import { useWizardStore } from "../../store/wizard";
import { downloadPattern } from "../../lib/api";

export function DownloadPanel() {
  const cascadeScript = useWizardStore((s) => s.cascadeScript);
  const diagnosisResult = useWizardStore((s) => s.diagnosisResult);
  const gradedPatternId = useWizardStore((s) => s.gradedPatternId);
  const reset = useWizardStore((s) => s.reset);

  const [downloading, setDownloading] = useState<"svg" | "pdf" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function handleDownload(format: "svg" | "pdf") {
    if (!gradedPatternId) return;
    setDownloading(format);
    setDownloadError(null);
    try {
      const blob = await downloadPattern(gradedPatternId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `muslin-adjusted.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setDownloadError("Download failed — please try again.");
    } finally {
      setDownloading(null);
    }
  }

  const isReady = Boolean(cascadeScript);

  return (
    <PanelShell icon="⬇" title="Download" headerBg="#F59E0B">
      <div className="px-4 py-4 flex flex-col gap-4">

        {/* Ready state */}
        {isReady ? (
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-3 py-3 text-xs text-amber-800 font-medium">
            🎉 Your adjusted pattern is ready!
            <p className="font-normal text-amber-600 mt-1">All adjustments applied, seam allowances added.</p>
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs text-gray-400">
            Apply adjustments to unlock download.
          </div>
        )}

        {downloadError && (
          <div role="alert" className="bg-red-50 border border-red-200 rounded-xl px-3 py-2 text-xs text-red-600">
            {downloadError}
          </div>
        )}

        {/* Download SVG */}
        <button
          type="button"
          disabled={!isReady || downloading !== null}
          onClick={() => handleDownload("svg")}
          className="w-full bg-amber-500 text-white text-sm font-semibold py-3 rounded-xl hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {downloading === "svg" ? "Downloading…" : "Download SVG"}
        </button>
        <p className="text-[11px] text-gray-400 -mt-2 text-center">Vector — open in any sewing software</p>

        {/* Download PDF */}
        <button
          type="button"
          disabled={!isReady || downloading !== null}
          onClick={() => handleDownload("pdf")}
          className="w-full bg-[#1E1B4B] text-white text-sm font-semibold py-3 rounded-xl hover:bg-indigo-900 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {downloading === "pdf" ? "Downloading…" : "Download PDF"}
        </button>
        <p className="text-[11px] text-gray-400 -mt-2 text-center">Print-ready — A4 or US Letter</p>

        <div className="h-px bg-gray-100" />

        {/* Adjustments summary */}
        {(cascadeScript || diagnosisResult) && (
          <div className="flex flex-col gap-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Adjustments applied</p>
            {cascadeScript && (
              <div className="bg-white border border-gray-100 rounded-xl p-3 text-xs shadow-sm flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-500 shrink-0" />
                <div>
                  <p className="font-semibold text-gray-700">{cascadeScript.adjustment_type}</p>
                  <p className="text-gray-400">{cascadeScript.amount_cm} cm change</p>
                </div>
              </div>
            )}
            <div className="bg-white border border-gray-100 rounded-xl p-3 text-xs shadow-sm flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
              <div>
                <p className="font-semibold text-gray-700">Seam allowance added</p>
                <p className="text-gray-400">1 cm all seams</p>
              </div>
            </div>
          </div>
        )}

        <div className="h-px bg-gray-100" />

        {/* Start over */}
        <button
          type="button"
          onClick={reset}
          className="w-full text-xs text-gray-400 hover:text-gray-600 transition-colors py-1"
        >
          ← Start a new fitting session
        </button>
      </div>
    </PanelShell>
  );
}
