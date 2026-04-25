"use client";

import React, { useState, useRef } from "react";
import type { CascadeScript } from "./CascadeScript";
import { useCascadeTimeline } from "./useCascadeTimeline";

interface CascadePlayerProps {
  script: CascadeScript;
  svgContent: string;
  onComplete?: () => void;
}

export function CascadePlayer({ script, svgContent, onComplete }: CascadePlayerProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = (msg: string) => {
    setError(msg);
    setIsPlaying(false);
  };

  const { play, pause, stepForward, stepBack } = useCascadeTimeline(
    script,
    setCurrentStepIndex,
    onComplete,
    handleError
  );

  const currentNarration = script.steps[currentStepIndex]?.narration ?? "";

  const handlePlay = () => {
    setIsPlaying(true);
    play();
  };

  const handlePause = () => {
    setIsPlaying(false);
    pause();
  };

  return (
    <div className="cascade-player">
      {error && (
        <div role="alert" className="cascade-player__error">
          {error}
        </div>
      )}

      <div
        className="cascade-player__svg"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: svgContent }}
      />

      <div className="cascade-player__narration" aria-live="polite">
        {currentNarration}
      </div>

      <div className="cascade-player__controls">
        <button
          type="button"
          aria-label="Step Back (Prev)"
          onClick={stepBack}
          disabled={currentStepIndex === 0}
        >
          ← Prev
        </button>

        {isPlaying ? (
          <button type="button" aria-label="Pause" onClick={handlePause}>
            Pause
          </button>
        ) : (
          <button type="button" aria-label="Play" onClick={handlePlay}>
            Play
          </button>
        )}

        <button
          type="button"
          aria-label="Step Forward (Next)"
          onClick={stepForward}
          disabled={currentStepIndex >= script.steps.length - 1}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
