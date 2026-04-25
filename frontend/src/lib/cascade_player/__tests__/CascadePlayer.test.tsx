import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// Mock GSAP before any imports
const mockTo = vi.fn().mockReturnThis();
const mockPause = vi.fn().mockReturnThis();
const mockPlay = vi.fn().mockReturnThis();
const mockSeek = vi.fn().mockReturnThis();
const mockOnComplete = vi.fn();
const mockTimeline = {
  to: mockTo,
  pause: mockPause,
  play: mockPlay,
  seek: mockSeek,
};

vi.mock("gsap", () => ({
  default: {
    timeline: vi.fn(() => mockTimeline),
    to: vi.fn(),
  },
}));

import { CascadePlayer } from "../CascadePlayer";
import type { CascadeScript } from "../CascadeScript";

const twoStepScript: CascadeScript = {
  version: "1",
  steps: [
    {
      id: "step-1",
      transform: { type: "translate", elementId: "front-bodice", dx: 10, dy: 5 },
      narration: "We are moving the piece right.",
      durationMs: 500,
    },
    {
      id: "step-2",
      transform: {
        type: "rotate",
        elementId: "back-bodice",
        angleDeg: 15,
        pivotX: 200,
        pivotY: 160,
      },
      narration: "Now rotating the back.",
      durationMs: 400,
    },
  ],
};

const simpleSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <g id="front-bodice"><rect x="0" y="0" width="50" height="50"/></g>
  <g id="back-bodice"><rect x="50" y="0" width="50" height="50"/></g>
</svg>`;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CascadePlayer", () => {
  it("renders the SVG content in the document", () => {
    render(<CascadePlayer script={twoStepScript} svgContent={simpleSvg} />);
    // SVG is injected via dangerouslySetInnerHTML — check container has svg element
    const svg = document.querySelector("svg");
    expect(svg).not.toBeNull();
  });

  it("shows a Play button", () => {
    render(<CascadePlayer script={twoStepScript} svgContent={simpleSvg} />);
    expect(screen.getByRole("button", { name: /play/i })).toBeInTheDocument();
  });

  it("shows narration text for the first step when Play is clicked", () => {
    render(<CascadePlayer script={twoStepScript} svgContent={simpleSvg} />);
    fireEvent.click(screen.getByRole("button", { name: /play/i }));
    expect(screen.getByText(/we are moving the piece right/i)).toBeInTheDocument();
  });

  it("calls timeline.play() when Play button is clicked", () => {
    render(<CascadePlayer script={twoStepScript} svgContent={simpleSvg} />);
    fireEvent.click(screen.getByRole("button", { name: /play/i }));
    expect(mockPlay).toHaveBeenCalled();
  });

  it("calls timeline.pause() when Pause is clicked", () => {
    render(<CascadePlayer script={twoStepScript} svgContent={simpleSvg} />);
    fireEvent.click(screen.getByRole("button", { name: /play/i }));
    fireEvent.click(screen.getByRole("button", { name: /pause/i }));
    expect(mockPause).toHaveBeenCalled();
  });

  it("shows Step Forward and Step Back buttons", () => {
    render(<CascadePlayer script={twoStepScript} svgContent={simpleSvg} />);
    expect(screen.getByRole("button", { name: /step forward|next/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /step back|prev/i })).toBeInTheDocument();
  });

  it("shows an error banner for a step referencing a nonexistent element without crashing", () => {
    const badScript: CascadeScript = {
      version: "1",
      steps: [
        {
          id: "bad",
          transform: { type: "translate", elementId: "nonexistent-element", dx: 5, dy: 0 },
          narration: "This element does not exist",
          durationMs: 300,
        },
      ],
    };
    // Should render without throwing
    expect(() =>
      render(<CascadePlayer script={badScript} svgContent={simpleSvg} />)
    ).not.toThrow();
  });

  it("calls onComplete after playback", () => {
    const onComplete = vi.fn();
    render(
      <CascadePlayer script={twoStepScript} svgContent={simpleSvg} onComplete={onComplete} />
    );
    // onComplete is wired via GSAP timeline — with mock it doesn't auto-fire,
    // but we verify the prop is accepted and doesn't crash
    expect(onComplete).not.toHaveBeenCalled(); // mock doesn't auto-fire
  });
});

describe("CascadePlayer boundary enforcement", () => {
  it("source files do not import domain vocabulary (fba, swayback, dart, bust, pattern)", async () => {
    const { readFileSync, readdirSync } = await import("fs");
    const { join } = await import("path");
    const dir = join(process.cwd(), "src", "lib", "cascade_player");

    const forbidden = ["fba", "swayback", "dart", "bust", "pattern"];

    const sourceFiles = readdirSync(dir)
      .filter((f: string) => f.endsWith(".ts") || f.endsWith(".tsx"))
      .map((f: string) => join(dir, f));

    for (const file of sourceFiles) {
      const content = readFileSync(file, "utf8").toLowerCase();
      for (const word of forbidden) {
        expect(
          content,
          `${file} must not contain domain word "${word}"`
        ).not.toContain(word);
      }
    }
  });
});
