/**
 * Tests for BodyViewer.tsx
 *
 * Three.js + jsdom is hostile — we mock all Three.js and GLTFLoader classes
 * extensively to avoid any real rendering attempts.
 */

import { describe, it, expect, vi, beforeEach, afterEach, Mock } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ---------------------------------------------------------------------------
// Mock fetchBodyMesh from api.ts
// ---------------------------------------------------------------------------
vi.mock("../../lib/api", () => ({
  fetchBodyMesh: vi.fn(),
  postMeasurements: vi.fn(),
  ApiValidationError: class ApiValidationError extends Error {},
}));

// ---------------------------------------------------------------------------
// Mock three-stdlib (OrbitControls)
// ---------------------------------------------------------------------------
const mockAutoRotate = { value: false };
const mockDispose = vi.fn();
const mockUpdate = vi.fn();
const mockOrbitControls = {
  autoRotate: false,
  dispose: mockDispose,
  update: mockUpdate,
  enableDamping: false,
};

vi.mock("three-stdlib", () => ({
  OrbitControls: vi.fn().mockImplementation(() => mockOrbitControls),
  GLTFLoader: vi.fn().mockImplementation(() => ({
    parse: vi.fn((buffer: ArrayBuffer, path: string, onLoad: (gltf: unknown) => void) => {
      const mockScene = {
        traverse: vi.fn(),
      };
      const mockMesh = {
        isMesh: true,
        geometry: { dispose: vi.fn() },
        material: { dispose: vi.fn() },
      };
      onLoad({ scene: mockScene });
    }),
  })),
}));

// ---------------------------------------------------------------------------
// Mock three
// ---------------------------------------------------------------------------
const mockSceneAdd = vi.fn();
const mockRendererDispose = vi.fn();
const mockRendererSetSize = vi.fn();
const mockRendererSetPixelRatio = vi.fn();
const mockRendererRender = vi.fn();
const mockRendererDomElement = document.createElement("canvas");

const mockScene = {
  add: mockSceneAdd,
  children: [],
  traverse: vi.fn(),
};

const mockCamera = {
  aspect: 1,
  updateProjectionMatrix: vi.fn(),
  position: { set: vi.fn() },
  lookAt: vi.fn(),
};

const mockAmbientLight = { isLight: true };
const mockDirectionalLight = {
  isLight: true,
  position: { set: vi.fn() },
};

vi.mock("three", () => ({
  WebGLRenderer: vi.fn().mockImplementation(() => ({
    dispose: mockRendererDispose,
    setSize: mockRendererSetSize,
    setPixelRatio: mockRendererSetPixelRatio,
    render: mockRendererRender,
    domElement: mockRendererDomElement,
  })),
  Scene: vi.fn().mockImplementation(() => mockScene),
  PerspectiveCamera: vi.fn().mockImplementation(() => mockCamera),
  AmbientLight: vi.fn().mockImplementation(() => mockAmbientLight),
  DirectionalLight: vi.fn().mockImplementation(() => mockDirectionalLight),
  Color: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Import component AFTER mocks are set up
// ---------------------------------------------------------------------------
import { BodyViewer } from "../BodyViewer";
import { fetchBodyMesh } from "../../lib/api";

const mockFetchBodyMesh = fetchBodyMesh as Mock;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const VALID_ARRAY_BUFFER = new ArrayBuffer(24);
// Inject glTF magic bytes at start
const view = new Uint8Array(VALID_ARRAY_BUFFER);
view[0] = 0x67; // 'g'
view[1] = 0x6c; // 'l'
view[2] = 0x54; // 'T'
view[3] = 0x46; // 'F'

beforeEach(() => {
  vi.clearAllMocks();
  mockOrbitControls.autoRotate = false;
  // Reset mock implementation
  mockFetchBodyMesh.mockResolvedValue(VALID_ARRAY_BUFFER);

  // Mock requestAnimationFrame to not actually loop
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
    // Don't actually call to avoid infinite loop
    return 0;
  });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});

  // Mock ResizeObserver
  (global as Record<string, unknown>).ResizeObserver = vi.fn().mockImplementation(
    (callback: ResizeObserverCallback) => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    }),
  );
});

