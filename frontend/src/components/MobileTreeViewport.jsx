import { useRef, useState } from "react";

// Phone-only pan/pinch-zoom wrapper around the word tree. On desktop it is a
// transparent pass-through: gestures are ignored above the phone breakpoint
// and the canvas renders untransformed. State lives here so the viewport
// survives view switches — the tree stays mounted, only hidden by CSS.

const MIN_SCALE = 1;
const MAX_SCALE = 2.75;
const DRAG_SUPPRESS_CLICK_PX = 8;

function isPhoneViewport() {
  // Must mirror the phone media condition in 22-learning-companion-refinements.css.
  return window.matchMedia(
    "(max-width: 520px), (max-height: 500px) and (pointer: coarse)"
  ).matches;
}

function clampView(next) {
  const scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, next.scale));

  // The canvas scales about its centre, so the content edge travels
  // (scale - 1) * size / 2 in each direction. Panning past that would
  // push the tree fully off-screen.
  const maxX = ((scale - 1) * next.width) / 2;
  const maxY = ((scale - 1) * next.height) / 2;

  return {
    scale,
    x: Math.min(maxX, Math.max(-maxX, next.x)),
    y: Math.min(maxY, Math.max(-maxY, next.y)),
  };
}

export default function MobileTreeViewport({ children }) {
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });

  const viewportRef = useRef(null);
  const pointersRef = useRef(new Map());
  const gestureRef = useRef(null);
  const movedRef = useRef(0);

  const isTransformed = view.scale !== 1 || view.x !== 0 || view.y !== 0;

  function beginGesture() {
    const pointers = [...pointersRef.current.values()];
    const rect = viewportRef.current?.getBoundingClientRect();

    if (!rect || !pointers.length) {
      gestureRef.current = null;
      return;
    }

    if (pointers.length >= 2) {
      const [a, b] = pointers;
      gestureRef.current = {
        kind: "pinch",
        startDistance: Math.hypot(a.x - b.x, a.y - b.y) || 1,
        startView: view,
        rect,
      };
    } else {
      gestureRef.current = {
        kind: "pan",
        startX: pointers[0].x,
        startY: pointers[0].y,
        startView: view,
        rect,
      };
    }
  }

  function handlePointerDown(event) {
    if (!isPhoneViewport()) {
      return;
    }

    pointersRef.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });
    movedRef.current = 0;
    beginGesture();
  }

  function handlePointerMove(event) {
    const tracked = pointersRef.current.get(event.pointerId);
    const gesture = gestureRef.current;

    if (!tracked || !gesture) {
      return;
    }

    movedRef.current = Math.max(
      movedRef.current,
      Math.hypot(event.clientX - tracked.x, event.clientY - tracked.y)
    );

    pointersRef.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });

    const pointers = [...pointersRef.current.values()];
    const { rect, startView } = gesture;

    if (gesture.kind === "pinch" && pointers.length >= 2) {
      const [a, b] = pointers;
      const distance = Math.hypot(a.x - b.x, a.y - b.y) || 1;
      const scale = startView.scale * (distance / gesture.startDistance);

      setView(
        clampView({
          scale,
          x: startView.x,
          y: startView.y,
          width: rect.width,
          height: rect.height,
        })
      );
    } else if (gesture.kind === "pan" && startView.scale > 1) {
      setView(
        clampView({
          scale: startView.scale,
          x: startView.x + (event.clientX - gesture.startX),
          y: startView.y + (event.clientY - gesture.startY),
          width: rect.width,
          height: rect.height,
        })
      );
    }
  }

  function handlePointerEnd(event) {
    if (!pointersRef.current.has(event.pointerId)) {
      return;
    }

    pointersRef.current.delete(event.pointerId);

    if (pointersRef.current.size > 0) {
      beginGesture();
    } else {
      gestureRef.current = null;
    }
  }

  function handleClickCapture(event) {
    // A drag or pinch must not fall through as a leaf tap.
    if (movedRef.current > DRAG_SUPPRESS_CLICK_PX) {
      event.preventDefault();
      event.stopPropagation();
      movedRef.current = 0;
    }
  }

  function handleReset() {
    setView({ scale: 1, x: 0, y: 0 });
  }

  return (
    <div
      ref={viewportRef}
      className="mobile-tree-viewport"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onClickCapture={handleClickCapture}
    >
      <div
        className="mobile-tree-canvas"
        style={
          isTransformed
            ? {
                transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
              }
            : undefined
        }
      >
        {children}
      </div>

      {isTransformed && (
        <button
          type="button"
          className="mobile-tree-reset"
          onClick={handleReset}
          aria-label="Reset tree view"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M4.5 10a8 8 0 1 1-.4 5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.9"
              strokeLinecap="round"
            />
            <path d="M4 5.5V10h4.5" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="mobile-tree-reset-label">Reset</span>
        </button>
      )}
    </div>
  );
}
