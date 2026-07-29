from typing import Any

from app.modules.lookup_module import run_lookup_module
from app.modules.morphology_reasoning_module import (
    build_morphology_output,
    run_morphology_reasoning_module,
)
from app.services.leaf_details_service import build_leaf_details_for_tree
from app.services.quiz_service import build_quiz_for_word
from app.services.tree_service import build_tree_response


def build_base_state(word: str) -> dict[str, Any]:
    lookup_result = run_lookup_module(word)

    if not lookup_result.get("found"):
        return {
            "found": False,
            "query": lookup_result.get("query", word),
            "normalized_query": lookup_result.get("normalized_query", ""),
            "reason": lookup_result.get("reason", "word_not_found"),
            "message": lookup_result.get(
                "message",
                "Word not found in the knowledge base.",
            ),
            "pipeline_trace": lookup_result.get("pipeline_trace", {}),
        }

    selected_word = lookup_result["selected_word"]
    selected_word_id = lookup_result["selected_word_id"]
    root = lookup_result["root"]
    pattern = lookup_result.get("pattern")

    morphology_result = run_morphology_reasoning_module(
        selected_word=selected_word,
        root=root,
        pattern=pattern,
    )

    tree = build_tree_response(
        selected_word=selected_word,
        root=root,
    )

    leaf_details = build_leaf_details_for_tree(
        tree=tree,
        root=root,
    )

    selected_leaf = leaf_details.get(selected_word_id)

    quiz = build_quiz_for_word(
        selected_word=selected_word,
        root=root,
    )

    pipeline_trace = lookup_result.get("pipeline_trace", {})
    pipeline_trace.update(morphology_result.get("pipeline_trace", {}))

    return build_state_from_components(
        query=word,
        normalized_query=lookup_result["normalized_query"],
        selected_word_id=selected_word_id,
        selected_word=selected_word,
        root=root,
        pattern=pattern,
        tree=tree,
        leaf_details=leaf_details,
        selected_leaf=selected_leaf,
        quiz=quiz,
        morphology=build_morphology_output(morphology_result),
        family_words=lookup_result.get("family_words", []),
        same_pattern_words=lookup_result.get("same_pattern_words", []),
        pipeline_trace=pipeline_trace,
    )


