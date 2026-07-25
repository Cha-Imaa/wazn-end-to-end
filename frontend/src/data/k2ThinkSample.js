// Fallback `k2_think`-shaped data for the K2 Think tab.
//
// The backend now returns a real `k2_think` object on every found word, so this
// is only a safety net when a result is missing it. It mirrors the contract in
// backend/app/services/k2_think_service.py (agents carry engine/model/reasoning/output).

export function getK2ThinkSample(word = "") {
  const w = word || "this word";
  const agent = (id, step, name, engine, summary, reasoning, output, model = null) => ({
    id, step, name, engine, model, status: "completed", summary, reasoning, output,
  });

  return {
    source: "deterministic",
    demo: true,
    subtitle: "See the reasoning behind every word.",
    agents: [
      agent(
        "lookup", 1, "Lookup Module", "deterministic",
        `Found ${w} in the verified knowledge base.`,
        `Normalized the query and searched the verified knowledge base.\nResolved it to a single word entry and collected its root family.`,
        `Word: ${w} · matched in the verified knowledge base`,
      ),
      agent(
        "morphology", 2, "Morphology Module", "deterministic",
        "Identified the root letters and morphological pattern.",
        `Split ${w} into letters and separated root letters from pattern letters.\nIdentified the morphological pattern (وزن).`,
        `Root letters + pattern identified`,
      ),
      agent(
        "explanation", 3, "Explanation Agent", "k2",
        "Generated a learner-friendly explanation using only verified data.",
        `Goal: explain ${w} to a beginner using only verified data.\nGrounded every claim in the verified root and pattern; invented no new Arabic.`,
        `${w} is explained from its verified root and pattern.`,
        "K2-Think-v2",
      ),
      agent(
        "quiz", 4, "Quiz Agent", "k2",
        "Created practice questions based on root, pattern, and meaning.",
        `Selected question templates and built one correct answer with plausible distractors.\nVerified each question has exactly one correct answer.`,
        `Practice questions generated`,
        "K2-Think-v2",
      ),
      agent(
        "guardrail", 5, "Guardrail Agent", "k2",
        "Validated root, pattern, meaning, and quiz answers. No unapproved content detected.",
        `Reviewed tutor and quiz output against the verified evidence.\nConfirmed no invented meanings, patterns, or words.`,
        "All checks passed",
        "K2-Think-v2",
      ),
      agent(
        "evaluation", 6, "Evaluation Agent", "k2",
        "Scored the response for quality and learning effectiveness.",
        `Scored groundedness, quiz validity, and clarity.\nWeighted groundedness most heavily.`,
        "Overall 94/100 · Groundedness 100% · Quiz 100% · Clarity 92%",
        "K2-Think-v2",
      ),
    ],
    evaluation: {
      overall: { value: 94, max: 100, stars: 4.5 },
      metrics: [
        { id: "groundedness", label: "Groundedness", percent: 100, rating: "Excellent" },
        { id: "quiz_validity", label: "Quiz Validity", percent: 100, rating: "Excellent" },
        { id: "clarity", label: "Clarity", percent: 92, rating: "Very Good" },
      ],
    },
    guardrails: {
      passed: true,
      summary: "All Checks Passed",
      checks: [
        { id: "verified_words", label: "Only verified words used", passed: true },
        { id: "root_pattern_matched", label: "Root & pattern matched", passed: true },
        { id: "meanings_verified", label: "Meanings from verified KB", passed: true },
        { id: "quiz_one_answer", label: "Quiz has one correct answer", passed: true },
      ],
    },
    fallback_note:
      "If any step fails, WAZN falls back to deterministic template explanations.",
  };
}
