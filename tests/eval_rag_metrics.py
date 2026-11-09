"""
Score the live ISAT RAG pipeline on a labeled catalog question set.

The indexed corpus is course-catalog chunks plus ABET syllabus chunks.
Imported ISAT website pages currently have no chunks, so they are not in this set.

Metrics are macro-averaged over questions:
- Accuracy: share of answers that contain every required fact.
- Precision: share of retrieved chunks that contain at least one required fact.
- Recall: share of required facts present in the retrieved context.

A fact matches when any alias appears as a case-insensitive substring.
Aliases are distinctive catalog phrases, not generic words like "credits" or "prerequisite".
"""
import json
import logging
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(project_root, ".env"))

# Each fact is a list of acceptable aliases. The first alias is the canonical label.
EVAL_SET = [
    {
        "id": "isat_212",
        "question": "What is ISAT 212, and what is its prerequisite?",
        "facts": [
            ["energy issues in science and technology"],
            ["renewable energy sources"],
            ["isat 152 or permission"],
        ],
    },
    {
        "id": "isat_391",
        "question": "What is ISAT 391 and what course is its prerequisite?",
        "facts": [
            ["holistic problem-solving workshop ii"],
            ["isat 390"],
        ],
    },
    {
        "id": "isat_151",
        "question": "What does ISAT 151 cover?",
        "facts": [
            ["topics in applied calculus"],
            ["differential and integral calculus"],
        ],
    },
    {
        "id": "isat_152",
        "question": "What physics topics does ISAT 152 introduce, and what is the prerequisite?",
        "facts": [
            ["one- and two-dimensional motion"],
            ["isat 151 or permission"],
        ],
    },
    {
        "id": "isat_113l",
        "question": "What do students do in the ISAT 113L laboratory?",
        "facts": [
            ["life science wet lab"],
            ["biotechnology issues in science and technology laboratory"],
        ],
    },
    {
        "id": "isat_252",
        "question": "What is ISAT 252?",
        "facts": [
            ["programming and problem solving"],
            ["computational thinking and formal logic"],
        ],
    },
    {
        "id": "isat_300",
        "question": "What are the prerequisites for ISAT 300?",
        "facts": [
            ["isat 252 and a minimum grade"],
            ["applied computing, instrumentation and measurement"],
        ],
    },
    {
        "id": "isat_320",
        "question": "What is ISAT 320 and what is its prerequisite?",
        "facts": [
            ["fundamentals of environmental science"],
            ["isat 112 or permission"],
        ],
    },
    {
        "id": "isat_410",
        "question": "What renewable technologies does ISAT 410 cover?",
        "facts": [
            ["sustainable energy development"],
            ["photovoltaics"],
            ["wind power"],
        ],
    },
    {
        "id": "isat_490",
        "question": "What is ISAT 490?",
        "facts": [
            ["capstone experience i"],
            ["independent research project"],
        ],
    },
    {
        "id": "isat_171",
        "question": "What is ISAT 171?",
        "facts": [
            ["governance of sociotechnical systems"],
        ],
    },
    {
        "id": "isat_301",
        "question": "What kinds of energy systems does ISAT 301 measure?",
        "facts": [
            ["instrumentation and measurement in energy"],
            ["nuclear energy"],
        ],
    },
    {
        "id": "isat_271",
        "question": "What does ISAT 271 cover?",
        "facts": [
            ["technology, science and society"],
            ["social aspects of technology and science"],
        ],
    },
    {
        "id": "isat_290",
        "question": "What does ISAT 290 teach?",
        "facts": [
            ["introduction to systems thinking for complex problems"],
            ["systems thinking methodology"],
        ],
    },
    {
        "id": "isat_350",
        "question": "What topics does ISAT 350 cover?",
        "facts": [
            ["biotechnology for the new millennium"],
            ["living system nanotechnology"],
        ],
    },
    {
        "id": "isat_420",
        "question": "What does ISAT 420 cover, and what is the prerequisite?",
        "facts": [
            ["environmental analysis and modeling"],
            ["mathematical techniques and computer models"],
            ["isat 321 or permission"],
        ],
    },
    {
        "id": "isat_251",
        "question": "What is ISAT 251?",
        "facts": [
            ["topics in applied statistics"],
            ["statistical thinking"],
        ],
    },
    {
        "id": "isat_211",
        "question": "What is ISAT 211?",
        "facts": [
            ["issues in modern production systems"],
        ],
    },
]


