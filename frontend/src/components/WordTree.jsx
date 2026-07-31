import { useEffect, useMemo, useRef, useState } from "react";
import {
  BIG_LEAF_COUNT,
  TREE_ENTRANCE_ANIMATION,
} from "./word-tree/treeConstants.js";

const SVG_PATH = "/assets/tree/wazn-tree.svg";

function getLeafNumber(index) {
  return String(index).padStart(2, "0");
}

function queryLeafElement(svgElement, baseId, leafNumber, index) {
  return (
    svgElement.querySelector(`#${baseId}_${leafNumber}`) ||
    svgElement.querySelector(`#${baseId}_${index}`)
  );
}

function normalizeText(value = "") {
  return String(value)
    .trim()
    .replace(/[ًٌٍَُِّْٰـ]/g, "")
    .toLowerCase();
}

function createSvgText({
  text,
  x,
  y,
  className,
  fontSize,
  direction = "ltr",
}) {
  const textElement = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "text"
  );

  textElement.textContent = text || "";
  textElement.setAttribute("class", className);
  textElement.setAttribute("x", String(x));
  textElement.setAttribute("y", String(y));
  textElement.setAttribute("text-anchor", "middle");
  textElement.setAttribute("dominant-baseline", "middle");
  textElement.setAttribute("font-size", String(fontSize));

  if (direction === "rtl") {
    textElement.setAttribute("lang", "ar");
    textElement.setAttribute("direction", "rtl");
    textElement.setAttribute("unicode-bidi", "plaintext");
  }

  return textElement;
}

function getBBoxSafe(element) {
  try {
    return element?.getBBox?.() || null;
  } catch {
    return null;
  }
}

function prepareSvg(svgElement) {
  svgElement.removeAttribute("width");
  svgElement.removeAttribute("height");

  svgElement.classList.add("word-tree-svg");
  svgElement.setAttribute("role", "img");
  svgElement.setAttribute("aria-label", "Arabic word family tree");
  svgElement.setAttribute("preserveAspectRatio", "xMidYMid meet");

  // Important:
  // Do not override the Figma viewBox.
  // The ground depends on the original SVG dimensions.
}

function clearGeneratedText(svgElement) {
  svgElement
    .querySelectorAll(".word-tree-generated-text, .tree-root-generated-text")
    .forEach((element) => element.remove());
}

function hideFigmaLeafText(contentGroup, leafNumber) {
  Array.from(contentGroup.children).forEach((child) => {
    const childId = child.getAttribute("id") || "";

    const shouldKeep =
      childId === `BigLeafDivider_${leafNumber}` ||
      child.classList.contains("word-tree-generated-text");

    if (!shouldKeep) {
      child.style.display = "none";
    }
  });
}

function hideFigmaRootLabels(svgElement) {
  const rootLabelGroup =
    svgElement.querySelector("#TreeRootLabel") ||
    svgElement.querySelector("#TreeRoot_Label") ||
    svgElement.querySelector("#RootLabel") ||
    svgElement.querySelector("#Root_Text") ||
    svgElement.querySelector("#TreeBase");

  if (!rootLabelGroup) return;

  Array.from(rootLabelGroup.children).forEach((child) => {
    if (!child.classList.contains("tree-root-generated-text")) {
      child.style.display = "none";
    }
  });
}

function getLeafTextPosition(contentGroup, leafNumber) {
  const divider = contentGroup.querySelector(`#BigLeafDivider_${leafNumber}`);
  const dividerBox = getBBoxSafe(divider);
  const contentBox = getBBoxSafe(contentGroup);

  if (dividerBox) {
    return {
      x: dividerBox.x + dividerBox.width / 2,
      dividerY: dividerBox.y + dividerBox.height / 2,
    };
  }

  if (contentBox) {
    return {
      x: contentBox.x + contentBox.width / 2,
      dividerY: contentBox.y + contentBox.height / 2,
    };
  }

  return {
    x: 720,
    dividerY: 512,
  };
}

function populateLeafText({ contentGroup, leafNumber, node }) {
  hideFigmaLeafText(contentGroup, leafNumber);

  contentGroup
    .querySelectorAll(".word-tree-generated-text")
    .forEach((element) => element.remove());

  const { x, dividerY } = getLeafTextPosition(contentGroup, leafNumber);

  const arabicText = createSvgText({
    text: node.arabic || "",
    x,
    y: dividerY - 35,
    className: "word-tree-generated-text big-leaf-word",
    fontSize: 50,
    direction: "rtl",
  });

  const englishText = createSvgText({
    text: node.short_meaning || node.meaning || "",
    x,
    y: dividerY + 24,
    className: "word-tree-generated-text big-leaf-meaning",
    fontSize: 23,
  });

  contentGroup.appendChild(arabicText);
  contentGroup.appendChild(englishText);
}

