import { BIG_LEAF_COUNT } from "./treeConstants.js";

export function createSvgElement(tagName) {
  return document.createElementNS("http://www.w3.org/2000/svg", tagName);
}

export function getBBoxSafe(element) {
  try {
    return element.getBBox();
  } catch {
    return null;
  }
}

export function getLeafNumber(index) {
  return String(index).padStart(2, "0");
}

export function hideElement(element) {
  if (!element) {
    return;
  }

  element.setAttribute("display", "none");
  element.setAttribute("aria-hidden", "true");
  element.style.display = "none";
}

export function hideDefaultSvgLabels(svgRoot) {
  for (let index = 1; index <= BIG_LEAF_COUNT; index += 1) {
    const leafNumber = getLeafNumber(index);

    hideElement(svgRoot.querySelector(`#BigLeafWord_${leafNumber}`));
    hideElement(svgRoot.querySelector(`#BigLeafMeaning_${leafNumber}`));
  }

  hideElement(svgRoot.querySelector("#RootArabic"));
  hideElement(svgRoot.querySelector("#RootTransliteration"));
}

export function sanitizeSvgMarkup(markup) {
  const parser = new DOMParser();
  const document = parser.parseFromString(markup, "image/svg+xml");
  const svgElement = document.querySelector("svg");

  if (!svgElement) {
    return markup;
  }

  hideDefaultSvgLabels(svgElement);

  return new XMLSerializer().serializeToString(svgElement);
}

export function removeExistingGeneratedText(group) {
  group
    .querySelectorAll(".word-tree-generated-text")
    .forEach((element) => element.remove());
}

export function removeExistingRootText(svgElement) {
  svgElement
    .querySelectorAll(".tree-root-generated-text")
    .forEach((element) => element.remove());
}

export function getAllSmallLeafGroups(svgElement) {
  return Array.from(svgElement.querySelectorAll('[id^="SmallLeaf_"]'));
}

export function getDrawableParts(element) {
  if (!element) {
    return [];
  }

  if (typeof element.getTotalLength === "function") {
    return [element];
  }

  const parts = Array.from(
    element.querySelectorAll("path, line, polyline, polygon")
  );

  return parts.length ? parts : [element];
}