def _contains_any(text: str, aliases: list[str]) -> bool:
    haystack = (text or "").lower()
    return any(alias.lower() in haystack for alias in aliases)


def score_example(answer: str, chunks: list[dict], facts: list[list[str]]) -> dict:
    context = "\n".join((c.get("chunk_text") or "") for c in chunks)
    facts_in_context = sum(1 for fact in facts if _contains_any(context, fact))
    facts_in_answer = sum(1 for fact in facts if _contains_any(answer, fact))
    relevant_chunks = sum(
        1 for chunk in chunks if any(_contains_any(chunk.get("chunk_text") or "", fact) for fact in facts)
    )
    n_chunks = len(chunks)
    n_facts = len(facts)
    precision = (relevant_chunks / n_chunks) if n_chunks else 0.0
    recall = (facts_in_context / n_facts) if n_facts else 0.0
    accurate = facts_in_answer == n_facts and n_facts > 0
    return {
        "precision": precision,
        "recall": recall,
        "accurate": accurate,
        "facts_in_context": facts_in_context,
        "facts_in_answer": facts_in_answer,
        "n_facts": n_facts,
        "relevant_chunks": relevant_chunks,
        "n_chunks": n_chunks,
        "answer_fact_recall": (facts_in_answer / n_facts) if n_facts else 0.0,
    }


def aggregate(rows: list[dict]) -> dict:
    n = len(rows) or 1
    return {
        "n": len(rows),
        "accuracy": sum(1 for r in rows if r["accurate"]) / n,
        "precision": sum(r["precision"] for r in rows) / n,
        "recall": sum(r["recall"] for r in rows) / n,
        "answer_fact_recall": sum(r["answer_fact_recall"] for r in rows) / n,
    }


def run(save_raw: str | None = None) -> dict:
    logging.disable(logging.CRITICAL)
    from LangGraph.main import graph

    rows = []
    for i, item in enumerate(EVAL_SET, 1):
        print(f"[{i}/{len(EVAL_SET)}] {item['question']}", flush=True)
        result = graph.invoke(
            {
                "question": item["question"],
                "requires_rag": None,
                "chunks": None,
                "answer": None,
                "conversation_history": [],
            }
        )
        chunks = result.get("chunks") or []
        answer = result.get("answer") or ""
        scored = score_example(answer, chunks, item["facts"])
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "requires_rag": result.get("requires_rag"),
                "answer": answer,
                "chunks": [
                    {
                        "chunk_id": c.get("chunk_id"),
                        "similarity": float(c["similarity"]) if c.get("similarity") is not None else None,
                        "chunk_text": c.get("chunk_text"),
                    }
                    for c in chunks
                ],
                **scored,
            }
        )
        print(
            f"  precision={scored['precision']:.2f} recall={scored['recall']:.2f} "
            f"answer_facts={scored['facts_in_answer']}/{scored['n_facts']}",
            flush=True,
        )

    summary = aggregate(rows)
    payload = {"summary": summary, "results": rows}
    if save_raw:
        with open(save_raw, "w") as f:
            json.dump(payload, f, indent=2)
    return payload


def print_summary(payload: dict) -> None:
    summary = payload["summary"]
    print("\n" + "=" * 72)
    print("RAG EVALUATION")
    print("=" * 72)
    print(f"Questions:  {summary['n']}")
    print(f"Accuracy:   {summary['accuracy'] * 100:.1f}%  (answer contains every labeled fact)")
    print(f"Precision:  {summary['precision'] * 100:.1f}%  (retrieved chunks that contain a labeled fact)")
    print(f"Recall:     {summary['recall'] * 100:.1f}%  (labeled facts found in retrieved context)")
    print(f"Answer fact coverage: {summary['answer_fact_recall'] * 100:.1f}%")
    print("-" * 72)
    for row in payload["results"]:
        mark = "PASS" if row["accurate"] else "FAIL"
        print(
            f"{mark:4} P={row['precision']:.2f} R={row['recall']:.2f} "
            f"ans={row['facts_in_answer']}/{row['n_facts']}  {row['id']}"
        )


if __name__ == "__main__":
    out = os.path.join(project_root, "tests", "rag_eval_results.json")
    payload = run(save_raw=out)
    print_summary(payload)
    print(f"\nWrote {out}")