// The Figma artwork carries the intended root-label placement as two hidden
// paths inside #TreeRootLabel. Their boxes are the anchor — the same idea as
// leaf text deriving its position from the leaf divider. getBBox returns
// zeros while an element is display:none, so lift the hiding for the read.
function probeHiddenBBox(element) {
  if (!element) return null;

  const previousDisplay = element.style.display;
  element.style.display = "";
  const box = getBBoxSafe(element);
  element.style.display = previousDisplay;

  return box && box.width > 0 ? box : null;
}

function getRootLabelAnchor(svgElement) {
  const arabicBox = probeHiddenBBox(svgElement.querySelector("#RootArabic"));
  const translitBox = probeHiddenBBox(
    svgElement.querySelector("#RootTransliteration")
  );

  if (arabicBox) {
    const arabicY = arabicBox.y + arabicBox.height / 2;

    return {
      x: arabicBox.x + arabicBox.width / 2,
      arabicY,
      translitY: translitBox
        ? translitBox.y + translitBox.height / 2
        : arabicY + 52,
    };
  }

  const trunkBox = getBBoxSafe(
    svgElement.querySelector("#TrunkAndMainBranches")
  );

  if (trunkBox) {
    return {
      x: trunkBox.x + trunkBox.width / 2,
      arabicY: trunkBox.y + trunkBox.height * 0.72,
      translitY: trunkBox.y + trunkBox.height * 0.79,
    };
  }

  return { x: 745, arabicY: 817, translitY: 869 };
}

function addRootText(svgElement, activeTree) {
  const rootArabic = activeTree?.trunk?.arabic || "";
  const rootTransliteration = activeTree?.trunk?.transliteration || "";
  const displayTransliteration = rootTransliteration.replaceAll("-", " · ");

  const rootLabelGroup =
    svgElement.querySelector("#TreeRootLabel") ||
    svgElement.querySelector("#TreeRoot_Label") ||
    svgElement.querySelector("#RootLabel") ||
    svgElement.querySelector("#Root_Text") ||
    svgElement.querySelector("#TreeBase") ||
    svgElement;

  hideFigmaRootLabels(svgElement);

  if (!rootArabic) return;

  const anchor = getRootLabelAnchor(svgElement);

  const rootTextGroup = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "g"
  );

  rootTextGroup.setAttribute(
    "class",
    "tree-root-generated-text tree-root-label"
  );

  rootTextGroup.appendChild(
    createSvgText({
      text: rootArabic,
      x: anchor.x,
      y: anchor.arabicY,
      className: "tree-root-arabic",
      fontSize: 48,
      direction: "rtl",
    })
  );

  if (displayTransliteration) {
    rootTextGroup.appendChild(
      createSvgText({
        text: displayTransliteration,
        x: anchor.x,
        y: anchor.translitY + 6,
        className: "tree-root-transliteration",
        fontSize: 22,
      })
    );
  }

  rootLabelGroup.appendChild(rootTextGroup);
}

function ensureLeafLift(leafGroup, shapeElement, contentGroup) {
  if (!shapeElement || !contentGroup) return;

  // Idempotent: populateSvgTree re-runs on the same DOM (e.g. selection change).
  if (shapeElement.parentNode?.classList?.contains("big-leaf-lift")) return;
  if (shapeElement.parentNode !== leafGroup) return;

  const lift = document.createElementNS("http://www.w3.org/2000/svg", "g");
  lift.setAttribute("class", "big-leaf-lift");

  // The branch connector (and hit area) stay outside the wrapper so they
  // never move on hover — only the leaf shape and its text lift.
  leafGroup.insertBefore(lift, shapeElement);
  lift.appendChild(shapeElement);
  lift.appendChild(contentGroup);
}

