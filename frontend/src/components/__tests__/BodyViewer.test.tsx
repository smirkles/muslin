/**
 * Tests for BodyViewer.tsx (spec 19 — Three.js morph-target body viewer)
 *
 * The component takes measurements + gender props and animates a GLB body model
 * via Three.js morph targets. Three.js and three-stdlib are fully mocked to
 * avoid JSDOM / WebGL incompatibility.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ---------------------------------------------------------------------------
// Shared mock objects (defined before vi.mock so factories can close over them)
// ---------------------------------------------------------------------------

const mockDispose = vi.fn();
const mockUpdate = vi.fn();
const mockControls = {
  autoRotate: false,
  enableDamping: false,
  enablePan: false,
  autoRotateSpeed: 0,
  minDistance: 0,
  maxDistance: 0,
  dispose: mockDispose,
  update: mockUpdate,
  target: { set: vi.fn() },
};

const mockRendererDispose = vi.fn();
const mockRendererSetSize = vi.fn();
const mockRendererSetPixelRatio = vi.fn();
const mockRendererRender = vi.fn();
const mockRendererDomElement = document.createElement("canvas");

const mockSceneAdd = vi.fn();

// Vector/Box mocks — y:1.7 so scale = targetHeight(1.7) / size.y(1.7) = 1 (safe)
const mockVec3 = { x: 0, y: 1.7, z: 0 };
const mockBox3 = {
  setFromObject: vi.fn().mockReturnThis(),
  getSize: vi.fn(),
  getCenter: vi.fn(),
  min: { y: 0 },
};

// ---------------------------------------------------------------------------
// Mock three-stdlib
// ---------------------------------------------------------------------------

vi.mock("three-stdlib", () => ({
  OrbitControls: vi.fn().mockImplementation(() => mockControls),
  GLTFLoader: vi.fn().mockImplementation(() => ({
    load: vi.fn(
      (
        _url: string,
        onLoad: (gltf: {
          scene: {
            traverse: ReturnType<typeof vi.fn>;
            scale: { setScalar: ReturnType<typeof vi.fn> };
            position: { set: ReturnType<typeof vi.fn> };
          };
        }) => void,
      ) => {
        onLoad({
          scene: {
            traverse: vi.fn(),
            scale: { setScalar: vi.fn() },
            position: { set: vi.fn() },
          },
        });
      },
    ),
  })),
}));

// ---------------------------------------------------------------------------
// Mock three
// ---------------------------------------------------------------------------

vi.mock("three", () => ({
  WebGLRenderer: vi.fn().mockImplementation(() => ({
    dispose: mockRendererDispose,
    setSize: mockRendererSetSize,
    setPixelRatio: mockRendererSetPixelRatio,
    render: mockRendererRender,
    domElement: mockRendererDomElement,
  })),
  Scene: vi.fn().mockImplementation(() => ({ add: mockSceneAdd })),
  PerspectiveCamera: vi.fn().mockImplementation(() => ({
    position: { set: vi.fn() },
    lookAt: vi.fn(),
  })),
  AmbientLight: vi.fn().mockImplementation(() => ({})),
  DirectionalLight: vi.fn().mockImplementation(() => ({
    position: { set: vi.fn() },
  })),
  Box3: vi.fn().mockImplementation(() => mockBox3),
  Vector3: vi.fn().mockImplementation(() => mockVec3),
  Mesh: vi.fn(),
  MeshStandardMaterial: vi.fn().mockImplementation(() => ({})),
  Group: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Import component AFTER mocks
// ---------------------------------------------------------------------------

import { BodyViewer } from "../BodyViewer";
import type { BodyGender } from "../../store/wizard";
import { GLTFLoader } from "three-stdlib";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DEFAULT_MEASUREMENTS = {
  bust_cm: 96,
  high_bust_cm: 85,
  apex_to_apex_cm: 18,
  waist_cm: 78,
  hip_cm: 104,
  height_cm: 168,
  back_length_cm: 39.5,
};

function renderViewer(
  measurements = DEFAULT_MEASUREMENTS,
  gender: BodyGender = "female",
  onGenderChange = vi.fn(),
) {
  return render(
    <BodyViewer
      measurements={measurements}
      gender={gender}
      onGenderChange={onGenderChange}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockControls.autoRotate = false;
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 0);
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
});

afterEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("BodyViewer", () => {
  describe("loading state", () => {
    it("shows loading text on initial render", () => {
      // GLTFLoader default mock calls onLoad synchronously, but React state
      // update ("success") is scheduled — initial render is always "loading"
      renderViewer();
      expect(screen.getByText(/loading body model/i)).toBeTruthy();
    });

    it("shows loading text while GLB is pending", () => {
      // Override: load callback never fires
      vi.mocked(GLTFLoader).mockImplementationOnce(
        () => ({ load: vi.fn() }) as unknown as InstanceType<typeof GLTFLoader>,
      );
      renderViewer();
      expect(screen.getByText(/loading body model/i)).toBeTruthy();
    });
  });

  describe("success state", () => {
    it("hides loading text after successful GLB load", async () => {
      renderViewer();
      await waitFor(() => {
        expect(screen.queryByText(/loading body model/i)).toBeNull();
      });
    });

    it("shows gender toggle F and M buttons after load", async () => {
      renderViewer();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: "F" })).toBeTruthy();
        expect(screen.getByRole("button", { name: "M" })).toBeTruthy();
      });
    });

    it("enables auto-rotation after load", async () => {
      renderViewer();
      await waitFor(() => {
        expect(mockControls.autoRotate).toBe(true);
      });
    });

    it("renders canvas container with data-testid", async () => {
      renderViewer();
      expect(screen.getByTestId("body-viewer-canvas")).toBeTruthy();
    });
  });

  describe("error state", () => {
    it("shows error message on GLB load failure", async () => {
      vi.mocked(GLTFLoader).mockImplementationOnce(
        () =>
          ({
            load: vi.fn(
              (
                _url: string,
                _onLoad: unknown,
                _onProgress: unknown,
                onError: (e: ErrorEvent) => void,
              ) => {
                onError(new Error("GLB load failed") as unknown as ErrorEvent);
              },
            ),
          }) as unknown as InstanceType<typeof GLTFLoader>,
      );
      renderViewer();
      await waitFor(() => {
        expect(screen.getByText(/couldn't load 3d body/i)).toBeTruthy();
      });
    });
  });

  describe("gender toggle", () => {
    it("calls onGenderChange('male') when M is clicked", async () => {
      const user = userEvent.setup();
      const onGenderChange = vi.fn();
      render(
        <BodyViewer
          measurements={DEFAULT_MEASUREMENTS}
          gender="female"
          onGenderChange={onGenderChange}
        />,
      );
      const mBtn = await screen.findByRole("button", { name: "M" });
      await user.click(mBtn);
      expect(onGenderChange).toHaveBeenCalledWith("male");
    });

    it("calls onGenderChange('female') when F is clicked", async () => {
      const user = userEvent.setup();
      const onGenderChange = vi.fn();
      render(
        <BodyViewer
          measurements={DEFAULT_MEASUREMENTS}
          gender="male"
          onGenderChange={onGenderChange}
        />,
      );
      const fBtn = await screen.findByRole("button", { name: "F" });
      await user.click(fBtn);
      expect(onGenderChange).toHaveBeenCalledWith("female");
    });
  });

  describe("auto-rotation control", () => {
    it("disables auto-rotation on pointerdown", async () => {
      renderViewer();
      await waitFor(() => expect(mockControls.autoRotate).toBe(true));

      const canvas = screen.getByTestId("body-viewer-canvas");
      act(() => {
        canvas.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
      });
      expect(mockControls.autoRotate).toBe(false);
    });
  });

  describe("null measurements", () => {
    it("renders without crash when measurements is null", async () => {
      render(
        <BodyViewer
          measurements={null}
          gender="female"
          onGenderChange={vi.fn()}
        />,
      );
      await waitFor(() => {
        expect(screen.queryByText(/loading body model/i)).toBeNull();
      });
    });
  });

  describe("className prop", () => {
    it("applies className to the wrapper element", () => {
      const { container } = render(
        <BodyViewer
          measurements={DEFAULT_MEASUREMENTS}
          gender="female"
          onGenderChange={vi.fn()}
          className="my-custom-class"
        />,
      );
      expect(container.firstElementChild?.className).toContain("my-custom-class");
    });
  });

  describe("unmount cleanup", () => {
    it("calls renderer.dispose() on unmount", async () => {
      const { unmount } = renderViewer();
      await waitFor(() =>
        expect(screen.queryByText(/loading body model/i)).toBeNull(),
      );
      unmount();
      expect(mockRendererDispose).toHaveBeenCalled();
    });

    it("calls controls.dispose() on unmount", async () => {
      const { unmount } = renderViewer();
      await waitFor(() =>
        expect(screen.queryByText(/loading body model/i)).toBeNull(),
      );
      unmount();
      expect(mockDispose).toHaveBeenCalled();
    });
  });
});
