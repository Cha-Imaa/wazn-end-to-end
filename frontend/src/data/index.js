import { normalizeArabic } from "../utils/normalizeArabic.js";

import { landingExamples } from "./landingExamples.js";
import { words } from "./words.js";
import { trees } from "./trees.js";
import { quizzes } from "./quizzes.js";

function getByNormalizedKey(collection, value) {
  const normalizedValue = normalizeArabic(value);

  return Object.values(collection).find((item) => {
    const itemKey = item?.plain || item?.originWord || "";
    return normalizeArabic(itemKey) === normalizedValue;
  });
}

export function getWordData(value) {
  return getByNormalizedKey(words, value);
}

export function getTreeData(value) {
  return getByNormalizedKey(trees, value);
}

export function getQuizData(value) {
  const normalizedValue = normalizeArabic(value);

  const matchingKey = Object.keys(quizzes).find(
    (key) => normalizeArabic(key) === normalizedValue
  );

  return matchingKey ? quizzes[matchingKey] : [];
}

export function getLearningData(value) {
  return {
    word: getWordData(value),
    tree: getTreeData(value),
    quiz: getQuizData(value),
  };
}

export function getLandingExampleData(examplePlainWord) {
  return getLearningData(examplePlainWord);
}

export { landingExamples, words, trees, quizzes };