function setupLeafInteraction({
  leafGroup,
  hitArea,
  node,
  selectedNode,
  onLeafClick,
}) {
  const isSelected =
    normalizeText(selectedNode?.id) === normalizeText(node.id) ||
    normalizeText(selectedNode?.arabic) === normalizeText(node.arabic);

  leafGroup.classList.add("big-leaf-node");
  leafGroup.classList.toggle("big-leaf-node--selected", isSelected);
  leafGroup.classList.remove("big-leaf-node--hidden");

  leafGroup.setAttribute("role", "button");
  leafGroup.setAttribute("tabindex", "0");
  leafGroup.setAttribute("aria-pressed", isSelected ? "true" : "false");
  leafGroup.setAttribute(
    "aria-label",
    `Open details for ${node.arabic || ""}, ${
      node.short_meaning || node.meaning || ""
    }`
  );

  if (hitArea) {
    hitArea.classList.add("big-leaf-hit-area");
    hitArea.setAttribute("pointer-events", "all");
    hitArea.style.cursor = "pointer";
  }

  leafGroup.onclick = (event) => {
    event.stopPropagation();
    onLeafClick?.(node);
  };

  leafGroup.onkeydown = (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;

    event.preventDefault();
    onLeafClick?.(node);
  };
}

function hideUnusedLeaf(leafGroup) {
  if (!leafGroup) return;

  leafGroup.classList.add("big-leaf-node--hidden");
  leafGroup.setAttribute("aria-hidden", "true");
  leafGroup.removeAttribute("role");
  leafGroup.removeAttribute("tabindex");
  leafGroup.onclick = null;
  leafGroup.onkeydown = null;
}

function parseNumberedId(id = "", prefix = "") {
  const match = id.match(new RegExp(`^${prefix}_(\\d+)(?:_(\\d+))?$`));

  if (!match) {
    return null;
  }

  return {
    primary: Number(match[1]),
    secondary: Number(match[2] || 0),
  };
}

function getOrderedSmallLeaves(svgElement) {
  return Array.from(svgElement.querySelectorAll('[id^="SmallLeaf_"]')).sort(
    (a, b) => {
      const aOrder = parseNumberedId(a.id, "SmallLeaf");
      const bOrder = parseNumberedId(b.id, "SmallLeaf");

      if (!aOrder || !bOrder) {
        return a.id.localeCompare(b.id);
      }

      if (aOrder.primary !== bOrder.primary) {
        return aOrder.primary - bOrder.primary;
      }

      return aOrder.secondary - bOrder.secondary;
    }
  );
}

function setAnimationTiming(element, delay, duration) {
  if (!element) return;

  element.style.setProperty("--tree-animation-delay", `${delay}ms`);
  element.style.setProperty("--tree-animation-duration", `${duration}ms`);
}

function prepareTreeEntranceAnimation(svgElement) {
  const timing = TREE_ENTRANCE_ANIMATION;

  svgElement.classList.add("word-tree-svg--entrance");

  setAnimationTiming(
    svgElement.querySelector("#Ground"),
    timing.ground.delay,
    timing.ground.duration
  );

  setAnimationTiming(
    svgElement.querySelector("#TrunkAndMainBranches"),
    timing.trunk.delay,
    timing.trunk.duration
  );

  svgElement.querySelectorAll(".tree-root-generated-text").forEach((element) => {
    setAnimationTiming(element, timing.rootText.delay, timing.rootText.duration);
  });

  const orderedSmallLeaves = getOrderedSmallLeaves(svgElement);

  const smallLeavesFinishTime =
    timing.smallLeaves.delay +
    Math.max(0, orderedSmallLeaves.length - 1) * timing.smallLeaves.stagger +
    timing.smallLeaves.duration;

  const bigLeavesStartTime =
    smallLeavesFinishTime + timing.bigLeaves.delayAfterSmallLeaves;

  for (let index = 1; index <= BIG_LEAF_COUNT; index += 1) {
    const leafNumber = getLeafNumber(index);

    const branch = queryLeafElement(
      svgElement,
      "BigLeafBranch",
      leafNumber,
      index
    );

    setAnimationTiming(
      branch,
      timing.branches.delay,
      timing.branches.duration
    );

    const bigLeaf = queryLeafElement(svgElement, "BigLeaf", leafNumber, index);

    setAnimationTiming(
      bigLeaf,
      bigLeavesStartTime + (index - 1) * timing.bigLeaves.stagger,
      timing.bigLeaves.duration
    );
  }

  orderedSmallLeaves.forEach((leaf, index) => {
    setAnimationTiming(
      leaf,
      timing.smallLeaves.delay + index * timing.smallLeaves.stagger,
      timing.smallLeaves.duration
    );
  });

  // The big leaves are the last track to finish. Report when the whole
  // timeline ends so the caller can release the entering state only after
  // every animation has reached its final keyframe — removing the class
  // earlier cancels in-flight animations and makes the leaves snap.
  return (
    bigLeavesStartTime +
    (BIG_LEAF_COUNT - 1) * timing.bigLeaves.stagger +
    timing.bigLeaves.duration
  );
}

