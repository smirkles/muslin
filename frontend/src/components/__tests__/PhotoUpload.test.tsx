import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PhotoUpload } from "../PhotoUpload";

// ---------------------------------------------------------------------------
// Mock URL.createObjectURL (jsdom does not implement it)
// ---------------------------------------------------------------------------
globalThis.URL.createObjectURL = vi.fn((blob: Blob) => `blob:mock/${Math.random()}`);
globalThis.URL.revokeObjectURL = vi.fn();

// ---------------------------------------------------------------------------
// Mock the API postPhotos function
// ---------------------------------------------------------------------------
vi.mock("../../lib/api", () => ({
  postPhotos: vi.fn(),
  postMeasurements: vi.fn(),
  ApiValidationError: class ApiValidationError extends Error {},
}));

const mockPostPhotos = vi.fn();

import * as apiModule from "../../lib/api";

const MEASUREMENT_ID = "test-measurement-id-1234";

function makePngFile(name = "photo.png", sizeBytes = 500): File {
  const buffer = new Uint8Array(sizeBytes);
  buffer[0] = 0x89;
  buffer[1] = 0x50;
  buffer[2] = 0x4e;
  buffer[3] = 0x47;
  return new File([buffer], name, { type: "image/png" });
}

function makeJpegFile(name = "photo.jpg", sizeBytes = 500): File {
  const buffer = new Uint8Array(sizeBytes);
  buffer[0] = 0xff;
  buffer[1] = 0xd8;
  buffer[2] = 0xff;
  return new File([buffer], name, { type: "image/jpeg" });
}

function makeLargeFile(name = "big.jpg"): File {
  // 11 MB > 10 MB limit
  const sizeBytes = 11 * 1024 * 1024;
  const buffer = new Uint8Array(sizeBytes);
  buffer[0] = 0xff;
  buffer[1] = 0xd8;
  buffer[2] = 0xff;
  return new File([buffer], name, { type: "image/jpeg" });
}

