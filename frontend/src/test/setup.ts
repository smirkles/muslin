import "@testing-library/jest-dom";

// jsdom does not implement PointerEvent — polyfill with MouseEvent so tests
// that dispatch pointer events work without a real browser.
if (typeof PointerEvent === "undefined") {
  (global as unknown as Record<string, unknown>).PointerEvent = class PointerEvent extends MouseEvent {
    constructor(type: string, params?: PointerEventInit) {
      super(type, params);
    }
  };
}
