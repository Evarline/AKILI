import '@testing-library/jest-dom/vitest'

/**
 * jsdom does not implement `Element.scrollIntoView`. The transcript uses it to
 * keep the newest turn in view, so it is stubbed here rather than guarded in
 * the component — the browser has it, and the component should not carry a
 * branch for a test environment.
 */
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {
    /* no layout in jsdom */
  }
}