def build_state_from_components(
    query: str,
    normalized_query: str,
    selected_word_id: str,
    selected_word: dict[str, Any],
    root: dict[str, Any],
    pattern: dict[str, Any] | None,
    tree: dict[str, Any],
    leaf_details: dict[str, Any],
    selected_leaf: dict[str, Any] | None,
    quiz: list[dict[str, Any]],
    morphology: dict[str, Any] | None = None,
    family_words: list[dict[str, Any]] | None = None,
    same_pattern_words: list[dict[str, Any]] | None = None,
    pipeline_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Assemble the evidence state from pieces the caller already has.

    `build_base_state` re-runs the entire pipeline from a query string, which is
    correct for the prompt lab and unacceptable on a request path — /api/insights
    would redo the lookup, morphology, tree, leaf-detail and quiz work that
    /api/analyze just did. The request path calls this instead, handing over what
    the pipeline already computed.

    This is the single definition of the state shape; `build_base_state` fills it
    from a word, everything else reads it.
    """
    return {
        "found": True,
        "query": query,
        "normalized_query": normalized_query,
        "selected_word_id": selected_word_id,
        "selected_word": selected_word,
        "root": root,
        "pattern": pattern,
        "family_words": family_words or [],
        "same_pattern_words": same_pattern_words or [],
        "morphology": morphology
        or {
            "root_letters": [],
            "pattern_letters": [],
            "reasoning_summary": "",
        },
        "tree": tree,
        "leaf_details": leaf_details,
        "selected_leaf": selected_leaf,
        "quiz": quiz,
        "pipeline_trace": pipeline_trace or {},
    }


def require_found_state(state: dict[str, Any]) -> None:
    if not state.get("found"):
        message = state.get("message", "Word not found.")
        reason = state.get("reason", "word_not_found")
        raise RuntimeError(f"Cannot build prompt evidence. Reason: {reason}. {message}")


def compact_word(word: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": word.get("id"),
        "arabic": word.get("arabic"),
        "normalized": word.get("normalized"),
        "transliteration": word.get("transliteration"),
        "meaning": word.get("meaning"),
        "short_meaning": word.get("short_meaning", word.get("meaning")),
        "root_id": word.get("root_id"),
        "pattern_id": word.get("pattern_id"),
        "word_type": word.get("word_type"),
        "pos": word.get("pos"),
        "level": word.get("level"),
    }


def compact_root(root: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": root.get("id"),
        "arabic": root.get("arabic"),
        "transliteration": root.get("transliteration"),
        "meaning": root.get("meaning"),
        "description": root.get("description"),
    }


def compact_pattern(pattern: dict[str, Any] | None) -> dict[str, Any] | None:
    if not pattern:
        return None

    return {
        "id": pattern.get("id"),
        "arabic": pattern.get("arabic"),
        "name": pattern.get("name"),
        "description": pattern.get("description"),
        "short_explanation": pattern.get("short_explanation"),
        "meaning_effect": pattern.get("meaning_effect"),
    }


def compact_leaf(leaf: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": leaf.get("id"),
        "arabic": leaf.get("arabic"),
        "normalized": leaf.get("normalized"),
        "transliteration": leaf.get("transliteration"),
        "meaning": leaf.get("meaning"),
        "short_meaning": leaf.get("short_meaning", leaf.get("meaning")),
        "is_selected": leaf.get("is_selected", False),
    }


def compact_leaf_detail(word_id: str, detail: dict[str, Any]) -> dict[str, Any]:
    word = detail.get("word", {})
    pattern = detail.get("pattern")

    return {
        "word_id": word_id,
        "word": word,
        "pattern": compact_pattern(pattern),
        "breakdown": detail.get("breakdown"),
        "explanation": detail.get("explanation"),
        "pattern_explanation": detail.get("pattern_explanation"),
        "same_pattern_words": detail.get("same_pattern_words", []),
        "same_pattern_explanation": detail.get("same_pattern_explanation"),
    }


def build_explanation_evidence(word: str) -> dict[str, Any]:
    return build_explanation_evidence_from_state(build_base_state(word))


def build_explanation_evidence_from_state(state: dict[str, Any]) -> dict[str, Any]:
    require_found_state(state)

    selected_leaf = state["selected_leaf"] or {}
    pattern = compact_pattern(state.get("pattern"))

    same_pattern_words = selected_leaf.get("same_pattern_words", [])

    llm_input = {
        "selected_word": {
            "arabic": state["selected_word"].get("arabic"),
            "meaning": state["selected_word"].get("meaning"),
        },
        "root": {
            "arabic": state["root"].get("arabic"),
            "meaning": state["root"].get("meaning"),
        },
        # name and meaning_effect are the KB's hand-curated statements of what
        # the pattern does. Without them the model guesses the function from the
        # pattern shape alone — observed live: فَعَل described as "points to the
        # person who does the action" (that is فَاعِل's job).
        "pattern": {
            "arabic": pattern.get("arabic") if pattern else None,
            "name": pattern.get("name") if pattern else None,
            "meaning_effect": pattern.get("meaning_effect") if pattern else None,
        },
        "same_pattern_cards": [
            {
                "arabic": item.get("arabic"),
                "meaning": item.get("meaning"),
            }
            for item in same_pattern_words
            if isinstance(item, dict)
        ],
    }

    review_context = {
        "query": state["query"],
        "normalized_query": state["normalized_query"],
        "selected_word_id": state["selected_word_id"],
        "selected_word": compact_word(state["selected_word"]),
        "root": compact_root(state["root"]),
        "pattern": pattern,
        "same_pattern_words": same_pattern_words,
        "current_explanation_fields": {
            "explanation": selected_leaf.get("explanation", ""),
            "pattern_explanation": selected_leaf.get("pattern_explanation", ""),
            "same_pattern_explanation": selected_leaf.get(
                "same_pattern_explanation",
                "",
            ),
            "tutor_note": selected_leaf.get("tutor_note", ""),
        },
    }

    return {
        "agent": "k2_explanation_agent",
        "prompt_lab_packet_version": "explanation_v5_grounded_pattern_input",
        "llm_input": llm_input,
        "review_context": review_context,
    }


def build_quiz_leaf_input(
    leaf: dict[str, Any],
    detail: dict[str, Any] | None,
) -> dict[str, Any]:
    detail = detail or {}

    pattern = detail.get("pattern") or {}

    return {
        "arabic": leaf.get("arabic"),
        "meaning": leaf.get("meaning"),
        # `name` is the KB's statement of what kind of pattern this is
        # ("abstract noun pattern", "Form VIII past-tense verb pattern"). Added
        # for the same reason the explanation packet carries it: without it the
        # model asserts the pattern's function from its shape, and observed live
        # on قَاسِم it called the verb pattern فَعَلَ "a noun pattern" in
        # distractor feedback. It is also what lets `quiz_claim_checker` decide
        # such a claim instead of leaving it to the guardrail, post-serve.
        "pattern": {
            "arabic": pattern.get("arabic"),
            "name": pattern.get("name"),
            "meaning_effect": pattern.get("meaning_effect"),
        },
    }


def build_quiz_evidence(word: str) -> dict[str, Any]:
    return build_quiz_evidence_from_state(build_base_state(word))


def build_quiz_evidence_from_state(state: dict[str, Any]) -> dict[str, Any]:
    require_found_state(state)

    tree_leaves = state["tree"].get("leaves", [])
    leaf_details = state.get("leaf_details", {})

    quiz_leaves = []

    for leaf in tree_leaves:
        if not isinstance(leaf, dict):
            continue

        leaf_id = leaf.get("id")
        detail = leaf_details.get(leaf_id, {})

        quiz_leaves.append(
            build_quiz_leaf_input(
                leaf=leaf,
                detail=detail,
            )
        )

    llm_input = {
        "root": {
            "arabic": state["root"].get("arabic"),
            "meaning": state["root"].get("meaning"),
        },
        "leaves": quiz_leaves,
    }

    review_context = {
        "query": state["query"],
        "normalized_query": state["normalized_query"],
        "selected_word_id": state["selected_word_id"],
        "selected_word": compact_word(state["selected_word"]),
        "root": compact_root(state["root"]),
        "tree": state["tree"],
        "leaf_details_summary": [
            compact_leaf_detail(word_id, detail)
            for word_id, detail in state["leaf_details"].items()
        ],
        "deterministic_quiz": state.get("quiz", []),
    }

    return {
        "agent": "tree_level_quiz_agent",
        "prompt_lab_packet_version": "quiz_v6_pattern_name",
        "llm_input": llm_input,
        "review_context": review_context,
    }


def build_combined_guardrail_input(
    word: str,
    tutor_output: dict[str, Any] | None,
    quiz_output: dict[str, Any] | None,
) -> dict[str, Any]:
    return build_combined_guardrail_input_from_state(
        state=build_base_state(word),
        tutor_output=tutor_output,
        quiz_output=quiz_output,
    )


def build_combined_guardrail_input_from_state(
    state: dict[str, Any],
    tutor_output: dict[str, Any] | None,
    quiz_output: dict[str, Any] | None,
) -> dict[str, Any]:
    require_found_state(state)

    selected_leaf = state["selected_leaf"] or {}
    pattern = compact_pattern(state.get("pattern"))

    same_pattern_cards = selected_leaf.get("same_pattern_words", [])
    if not isinstance(same_pattern_cards, list):
        same_pattern_cards = []

    leaves = []

    for leaf in state["tree"].get("leaves", []):
        if not isinstance(leaf, dict):
            continue

        leaf_id = leaf.get("id")
        detail = state.get("leaf_details", {}).get(leaf_id, {})
        detail_pattern = detail.get("pattern") if isinstance(detail, dict) else None

        compact_detail_pattern = compact_pattern(detail_pattern)

        leaves.append(
            {
                "arabic": leaf.get("arabic"),
                "meaning": leaf.get("meaning"),
                "pattern": {
                    "arabic": compact_detail_pattern.get("arabic")
                    if compact_detail_pattern
                    else None,
                    "meaning_effect": compact_detail_pattern.get("meaning_effect")
                    if compact_detail_pattern
                    else None,
                },
            }
        )

    normalized_tutor_output = normalize_tutor_output_for_guardrail(
        tutor_output=tutor_output,
        fallback_selected_leaf=selected_leaf,
    )

    normalized_quiz_output = normalize_quiz_output_for_guardrail(
        quiz_output=quiz_output,
        fallback_quiz=state.get("quiz", []),
    )

    return {
        "evidence": {
            "root": {
                "arabic": state["root"].get("arabic"),
                "meaning": state["root"].get("meaning"),
            },
            "leaves": leaves,
            "selected_word": {
                "arabic": state["selected_word"].get("arabic"),
                "meaning": state["selected_word"].get("meaning"),
            },
            "pattern": {
                "arabic": pattern.get("arabic") if pattern else None,
            },
            "same_pattern_cards": [
                {
                    "arabic": item.get("arabic"),
                    "meaning": item.get("meaning"),
                }
                for item in same_pattern_cards
                if isinstance(item, dict)
            ],
        },
        "tutor_output": normalized_tutor_output,
        "quiz_output": normalized_quiz_output,
    }


def normalize_tutor_output_for_guardrail(
    tutor_output: dict[str, Any] | None,
    fallback_selected_leaf: dict[str, Any],
) -> dict[str, str]:
    if not isinstance(tutor_output, dict):
        tutor_output = {}

    return {
        "explanation": string_or_fallback(
            tutor_output.get("explanation"),
            fallback_selected_leaf.get("explanation"),
        ),
        "pattern_explanation": string_or_fallback(
            tutor_output.get("pattern_explanation"),
            fallback_selected_leaf.get("pattern_explanation"),
        ),
        "same_pattern_explanation": string_or_fallback(
            tutor_output.get("same_pattern_explanation"),
            fallback_selected_leaf.get("same_pattern_explanation"),
        ),
    }


def normalize_quiz_output_for_guardrail(
    quiz_output: dict[str, Any] | None,
    fallback_quiz: list[dict[str, Any]],
) -> dict[str, Any]:
    if isinstance(quiz_output, dict) and isinstance(quiz_output.get("quiz"), list):
        return {
            "quiz": quiz_output["quiz"],
        }

    return {
        "quiz": fallback_quiz,
    }


def string_or_fallback(value: Any, fallback: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(fallback, str):
        return fallback

    return ""


def build_guardrail_evidence(word: str) -> dict[str, Any]:
    state = build_base_state(word)
    require_found_state(state)

    return {
        "agent": "hybrid_guardrail_validator",
        "task": "Review a final WAZN response for grounding, structure, and learning safety.",
        "query": state["query"],
        "normalized_query": state["normalized_query"],
        "selected_word_id": state["selected_word_id"],
        "selected_word": compact_word(state["selected_word"]),
        "root": compact_root(state["root"]),
        "pattern": compact_pattern(state.get("pattern")),
        "selected_leaf": state["selected_leaf"],
        "tree": state["tree"],
        "quiz": state["quiz"],
        "checks_to_review": [
            "selected_word exists",
            "selected_word_id matches selected_word.id",
            "root_id matches selected_word.root_id",
            "pattern_id matches selected_word.pattern_id",
            "selected_leaf exists",
            "explanation fields are strings",
            "quiz answer_id exists in choices",
            "same_pattern_words do not include selected word",
            "no unsupported Arabic examples appear",
        ],
    }


def build_evaluation_evidence(word: str) -> dict[str, Any]:
    state = build_base_state(word)
    require_found_state(state)

    quiz_summary = {
        "question_count": len(state.get("quiz", [])),
        "categories": [
            question.get("category")
            for question in state.get("quiz", [])
            if isinstance(question, dict)
        ],
        "uses_answer_id": all(
            isinstance(question, dict) and "answer_id" in question
            for question in state.get("quiz", [])
        ),
    }

    return {
        "agent": "k2_evaluation_agent",
        "task": "Evaluate the quality of the final WAZN learner response.",
        "query": state["query"],
        "normalized_query": state["normalized_query"],
        "selected_word": compact_word(state["selected_word"]),
        "root": compact_root(state["root"]),
        "pattern": compact_pattern(state.get("pattern")),
        "morphology": state["morphology"],
        "selected_leaf_explanation": {
            "explanation": state["selected_leaf"].get("explanation", "")
            if state["selected_leaf"]
            else "",
            "pattern_explanation": state["selected_leaf"].get("pattern_explanation", "")
            if state["selected_leaf"]
            else "",
            "same_pattern_explanation": state["selected_leaf"].get("same_pattern_explanation", "")
            if state["selected_leaf"]
            else "",
        },
        "quiz_summary": quiz_summary,
        "guardrail_result": {
            "status": "not_run_in_prompt_lab",
            "note": "This prompt-lab evidence is built from deterministic backend data.",
        },
        "scoring_dimensions": [
            "overall_score",
            "groundedness",
            "morphology_clarity",
            "arabic_safety",
            "beginner_friendliness",
            "quiz_quality",
            "pedagogical_usefulness",
        ],
    }


from typing import Any


def build_combined_evaluation_input(
    word: str,
    tutor_output: dict[str, Any] | None,
    quiz_output: dict[str, Any] | None,
) -> dict[str, Any]:
    return build_combined_evaluation_input_from_state(
        state=build_base_state(word),
        tutor_output=tutor_output,
        quiz_output=quiz_output,
    )


def build_combined_evaluation_input_from_state(
    state: dict[str, Any],
    tutor_output: dict[str, Any] | None,
    quiz_output: dict[str, Any] | None,
) -> dict[str, Any]:
    require_found_state(state)

    selected_leaf = state["selected_leaf"] or {}
    pattern = compact_pattern(state.get("pattern"))

    same_pattern_cards = selected_leaf.get("same_pattern_words", [])
    if not isinstance(same_pattern_cards, list):
        same_pattern_cards = []

    leaves = []

    for leaf in state["tree"].get("leaves", []):
        if not isinstance(leaf, dict):
            continue

        leaf_id = leaf.get("id")
        detail = state.get("leaf_details", {}).get(leaf_id, {})
        detail_pattern = detail.get("pattern") if isinstance(detail, dict) else None
        compact_detail_pattern = compact_pattern(detail_pattern)

        leaves.append(
            {
                "arabic": leaf.get("arabic"),
                "meaning": leaf.get("meaning"),
                "pattern": {
                    "arabic": compact_detail_pattern.get("arabic")
                    if compact_detail_pattern
                    else None,
                    "meaning_effect": compact_detail_pattern.get("meaning_effect")
                    if compact_detail_pattern
                    else None,
                },
            }
        )

    normalized_tutor_output = normalize_tutor_output_for_evaluation(
        tutor_output=tutor_output,
        fallback_selected_leaf=selected_leaf,
    )

    normalized_quiz_output = normalize_quiz_output_for_evaluation(
        quiz_output=quiz_output,
        fallback_quiz=state.get("quiz", []),
    )

    return {
        "evidence": {
            "root": {
                "arabic": state["root"].get("arabic"),
                "meaning": state["root"].get("meaning"),
            },
            "leaves": leaves,
            "selected_word": {
                "arabic": state["selected_word"].get("arabic"),
                "meaning": state["selected_word"].get("meaning"),
            },
            "pattern": {
                "arabic": pattern.get("arabic") if pattern else None,
                "name": pattern.get("name") if pattern else None,
                "meaning_effect": pattern.get("meaning_effect") if pattern else None,
            },
            # Each card carries the pattern it shares with the selected word.
            # `get_same_pattern_words` draws them from `kb.words_by_pattern`, so
            # the shared pattern is a KB fact — but the packet used to omit it,
            # which made `same_pattern_explanation`'s central claim ("words such
            # as شَغَلَ, حَمَلَ, كَتَبَ use the same pattern") unverifiable from
            # the evidence. The evaluation agent was right to deduct for it:
            # measured 2026-07-29, groundedness 6 on مدرسة and قَرَأَ, both
            # citing an "ungrounded claim about the same-pattern cards".
            "same_pattern_cards": [
                {
                    "arabic": item.get("arabic"),
                    "meaning": item.get("meaning"),
                    "pattern": {
                        "arabic": pattern.get("arabic") if pattern else None,
                    },
                }
                for item in same_pattern_cards
                if isinstance(item, dict)
            ],
        },
        "tutor_output": normalized_tutor_output,
        "quiz_output": normalized_quiz_output,
    }


def normalize_tutor_output_for_evaluation(
    tutor_output: dict[str, Any] | None,
    fallback_selected_leaf: dict[str, Any],
) -> dict[str, str] | None:
    if not isinstance(tutor_output, dict):
        return {
            "explanation": string_or_fallback(
                None,
                fallback_selected_leaf.get("explanation"),
            ),
            "pattern_explanation": string_or_fallback(
                None,
                fallback_selected_leaf.get("pattern_explanation"),
            ),
            "same_pattern_explanation": string_or_fallback(
                None,
                fallback_selected_leaf.get("same_pattern_explanation"),
            ),
        }

    return {
        "explanation": string_or_fallback(
            tutor_output.get("explanation"),
            fallback_selected_leaf.get("explanation"),
        ),
        "pattern_explanation": string_or_fallback(
            tutor_output.get("pattern_explanation"),
            fallback_selected_leaf.get("pattern_explanation"),
        ),
        "same_pattern_explanation": string_or_fallback(
            tutor_output.get("same_pattern_explanation"),
            fallback_selected_leaf.get("same_pattern_explanation"),
        ),
    }


def normalize_quiz_output_for_evaluation(
    quiz_output: dict[str, Any] | None,
    fallback_quiz: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if isinstance(quiz_output, dict) and isinstance(quiz_output.get("quiz"), list):
        return {
            "quiz": quiz_output["quiz"],
        }

    return {
        "quiz": fallback_quiz,
    }


def string_or_fallback(value: Any, fallback: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(fallback, str):
        return fallback

    return ""