afterEach(() => {
  // Do not use vi.restoreAllMocks() here — it calls mockRestore() on all vi.fn()
  // mocks including those created inside vi.mock() factories, wiping their
  // implementations and breaking tests that run after the first one.
  // The rAF/cAF spies are re-created in beforeEach so no restore is needed.
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("BodyViewer", () => {
  describe("loading state", () => {
    it("shows loading indicator while fetching", async () => {
      // Keep fetch pending
      let resolveFetch!: (buf: ArrayBuffer) => void;
      mockFetchBodyMesh.mockReturnValue(
        new Promise<ArrayBuffer>((resolve) => {
          resolveFetch = resolve;
        }),
      );

      render(<BodyViewer measurementId="test-id-123" />);

      expect(screen.getByTestId("body-viewer-loading")).toBeTruthy();

      // Resolve so we don't leak async
      await act(async () => {
        resolveFetch(VALID_ARRAY_BUFFER);
      });
    });

    it("calls fetchBodyMesh exactly once with measurementId on mount", async () => {
      render(<BodyViewer measurementId="my-measurement-id" />);

      await waitFor(() => {
        expect(mockFetchBodyMesh).toHaveBeenCalledTimes(1);
        expect(mockFetchBodyMesh).toHaveBeenCalledWith("my-measurement-id");
      });
    });
  });

  describe("success state", () => {
    it("calls onMeshLoaded after successful load", async () => {
      const onMeshLoaded = vi.fn();
      render(<BodyViewer measurementId="id-1" onMeshLoaded={onMeshLoaded} />);

      await waitFor(() => {
        expect(onMeshLoaded).toHaveBeenCalledTimes(1);
      });
    });

    it("removes loading indicator after successful load", async () => {
      render(<BodyViewer measurementId="id-1" />);

      await waitFor(() => {
        expect(screen.queryByTestId("body-viewer-loading")).toBeNull();
      });
    });

    it("adds AmbientLight to scene on success", async () => {
      render(<BodyViewer measurementId="id-1" />);

      await waitFor(() => {
        // Scene.add should have been called at least once
        expect(mockSceneAdd).toHaveBeenCalled();
      });
    });

    it("enables auto-rotation on mount", async () => {
      render(<BodyViewer measurementId="id-1" />);

      await waitFor(() => {
        expect(mockOrbitControls.autoRotate).toBe(true);
      });
    });

    it("shows Reset view button after load", async () => {
      render(<BodyViewer measurementId="id-1" />);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /reset view/i })).toBeTruthy();
      });
    });
  });

  describe("error state", () => {
    beforeEach(() => {
      mockFetchBodyMesh.mockRejectedValue(new Error("API error 500"));
    });

    it("shows error message on fetch failure", async () => {
      render(<BodyViewer measurementId="bad-id" />);

      await waitFor(() => {
        expect(
          screen.getByText(/couldn't build your 3d body/i),
        ).toBeTruthy();
      });
    });

    it("shows Retry button on fetch failure", async () => {
      render(<BodyViewer measurementId="bad-id" />);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
      });
    });

    it("retry button re-invokes fetchBodyMesh", async () => {
      const user = userEvent.setup();
      render(<BodyViewer measurementId="bad-id" />);

      const retryBtn = await screen.findByRole("button", { name: /retry/i });
      await user.click(retryBtn);

      expect(mockFetchBodyMesh).toHaveBeenCalledTimes(2);
    });
  });

  describe("auto-rotation control", () => {
    it("disables auto-rotation on pointerdown", async () => {
      render(<BodyViewer measurementId="id-1" />);

      await waitFor(() => {
        expect(mockOrbitControls.autoRotate).toBe(true);
      });

      // Simulate pointerdown on the canvas/container
      const container = screen.getByTestId("body-viewer-canvas");
      act(() => {
        container.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
      });

      expect(mockOrbitControls.autoRotate).toBe(false);
    });

    it("Reset view button re-enables auto-rotation", async () => {
      const user = userEvent.setup();
      render(<BodyViewer measurementId="id-1" />);

      // Wait for load and button
      const resetBtn = await screen.findByRole("button", { name: /reset view/i });

      // Manually disable auto-rotation first
      mockOrbitControls.autoRotate = false;

      await user.click(resetBtn);

      expect(mockOrbitControls.autoRotate).toBe(true);
    });
  });

  describe("unmount cleanup", () => {
    it("calls renderer.dispose() on unmount", async () => {
      const { unmount } = render(<BodyViewer measurementId="id-1" />);

      await waitFor(() => {
        expect(screen.queryByTestId("body-viewer-loading")).toBeNull();
      });

      unmount();

      expect(mockRendererDispose).toHaveBeenCalled();
    });

    it("calls controls.dispose() on unmount", async () => {
      const { unmount } = render(<BodyViewer measurementId="id-1" />);

      await waitFor(() => {
        expect(screen.queryByTestId("body-viewer-loading")).toBeNull();
      });

      unmount();

      expect(mockDispose).toHaveBeenCalled();
    });
  });

  describe("optional className prop", () => {
    it("applies className to wrapper element", async () => {
      const { container } = render(
        <BodyViewer measurementId="id-1" className="my-class" />,
      );

      // The wrapper should have the className
      expect(container.firstElementChild?.className).toContain("my-class");
    });
  });
});
