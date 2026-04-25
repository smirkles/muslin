"use client";

import { useRef, useCallback } from "react";
import gsap from "gsap";
import type { CascadeScript } from "./CascadeScript";

export interface TimelineControls {
  play: () => void;
  pause: () => void;
  stepForward: () => void;
  stepBack: () => void;
  currentStep: number;
  isPlaying: boolean;
}

export function useCascadeTimeline(
  script: CascadeScript,
  onStepChange: (stepIndex: number) => void,
  onComplete?: () => void,
  onError?: (message: string) => void
) {
  const timelineRef = useRef<gsap.core.Timeline | null>(null);
  const currentStepRef = useRef(0);
  const isPlayingRef = useRef(false);
  // step start times in seconds for seek
  const stepTimesRef = useRef<number[]>([]);

  const buildTimeline = useCallback(() => {
    const tl = gsap.timeline({ paused: true });
    let time = 0;
    const times: number[] = [];

    for (const step of script.steps) {
      times.push(time);
      const { transform } = step;
      const el = document.getElementById(transform.elementId);
      if (!el) {
        onError?.(`Element not found: ${transform.elementId}`);
        return null;
      }

      const duration = step.durationMs / 1000;

      if (transform.type === "translate") {
        tl.to(el, { x: transform.dx, y: transform.dy, duration }, time);
      } else if (transform.type === "rotate") {
        tl.to(
          el,
          {
            rotation: transform.angleDeg,
            transformOrigin: `${transform.pivotX} ${transform.pivotY}`,
            duration,
          },
          time
        );
      } else if (transform.type === "scale") {
        tl.to(
          el,
          {
            scaleX: transform.sx,
            scaleY: transform.sy,
            transformOrigin: `${transform.originX} ${transform.originY}`,
            duration,
          },
          time
        );
      }

      time += duration;
    }

    if (onComplete) {
      tl.call(onComplete);
    }

    stepTimesRef.current = times;
    return tl;
  }, [script, onComplete, onError]);

  const ensureTimeline = useCallback(() => {
    if (!timelineRef.current) {
      timelineRef.current = buildTimeline();
    }
    return timelineRef.current;
  }, [buildTimeline]);

  const play = useCallback(() => {
    const tl = ensureTimeline();
    if (!tl) return;
    isPlayingRef.current = true;
    onStepChange(currentStepRef.current);
    tl.play();
  }, [ensureTimeline, onStepChange]);

  const pause = useCallback(() => {
    const tl = ensureTimeline();
    if (!tl) return;
    isPlayingRef.current = false;
    tl.pause();
  }, [ensureTimeline]);

  const stepForward = useCallback(() => {
    const tl = ensureTimeline();
    if (!tl) return;
    tl.pause();
    const next = Math.min(currentStepRef.current + 1, script.steps.length - 1);
    currentStepRef.current = next;
    onStepChange(next);
    tl.seek(stepTimesRef.current[next] ?? 0);
  }, [ensureTimeline, script.steps.length, onStepChange]);

  const stepBack = useCallback(() => {
    const tl = ensureTimeline();
    if (!tl) return;
    tl.pause();
    const prev = Math.max(currentStepRef.current - 1, 0);
    currentStepRef.current = prev;
    onStepChange(prev);
    tl.seek(stepTimesRef.current[prev] ?? 0);
  }, [ensureTimeline, onStepChange]);

  return { play, pause, stepForward, stepBack };
}
