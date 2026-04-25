"use client";

import { z } from "zod";

export class ScriptValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ScriptValidationError";
  }
}

const TransformStepSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("translate"),
    elementId: z.string(),
    dx: z.number(),
    dy: z.number(),
  }),
  z.object({
    type: z.literal("rotate"),
    elementId: z.string(),
    angleDeg: z.number(),
    pivotX: z.number(),
    pivotY: z.number(),
  }),
  z.object({
    type: z.literal("scale"),
    elementId: z.string(),
    sx: z.number(),
    sy: z.number(),
    originX: z.number(),
    originY: z.number(),
  }),
]);

const CascadeStepSchema = z.object({
  id: z.string(),
  transform: TransformStepSchema,
  narration: z.string(),
  durationMs: z.number(),
});

const CascadeScriptSchema = z.object({
  version: z.literal("1"),
  steps: z.array(CascadeStepSchema),
});

export type TransformStep = z.infer<typeof TransformStepSchema>;
export type CascadeStep = z.infer<typeof CascadeStepSchema>;
export type CascadeScript = z.infer<typeof CascadeScriptSchema>;

export function parseCascadeScript(json: unknown): CascadeScript {
  const result = CascadeScriptSchema.safeParse(json);
  if (!result.success) {
    throw new ScriptValidationError(
      `Invalid cascade script: ${result.error.message}`
    );
  }
  return result.data;
}