function populateSvgTree({
  container,
  activeTree,
  selectedNode,
  onLeafClick,
  shouldAnimate,
}) {
  const svgElement = container.querySelector("svg");
  if (!svgElement) return;

  prepareSvg(svgElement);
  clearGeneratedText(svgElement);

  for (let index = 1; index <= BIG_LEAF_COUNT; index += 1) {
    const leafNumber = getLeafNumber(index);
    const node = activeTree?.leaves?.[index - 1];

    const leafGroup = queryLeafElement(svgElement, "BigLeaf", leafNumber, index);
    const contentGroup = queryLeafElement(
      svgElement,
      "BigLeafContent",
      leafNumber,
      index
    );
    const hitArea = queryLeafElement(
      svgElement,
      "BigLeafHitArea",
      leafNumber,
      index
    );
    const shapeElement = queryLeafElement(
      svgElement,
      "BigLeafShape",
      leafNumber,
      index
    );

    if (!leafGroup) continue;

    if (!node || !contentGroup) {
      hideUnusedLeaf(leafGroup);
      continue;
    }

    ensureLeafLift(leafGroup, shapeElement, contentGroup);

    leafGroup.style.visibility = "visible";
    leafGroup.style.opacity = "1";
    leafGroup.removeAttribute("aria-hidden");

    populateLeafText({
      contentGroup,
      leafNumber,
      node,
    });

    setupLeafInteraction({
      leafGroup,
      hitArea,
      node,
      selectedNode,
      onLeafClick,
    });
  }

  addRootText(svgElement, activeTree);

  if (shouldAnimate) {
    return prepareTreeEntranceAnimation(svgElement);
  }

  return null;
}

function EmptyStateArrowIcon() {
  return (
    <svg
      className="word-tree-empty-button-icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 3.5L10.5 8L6 12.5" />
    </svg>
  );
}

function EmptyStateLeafIcon() {
  return (
    <svg
      className="word-tree-empty-button-icon"
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M13.5 2.5c-5.6.3-9.4 2.4-10.6 6-.6 1.9-.2 3.7.4 4.8l.9-.5c1.3-2.9 3.4-5 6.3-6.4-2.3 2-4 4.3-4.9 6.9 1.2.4 2.9.5 4.4-.3 2.9-1.5 4-5.6 3.5-10.5z" />
    </svg>
  );
}

