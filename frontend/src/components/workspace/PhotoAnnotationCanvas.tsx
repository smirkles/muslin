"use client";

import { useState } from "react";
import { useWizardStore } from "../../store/wizard";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RegionHint {
  cx: number;  // % from left
  cy: number;  // % from top
  rx: number;  // % of width
  ry: number;  // % of height
  preferredView: string;
}

function getRegionForIssue(issueType: string): RegionHint {
  const t = issueType.toLowerCase().replace(/[_\s-]+/g, " ");

  // Neck / collar / neckline — checked before "back" so "neckline_gaping_at_back" lands here, not upper-back
  if (t.includes("neck") || t.includes("collar")) {
    return { cx: 50, cy: 22, rx: 18, ry: 7, preferredView: "front" };
  }
  // Shoulder — separate from neck
  if (t.includes("shoulder")) {
    return { cx: 50, cy: 30, rx: 26, ry: 8, preferredView: "front" };
  }
  // Sleeve / armhole
  if (t.includes("sleeve") || t.includes("armhole") || t.includes("arm")) {
    return { cx: 50, cy: 35, rx: 28, ry: 9, preferredView: "front" };
  }
  // Bust / chest / dart
  if (t.includes("bust") || t.includes("chest") || t.includes("fba") || t.includes("dart")) {
    return { cx: 50, cy: 36, rx: 18, ry: 10, preferredView: "front" };
  }
  // Waist
  if (t.includes("waist")) {
    return { cx: 50, cy: 50, rx: 16, ry: 7, preferredView: "front" };
  }
  // Hip / seat — checked before hem so "hip hem flare" focuses the body region
  if (t.includes("hip") || t.includes("seat")) {
    return { cx: 50, cy: 60, rx: 20, ry: 8, preferredView: "front" };
  }
  // Hem — bottom of garment
  if (t.includes("hem")) {
    return { cx: 50, cy: 80, rx: 22, ry: 6, preferredView: "front" };
  }
  // Swayback / lower back
  if (t.includes("swayback") || (t.includes("back") && t.includes("lower"))) {
    return { cx: 50, cy: 62, rx: 20, ry: 9, preferredView: "back" };
  }
  // General back / round shoulders
  if (t.includes("back") || t.includes("round")) {
    return { cx: 50, cy: 30, rx: 22, ry: 11, preferredView: "back" };
  }
  // Side seam / swing / balance
  if (t.includes("side") || t.includes("seam") || t.includes("swing") || t.includes("balance")) {
    return { cx: 50, cy: 50, rx: 20, ry: 18, preferredView: "front" };
  }
  // Default — centre of garment
  return { cx: 50, cy: 40, rx: 20, ry: 10, preferredView: "front" };
}

export function PhotoAnnotationCanvas() {
  const photos = useWizardStore((s) => s.photos);
  const diagnosisResult = useWizardStore((s) => s.diagnosisResult);
  const selectedIssueIndex = useWizardStore((s) => s.selectedIssueIndex);

  const [activePhotoIndex, setActivePhotoIndex] = useState(0);

  if (photos.length === 0) return null;

  const activePhoto = photos[activePhotoIndex] ?? photos[0];
  const selectedIssue = diagnosisResult && selectedIssueIndex !== null
    ? diagnosisResult.issues[selectedIssueIndex]
    : null;

  const region = selectedIssue ? getRegionForIssue(selectedIssue.issue_type) : null;

  // Prefer the view that matches the issue region
  const preferredIndex = region
    ? photos.findIndex((p) => p.view_label === region.preferredView)
    : -1;
  const displayIndex = preferredIndex >= 0 ? preferredIndex : activePhotoIndex;
  const displayPhoto = photos[displayIndex] ?? photos[0];

  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-3 p-6">
      {/* Main photo with SVG overlay */}
      <div className="relative flex items-center justify-center" style={{ maxHeight: "calc(100% - 60px)", maxWidth: "100%" }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          key={displayPhoto.photo_id}
          src={`${API_URL}/photos/${displayPhoto.photo_id}/image`}
          alt={`${displayPhoto.view_label} view`}
          className="max-h-full max-w-full object-contain rounded-xl shadow-lg"
          style={{ maxHeight: "420px" }}
        />

        {/* SVG glow overlay — positioned absolutely over the image */}
        {region && (
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
          >
            <defs>
              <radialGradient id="glowGrad" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#F43F5E" stopOpacity="0.55" />
                <stop offset="60%" stopColor="#F43F5E" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#F43F5E" stopOpacity="0" />
              </radialGradient>
              <filter id="blur">
                <feGaussianBlur stdDeviation="1.5" />
              </filter>
            </defs>

            {/* Outer glow */}
            <ellipse
              cx={region.cx}
              cy={region.cy}
              rx={region.rx * 1.6}
              ry={region.ry * 1.6}
              fill="url(#glowGrad)"
              filter="url(#blur)"
              className="animate-pulse"
              style={{ animationDuration: "1.4s" }}
            />

            {/* Inner ring */}
            <ellipse
              cx={region.cx}
              cy={region.cy}
              rx={region.rx}
              ry={region.ry}
              fill="none"
              stroke="#F43F5E"
              strokeWidth="0.6"
              strokeDasharray="2 1.5"
              opacity="0.85"
              className="animate-pulse"
              style={{ animationDuration: "1.4s" }}
            />
          </svg>
        )}
      </div>

      {/* Thumbnail strip — show view switcher if multiple photos */}
      {photos.length > 1 && (
        <div className="flex items-center gap-2">
          {photos.map((photo, i) => (
            <button
              key={photo.photo_id}
              type="button"
              onClick={() => setActivePhotoIndex(i)}
              className={[
                "flex flex-col items-center gap-0.5 transition-all",
                i === displayIndex ? "opacity-100" : "opacity-50 hover:opacity-75",
              ].join(" ")}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`${API_URL}/photos/${photo.photo_id}/image`}
                alt={photo.view_label}
                className={[
                  "w-10 h-14 object-cover rounded-md border-2 transition-colors",
                  i === displayIndex ? "border-rose-400" : "border-gray-200",
                ].join(" ")}
              />
              <span className="text-[9px] text-gray-400 capitalize">{photo.view_label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Hint text */}
      {!selectedIssue && diagnosisResult && (
        <p className="text-[11px] text-gray-400 text-center">
          Click an issue in the panel to highlight it on the photo
        </p>
      )}
    </div>
  );
}