describe("PhotoUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Point apiModule.postPhotos to our local mock
    (apiModule as { postPhotos: typeof mockPostPhotos }).postPhotos = mockPostPhotos;
  });

  // -------------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------------
  describe("rendering", () => {
    it("renders a drop zone", () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      expect(screen.getByText(/upload your muslin photos/i)).toBeTruthy();
    });

    it("renders an upload button", () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      expect(screen.getByRole("button", { name: /upload/i })).toBeTruthy();
    });

    it("upload button is disabled initially (no files selected)", () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      expect(screen.getByRole("button", { name: /upload/i })).toBeDisabled();
    });
  });

  // -------------------------------------------------------------------------
  // Thumbnail rendering
  // -------------------------------------------------------------------------
  describe("thumbnail rendering", () => {
    it("shows a thumbnail immediately when a JPEG file is dropped", async () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      const file = makeJpegFile("front.jpg");
      await userEvent.upload(dropzone, [file]);

      const imgs = screen.getAllByRole("img");
      expect(imgs.length).toBeGreaterThanOrEqual(1);
      // Thumbnails have blob: URLs from createObjectURL
      const hasBlobSrc = imgs.some((img) => img.getAttribute("src")?.startsWith("blob:"));
      expect(hasBlobSrc).toBe(true);
    });

    it("shows a thumbnail for a PNG file", async () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      const file = makePngFile("back.png");
      await userEvent.upload(dropzone, [file]);

      const imgs = screen.getAllByRole("img");
      expect(imgs.length).toBeGreaterThanOrEqual(1);
    });
  });

  // -------------------------------------------------------------------------
  // Client-side size validation
  // -------------------------------------------------------------------------
  describe("client-side size validation", () => {
    it("shows an inline error when a file > 10 MB is dropped", async () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      const bigFile = makeLargeFile("big.jpg");
      await userEvent.upload(dropzone, [bigFile]);

      expect(screen.getByText(/10 mb/i)).toBeTruthy();
    });

    it("does not include an oversized file in the submission list", async () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      const bigFile = makeLargeFile("big.jpg");
      await userEvent.upload(dropzone, [bigFile]);

      // Upload button should still be disabled since no valid files
      expect(screen.getByRole("button", { name: /upload/i })).toBeDisabled();
    });
  });

  // -------------------------------------------------------------------------
  // More than 3 files
  // -------------------------------------------------------------------------
  describe("more than 3 files", () => {
    it("shows an inline error when more than 3 files are dropped", async () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      const files = [
        makeJpegFile("a.jpg"),
        makeJpegFile("b.jpg"),
        makeJpegFile("c.jpg"),
        makeJpegFile("d.jpg"),
      ];
      await userEvent.upload(dropzone, files);

      expect(screen.getByText(/3/)).toBeTruthy();
    });

    it("keeps only the first 3 files when more than 3 are dropped", async () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      const files = [
        makeJpegFile("a.jpg"),
        makeJpegFile("b.jpg"),
        makeJpegFile("c.jpg"),
        makeJpegFile("d.jpg"),
      ];
      await userEvent.upload(dropzone, files);

      // Should show only 3 thumbnails
      const imgs = screen.getAllByRole("img");
      expect(imgs.filter((img) => img.getAttribute("src")?.startsWith("blob:")).length).toBe(3);
    });
  });

  // -------------------------------------------------------------------------
  // View label selection
  // -------------------------------------------------------------------------
  describe("view label selection", () => {
    it("upload button is disabled until all files have a view label", async () => {
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      const file = makeJpegFile("front.jpg");
      await userEvent.upload(dropzone, [file]);

      // No label selected yet → button still disabled
      expect(screen.getByRole("button", { name: /upload/i })).toBeDisabled();
    });

    it("upload button becomes enabled when file has a label", async () => {
      const user = userEvent.setup();
      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      const file = makeJpegFile("front.jpg");
      await userEvent.upload(dropzone, [file]);

      // Select a view label
      const select = screen.getByRole("combobox");
      await user.selectOptions(select, "front");

      expect(screen.getByRole("button", { name: /upload/i })).not.toBeDisabled();
    });
  });

  // -------------------------------------------------------------------------
  // onSuccess callback
  // -------------------------------------------------------------------------
  describe("onSuccess callback", () => {
    it("calls onSuccess with PhotoRecord[] on successful upload", async () => {
      const user = userEvent.setup();
      const onSuccess = vi.fn();
      const mockRecords = [
        { photo_id: "uuid-1", view_label: "front", filename: "front.jpg" },
      ];
      mockPostPhotos.mockResolvedValueOnce(mockRecords);

      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={onSuccess} />);
      const dropzone = screen.getByTestId("dropzone");

      await userEvent.upload(dropzone, [makeJpegFile("front.jpg")]);
      await user.selectOptions(screen.getByRole("combobox"), "front");
      await user.click(screen.getByRole("button", { name: /upload/i }));

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledWith(mockRecords);
      });
    });
  });

  // -------------------------------------------------------------------------
  // API error handling
  // -------------------------------------------------------------------------
  describe("API error handling", () => {
    it("displays an error message when the API returns an error", async () => {
      const user = userEvent.setup();
      mockPostPhotos.mockRejectedValueOnce(new Error("API error 413"));

      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      await userEvent.upload(dropzone, [makeJpegFile("front.jpg")]);
      await user.selectOptions(screen.getByRole("combobox"), "front");
      await user.click(screen.getByRole("button", { name: /upload/i }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeTruthy();
      });
    });

    it("allows retry after an API error", async () => {
      const user = userEvent.setup();
      mockPostPhotos.mockRejectedValueOnce(new Error("API error 500"));

      render(<PhotoUpload measurementId={MEASUREMENT_ID} onSuccess={vi.fn()} />);
      const dropzone = screen.getByTestId("dropzone");

      await userEvent.upload(dropzone, [makeJpegFile("front.jpg")]);
      await user.selectOptions(screen.getByRole("combobox"), "front");
      await user.click(screen.getByRole("button", { name: /upload/i }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeTruthy();
      });

      // Upload button is still present and can be clicked again
      expect(screen.getByRole("button", { name: /upload/i })).not.toBeDisabled();
    });
  });
});
