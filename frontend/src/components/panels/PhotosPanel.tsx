"use client";

import { useState } from "react";
import { PanelShell } from "./PanelShell";
import { PhotoUpload } from "../PhotoUpload";
import { useWizardStore } from "../../store/wizard";
import type { PhotoRecord } from "../../lib/api";
import { segmentPhoto } from "../../lib/api";

export function PhotosPanel() {
  const setPhotoIds = useWizardStore((s) => s.setPhotoIds);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);
  const measurementsResponse = useWizardStore((s) => s.measurementsResponse);
  const photoIds = useWizardStore((s) => s.photoIds);

  const [isSegmenting, setIsSegmenting] = useState(false);
  const [segmentError, setSegmentError] = useState<string | null>(null);

  async function handleUploadSuccess(photos: PhotoRecord[]) {
    const ids = photos.map((p) => p.photo_id);
    setPhotoIds(ids);
    setSegmentError(null);
    setIsSegmenting(true);
    try {
      await Promise.all(ids.map((id) => segmentPhoto(id)));
      // Advance to diagnosis
      setActiveTool("diagnosis");
    } catch {
      setSegmentError("Segmentation failed — please try again.");
    } finally {
      setIsSegmenting(false);
    }
  }

  return (
    <PanelShell icon="📷" title="Upload photos" headerBg="#0EA5E9">
      <div className="px-4 py-4 flex flex-col gap-4">
        <p className="text-xs text-gray-400">
          Front, side, and back views help Claude diagnose fit issues across your whole body.
        </p>

        {!measurementsResponse && (
          <div className="bg-sky-50 border border-sky-200 rounded-xl px-3 py-2 text-xs text-sky-600">
            ℹ️ Enter measurements first so we can associate photos with your session.
          </div>
        )}

        {photoIds.length > 0 && (
          <div className="bg-sky-50 border border-sky-200 rounded-xl px-3 py-2 text-xs text-sky-700 font-medium">
            ✓ {photoIds.length} photo{photoIds.length > 1 ? "s" : ""} uploaded
          </div>
        )}

        {isSegmenting && (
          <div className="flex items-center gap-2 px-3 py-2 bg-sky-50 border border-sky-200 rounded-xl text-xs text-sky-700">
            <div className="w-3 h-3 border border-sky-300 border-t-sky-600 rounded-full animate-spin shrink-0" />
            Segmenting photos…
          </div>
        )}

        {segmentError && (
          <div role="alert" className="bg-red-50 border border-red-200 rounded-xl px-3 py-2 text-xs text-red-600">
            {segmentError}
          </div>
        )}

        {measurementsResponse ? (
          <PhotoUpload
            measurementId={measurementsResponse.measurement_id}
            onSuccess={handleUploadSuccess}
          />
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 flex flex-col items-center gap-2 text-center">
            <span className="text-2xl">📏</span>
            <p className="text-xs text-gray-400">
              Enter measurements first, then come back to upload photos.
            </p>
            <button
              type="button"
              onClick={() => setActiveTool("measurements")}
              className="text-xs text-sky-500 underline hover:text-sky-700 transition-colors"
            >
              Go to measurements →
            </button>
          </div>
        )}

        <p className="text-[11px] text-gray-300 text-center">
          Photos stay on your device — sent only to run diagnosis.
        </p>
      </div>
    </PanelShell>
  );
}
