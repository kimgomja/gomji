"""Run the existing SANUP-P RAG pipeline in its own Python environment.

The Streamlit app sends one JSON request on stdin. This process returns one JSON
result on stdout and never prints credentials or raw exception messages.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


SOURCE_TYPES = {
    "all": None,
    "sif": "sif",
    "moel_report": "moel_report",
    "kosha_guide": "kosha_guide",
}
SEARCH_MODES = {"semantic", "hybrid_rrf", "lexical"}


def run(root: Path, request: dict) -> dict:
    sys.path.insert(0, str(root))
    from dotenv import dotenv_values
    from langchain_openai import ChatOpenAI
    from src.rag_chain import build_rag_chain
    from src.retriever import PersonalRetriever

    question = str(request.get("question") or "").strip()
    if not question or len(question) > 2000:
        raise ValueError("invalid_question")
    mode = str(request.get("mode") or "semantic")
    source = str(request.get("source") or "all")
    if mode not in SEARCH_MODES or source not in SOURCE_TYPES:
        raise ValueError("invalid_filter")

    config = dotenv_values(root / ".env")
    api_key = (os.getenv("OPENAI_API_KEY") or config.get("OPENAI_API_KEY") or "").strip()
    if mode != "lexical" and not api_key:
        raise ValueError("semantic_key_missing")
    llm = None
    if api_key and request.get("generate", True):
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL") or config.get("OPENAI_MODEL") or "gpt-6-luna",
            api_key=api_key,
            timeout=60,
            max_retries=0,
            max_completion_tokens=1200,
            reasoning_effort="low",
        )

    retriever = PersonalRetriever(root, mode=mode)
    if mode != "lexical" and api_key and not (config.get("OPENAI_API_KEY") or "").strip():
        from openai import OpenAI
        retriever._openai = OpenAI(api_key=api_key, timeout=60, max_retries=2)
    tbm = bool(request.get("tbm"))
    retrieve = retriever.retrieve_tbm if tbm else retriever.retrieve
    retrieved: list[dict] = []

    def tracked_retrieve(*args, **kwargs):
        hits = retrieve(*args, **kwargs)
        retrieved[:] = hits
        return hits

    chain = build_rag_chain(tracked_retrieve, llm, min_similarity=0.12 if mode == "lexical" else 0.38)
    chain_input = {
            "question": question,
            "source_type": None if tbm else SOURCE_TYPES[source],
            "required_source_types": ["sif", "kosha_guide"] if tbm else None,
            "industry_major": str(request.get("industry_major") or "").strip() or None,
            "equipment": str(request.get("equipment") or "").strip() or None,
            "work_context": str(request.get("work_context") or "").strip()[:500],
            "chat_history": request.get("history") or [],
        }
    result = chain.invoke(chain_input)
    if llm is not None and result.get("status") in {"unsupported_citation", "malformed_quantity", "empty_response"}:
        result = chain.invoke(chain_input)
    answer = result.get("answer") or ""
    sources = []
    for position, hit in enumerate(result.get("sources") or []):
        metadata = hit.get("metadata") or {}
        citation_number = next(
            (index for index, original in enumerate(retrieved, start=1) if original is hit),
            position + 1,
        )
        sources.append(
            {
                "number": citation_number,
                "title": str(metadata.get("title") or hit.get("doc_id") or "제목 없음"),
                "organization": str(metadata.get("organization") or ""),
                "url": str(metadata.get("source_url") or ""),
                "page": metadata.get("page"),
                "doc_id": str(hit.get("doc_id") or ""),
                "source_type": str(metadata.get("source_type") or ""),
                "ocr_review_required": bool(metadata.get("ocr_review_required")),
            }
        )
    return {"status": result.get("status"), "answer": answer, "sources": sources}


def main() -> None:
    try:
        root = Path(sys.argv[1]).resolve()
        request = json.load(sys.stdin)
        output = run(root, request)
    except Exception as exc:
        kind = type(exc).__name__
        detail = str(exc).lower()
        if "readonly database" in detail or "read-only database" in detail:
            code = "index_readonly"
        elif kind == "ValueError" and "semantic_key_missing" in detail:
            code = "semantic_key_missing"
        elif kind == "RuntimeError" and "index" in detail:
            code = "index_invalid"
        else:
            code = kind
        output = {"status": "error", "code": code, "answer": "", "sources": []}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
