"use client";

import { useRef, useState } from "react";
import type { PhotoRecord } from "../lib/api";
import { postPhotos } from "../lib/api";

const MAX_FILES = 3;
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const VIEW_LABELS = ["front", "back", "side"] as const;
type ViewLabel = (typeof VIEW_LABELS)[number];

interface SelectedFile {
  file: File;
  objectUrl: string;
  label: ViewLabel | "";
  error?: string;
}

interface PhotoUploadProps {
  measurementId: string;
  onSuccess: (photos: PhotoRecord[]) => void;
}

export function PhotoUpload({ measurementId, onSuccess }: PhotoUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [globalError, setGlobalError] = useState<string>("");
  const [apiError, setApiError] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function processNewFiles(newFiles: File[]) {
    setApiError("");
    setGlobalError("");

    const allFiles = [...selectedFiles.map((s) => s.file), ...newFiles];
    let overflow = false;

    let kept = allFiles;
    if (allFiles.length > MAX_FILES) {
      kept = allFiles.slice(0, MAX_FILES);
      overflow = true;
    }

    // Revoke old URLs before rebuilding
    selectedFiles.forEach((s) => URL.revokeObjectURL(s.objectUrl));

    const next: SelectedFile[] = kept.map((file, idx) => {
      // Preserve existing labels where possible
      const existing = selectedFiles[idx];
      let error: string | undefined;
      if (file.size > MAX_FILE_SIZE_BYTES) {
        error = `"${file.name}" exceeds the 10 MB limit.`;
      }
      return {
        file,
        objectUrl: URL.createObjectURL(file),
        label: existing?.file === file ? existing.label : "",
        error,
      };
    });

    setSelectedFiles(next);

    if (overflow) {
      setGlobalError(`Maximum 3 photos allowed. Only the first 3 were kept.`);
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length > 0) processNewFiles(files);
    // Reset input so the same file can be re-selected
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) processNewFiles(files);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
  }

  function handleLabelChange(idx: number, label: ViewLabel | "") {
    setSelectedFiles((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, label } : item)),
    );
  }

  function removeFile(idx: number) {
    setSelectedFiles((prev) => {
      URL.revokeObjectURL(prev[idx].objectUrl);
      return prev.filter((_, i) => i !== idx);
    });
    setGlobalError("");
  }

  const validFiles = selectedFiles.filter((s) => !s.error);
  const allLabelled =
    validFiles.length > 0 && validFiles.every((s) => s.label !== "");
  const canUpload = !isUploading && allLabelled;

  async function handleUpload() {
    if (!canUpload) return;
    setIsUploading(true);
    setApiError("");
    try {
      const files = validFiles.map((s) => s.file);
      const labels = validFiles.map((s) => s.label as string);
      const records = await postPhotos(measurementId, files, labels);
      onSuccess(records);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed. Please try again.";
      setApiError(message);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        data-testid="dropzone"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => inputRef.current?.click()}
        className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-8 text-center hover:border-indigo-400 hover:bg-indigo-50"
        role="button"
        aria-label="Drop zone — click or drag photos here"
      >
        <p className="text-sm font-medium text-gray-600">Upload your muslin photos</p>
        <p className="mt-1 text-xs text-gray-400">Drag &amp; drop or click to browse</p>
        <p className="mt-1 text-xs text-gray-400">JPEG or PNG · Up to 3 files · Max 10 MB each</p>
      </div>

      {/* File input — visually hidden but accessible to assistive tech and tests */}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        multiple
        style={{ position: "absolute", width: 1, height: 1, opacity: 0, overflow: "hidden", zIndex: -1 }}
        onChange={handleInputChange}
        data-testid="file-input"
        aria-label="Select photos"
      />

      {/* Global error (overflow) */}
      {globalError && (
        <p className="text-sm text-amber-600" role="status">
          {globalError}
        </p>
      )}

      {/* Per-file thumbnails */}
      {selectedFiles.length > 0 && (
        <ul className="space-y-3">
          {selectedFiles.map((item, idx) => (
            <li key={item.objectUrl} className="flex items-start gap-3 rounded-lg border border-gray-200 p-3">
              {/* Thumbnail */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={item.objectUrl}
                alt={`Thumbnail for ${item.file.name}`}
                className="h-16 w-16 rounded object-cover"
              />
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium text-gray-700 truncate">{item.file.name}</p>
                {item.error ? (
                  <p className="text-xs text-red-600" role="alert">
                    {item.error}
                  </p>
                ) : (
                  <select
                    value={item.label}
                    onChange={(e) =>
                      handleLabelChange(idx, e.target.value as ViewLabel | "")
                    }
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                    aria-label={`View label for ${item.file.name}`}
                  >
                    <option value="">Select view…</option>
                    {VIEW_LABELS.map((l) => (
                      <option key={l} value={l}>
                        {l.charAt(0).toUpperCase() + l.slice(1)}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <button
                type="button"
                onClick={() => removeFile(idx)}
                className="text-gray-400 hover:text-red-500"
                aria-label={`Remove ${item.file.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* API error */}
      {apiError && (
        <p className="text-sm text-red-600" role="alert">
          {apiError}
        </p>
      )}

      {/* Upload button */}
      <button
        type="button"
        onClick={handleUpload}
        disabled={!canUpload}
        className="w-full rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300"
      >
        {isUploading ? "Uploading…" : "Upload photos"}
      </button>
    </div>
  );
}
