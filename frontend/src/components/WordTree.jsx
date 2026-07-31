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

function formatRootArabic(rootLetters) {
  if (!rootLetters?.length) return "";
  return rootLetters.join(" · ");
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

function createSvgRect({ x, y, width, height, rx, className }) {
  const rectElement = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "rect"
  );

  rectElement.setAttribute("x", String(x));
  rectElement.setAttribute("y", String(y));
  rectElement.setAttribute("width", String(width));
  rectElement.setAttribute("height", String(height));
  rectElement.setAttribute("rx", String(rx));
  rectElement.setAttribute("class", className);

  return rectElement;
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

  const rootTextGroup = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "g"
  );

  rootTextGroup.setAttribute(
    "class",
    "tree-root-generated-text tree-root-label"
  );

  const arabicRoot = createSvgText({
    text: rootArabic,
    x: 745,
    y: 845,
    className: "tree-root-arabic",
    fontSize: 34,
    direction: "rtl",
  });

  rootTextGroup.appendChild(arabicRoot);

  if (displayTransliteration) {
    const transliteration = createSvgText({
      text: displayTransliteration,
      x: 745,
      y: 905,
      className: "tree-root-transliteration",
      fontSize: 25,
    });

    rootTextGroup.appendChild(transliteration);
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

  getOrderedSmallLeaves(svgElement).forEach((leaf, index) => {
    setAnimationTiming(
      leaf,
      timing.smallLeaves.delay + index * timing.smallLeaves.stagger,
      timing.smallLeaves.duration
    );
  });
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
    prepareTreeEntranceAnimation(svgElement);
  }
}

export default function WordTree({
  activeTree,
  selectedNode,
  onLeafClick,
  searchTerm = "",
  isQuizActive = false,
}) {
  const containerRef = useRef(null);
  const [svgMarkup, setSvgMarkup] = useState("");
  const [loadError, setLoadError] = useState(false);
  const [isTreeEntering, setIsTreeEntering] = useState(false);

  const hasTreeData = Boolean(activeTree?.leaves?.length);

  const treeKey = useMemo(() => {
    return activeTree?.trunk?.root_id || activeTree?.trunk?.arabic || "word-tree";
  }, [activeTree]);

  useEffect(() => {
    if (!hasTreeData) return;

    setIsTreeEntering(true);

    const timeoutId = window.setTimeout(() => {
      setIsTreeEntering(false);
    }, TREE_ENTRANCE_ANIMATION.totalDuration);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [treeKey, hasTreeData]);

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

  useEffect(() => {
    if (!svgMarkup || !containerRef.current || !hasTreeData) return;

    const frameId = requestAnimationFrame(() => {
      if (!containerRef.current) return;

      populateSvgTree({
        container: containerRef.current,
        activeTree,
        selectedNode,
        onLeafClick,
        shouldAnimate: isTreeEntering,
      });
    });

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [
    svgMarkup,
    activeTree,
    selectedNode,
    onLeafClick,
    hasTreeData,
    isTreeEntering,
  ]);

  if (!hasTreeData) {
    return (
      <div className="word-tree-empty word-tree-empty--unknown" role="status">
        <p className="word-tree-empty-title">This word has not bloomed yet</p>

        {searchTerm ? (
          <p className="word-tree-empty-copy">
            We could not grow a tree for{" "}
            <strong dir="auto">“{searchTerm}”</strong>.
          </p>
        ) : (
          <p className="word-tree-empty-copy">
            Search an Arabic word to grow its tree.
          </p>
        )}

        <p className="word-tree-empty-hint">
          Try another Arabic word, or check the spelling and diacritics.
        </p>
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
      dangerouslySetInnerHTML={{ __html: svgMarkup }}
    />
  );
}