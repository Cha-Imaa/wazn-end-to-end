from typing import Any

from app.modules.lookup_module import run_lookup_module
from app.modules.morphology_reasoning_module import run_morphology_reasoning_module
from app.services.k2_think_service import build_k2_think
from app.services.leaf_details_service import build_leaf_details_for_tree
from app.services.quiz_service import build_quiz_for_word
from app.services.tree_service import build_tree_response


DETERMINISTIC_SOURCE = "deterministic"
STATUS_FOUND = "found"
STATUS_NOT_FOUND = "not_found"


def run_wazn_pipeline(query: str) -> dict[str, Any]:
    lookup_result = run_lookup_module(query)

    pipeline_trace = lookup_result.get("pipeline_trace", {})

    if not lookup_result.get("found"):
        return build_not_found_response(
            query=lookup_result.get("query", query),
            normalized_query=lookup_result.get("normalized_query", ""),
            reason=lookup_result.get("reason", "word_not_found"),
            message=lookup_result.get(
                "message",
                "Word not found in the knowledge base.",
            ),
            pipeline_trace=pipeline_trace,
        )

    normalized_query = lookup_result["normalized_query"]
    selected_word_id = lookup_result["selected_word_id"]
    selected_word = lookup_result["selected_word"]
    root = lookup_result["root"]
    pattern = lookup_result.get("pattern")

    morphology_result = run_morphology_reasoning_module(
        selected_word=selected_word,
        root=root,
        pattern=pattern,
    )

    pipeline_trace.update(
        morphology_result.get("pipeline_trace", {})
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

    if not selected_leaf:
        return build_not_found_response(
            query=query,
            normalized_query=normalized_query,
            reason="missing_selected_leaf_detail",
            message="Selected word is missing leaf detail data.",
            pipeline_trace=pipeline_trace,
        )

    quiz = build_quiz_for_word(
        selected_word=selected_word,
        root=root,
    )

    pipeline_trace["quiz_generator"] = build_quiz_generator_trace(
        selected_word=selected_word,
        root=root,
        quiz=quiz,
    )

    k2_think = build_k2_think(
        selected_word=selected_word,
        root=root,
        pattern=pattern,
        quiz=quiz,
        pipeline_trace=pipeline_trace,
        selected_leaf=selected_leaf,
    )

    return {
        "status": STATUS_FOUND,
        "query": query,
        "normalized_query": normalized_query,
        "selected_word_id": selected_word_id,
        "root": {
            "id": root.get("id"),
            "arabic": root.get("arabic"),
            "transliteration": root.get("transliteration"),
            "meaning": root.get("meaning"),
            "description": root.get("description"),
        },
        "tree": tree,
        "leaf_details": leaf_details,
        "selected_leaf": selected_leaf,
        "quiz": quiz,
        "k2_think": k2_think,
        "source": DETERMINISTIC_SOURCE,
        "pipeline_trace": pipeline_trace,
    }


def build_quiz_generator_trace(
    selected_word: dict[str, Any],
    root: dict[str, Any],
    quiz: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source": DETERMINISTIC_SOURCE,
        "selected_word_id": selected_word.get("id"),
        "root_id": root.get("id"),
        "quiz_generated": bool(quiz),
        "question_count": len(quiz),
        "uses_answer_id": all(
            isinstance(question, dict) and "answer_id" in question
            for question in quiz
        ),
    }


def build_not_found_response(
    query: str,
    normalized_query: str,
    reason: str,
    message: str,
    pipeline_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": STATUS_NOT_FOUND,
        "query": query,
        "normalized_query": normalized_query,
        "selected_word_id": None,
        "root": None,
        "tree": {
            "trunk": None,
            "leaves": [],
        },
        "leaf_details": {},
        "selected_leaf": None,
        "quiz": [],
        "k2_think": None,
        "source": DETERMINISTIC_SOURCE,
        "reason": reason,
        "message": message,
        "pipeline_trace": pipeline_trace or {},
    }