export default function WordTree({
  activeTree,
  selectedNode,
  onLeafClick,
  searchTerm = "",
  isQuizActive = false,
  notFoundReason = "",
  onTryAnotherWord,
}) {
  const containerRef = useRef(null);
  const [svgMarkup, setSvgMarkup] = useState("");
  const [loadError, setLoadError] = useState(false);

  const hasTreeData = Boolean(activeTree?.leaves?.length);

  const treeKey = useMemo(() => {
    return activeTree?.trunk?.root_id || activeTree?.trunk?.arabic || "word-tree";
  }, [activeTree]);

  // React decides whether to re-apply dangerouslySetInnerHTML by comparing
  // this object between renders. It must stay referentially stable: a fresh
  // `{ __html }` literal on every render makes React re-set the innerHTML on
  // any re-render of the container (e.g. the entering→ready class swap),
  // which wipes everything populateSvgTree wrote into the SVG.
  const svgHtml = useMemo(() => ({ __html: svgMarkup }), [svgMarkup]);

  const [isTreeEntering, setIsTreeEntering] = useState(hasTreeData);
  const [enteringTreeKey, setEnteringTreeKey] = useState(treeKey);

  // Restart the entrance animation when a different tree arrives, adjusting
  // state during render instead of in an effect.
  if (enteringTreeKey !== treeKey) {
    setEnteringTreeKey(treeKey);

    if (hasTreeData) {
      setIsTreeEntering(true);
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function loadSvg() {
      try {
        const response = await fetch(SVG_PATH);

        if (!response.ok) {
          throw new Error("Could not load SVG tree.");
        }

        const markup = await response.text();

        if (!isMounted) return;

        setSvgMarkup(markup);
        setLoadError(false);
      } catch {
        if (!isMounted) return;

        setLoadError(true);
      }
    }

    loadSvg();

    return () => {
      isMounted = false;
    };
  }, []);

  // Which tree the SVG was last populated (and animated) for. Deciding
  // "should this run animate" from this ref instead of isTreeEntering keeps
  // the entering→ready flip out of the populate effect's dependencies: the
  // flip must only swap the container class. Re-running the populate pass at
  // that moment forces layout and churns the SVG DOM, which interrupts an
  // in-flight hover transition and makes the hovered leaf visibly dip.
  const animatedTreeKeyRef = useRef(null);

  // Absolute time at which the current entrance ends. Kept in a ref so a
  // mid-entrance re-run of the populate effect (whose cleanup clears the
  // pending timeout) can reschedule the remaining wait instead of losing it.
  const entranceDeadlineRef = useRef(null);

  useEffect(() => {
    if (!svgMarkup || !containerRef.current || !hasTreeData) return;

    let entranceTimeoutId = null;

    const frameId = requestAnimationFrame(() => {
      if (!containerRef.current) return;

      const shouldAnimate = animatedTreeKeyRef.current !== treeKey;
      animatedTreeKeyRef.current = treeKey;

      const entranceEndTime = populateSvgTree({
        container: containerRef.current,
        activeTree,
        selectedNode,
        onLeafClick,
        shouldAnimate,
      });

      // Release the entering state only once the slowest animation track is
      // done; ending it early cancels in-flight animations and the tree jumps.
      if (entranceEndTime != null) {
        entranceDeadlineRef.current =
          performance.now() +
          entranceEndTime +
          TREE_ENTRANCE_ANIMATION.totalDurationBuffer;
      }

      if (entranceDeadlineRef.current != null) {
        const remaining = Math.max(
          0,
          entranceDeadlineRef.current - performance.now()
        );

        entranceTimeoutId = window.setTimeout(() => {
          entranceDeadlineRef.current = null;
          setIsTreeEntering(false);
        }, remaining);
      }
    });

    return () => {
      cancelAnimationFrame(frameId);

      if (entranceTimeoutId !== null) {
        window.clearTimeout(entranceTimeoutId);
      }
    };
  }, [
    svgMarkup,
    activeTree,
    selectedNode,
    onLeafClick,
    hasTreeData,
    treeKey,
  ]);

  if (!hasTreeData) {
    // A dead backend is not an unknown word — telling users their word
    // doesn't exist when the server is down teaches them a falsehood.
    if (notFoundReason === "backend_error") {
      return (
        <div className="word-tree-empty word-tree-empty--offline" role="status">
          <p className="word-tree-empty-title">We can’t reach the Wazn server</p>

          <p className="word-tree-empty-copy">
            Your word wasn’t the problem — the connection failed before we
            could look it up.
          </p>

          <p className="word-tree-empty-hint">
            Check that you’re online, then search again.
          </p>
        </div>
      );
    }

    return (
      <div className="word-tree-empty word-tree-empty--unknown" role="status">
        <div className="word-tree-empty-body">
          <img
            className="word-tree-empty-illustration"
            src="/assets/decor/young-flower.png"
            alt=""
            aria-hidden="true"
          />

          <p className="word-tree-empty-title">
            We couldn’t grow this word yet
          </p>

          <div className="word-tree-empty-divider" aria-hidden="true" />

          {searchTerm && (
            <p className="word-tree-empty-word" lang="ar" dir="rtl">
              {searchTerm}
            </p>
          )}

          <p className="word-tree-empty-copy">
            <EmptyStateLeafIcon />
            We couldn’t find it in WAZN — check the spelling and diacritics.
          </p>

          <div className="word-tree-empty-actions">
            <button
              type="button"
              className="word-tree-empty-button word-tree-empty-button--filled"
              onClick={onTryAnotherWord}
            >
              Try another word
              <EmptyStateArrowIcon />
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="word-tree-fallback" role="status">
        SVG tree could not be loaded.
      </div>
    );
  }

  return (
    <div
      key={treeKey}
      ref={containerRef}
      className={`word-tree ${
        isQuizActive ? "word-tree--quiz-active" : ""
      } ${isTreeEntering ? "word-tree--entering" : "word-tree--ready"}`}
      dangerouslySetInnerHTML={svgHtml}
    />
  );
}