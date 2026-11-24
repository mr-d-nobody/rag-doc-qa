"""Evaluate retrieval (and optionally answers) on samples/eval_questions.json.

Metrics
  hit@k : fraction of questions whose expected page appears in the top-k retrieved chunks
  MRR   : mean reciprocal rank of the first chunk from the expected page
  answer accuracy (--answers) : generated answer contains the expected string

Usage
  python eval.py                         # retrieval only, current LLM_PROVIDER
  python eval.py --answers               # also generate and check answers
  python eval.py --sweep                 # compare chunk sizes
"""
import argparse
import json
from pathlib import Path

import rag

HERE = Path(__file__).parent / "samples"


def build_store(pdf: Path, size: int, overlap: int) -> rag.VectorStore:
    store = rag.VectorStore()
    with open(pdf, "rb") as f:
        store.add_document(f, pdf.name, size, overlap)
    return store


def evaluate(store, questions, k: int, answers: bool):
    hits, rr, correct = 0, 0.0, 0
    for item in questions:
        results = store.search(item["q"], k)
        pages = [c.page for c, _ in results]
        if item["page"] in pages:
            hits += 1
            rr += 1.0 / (pages.index(item["page"]) + 1)
        if answers:
            _, tokens = rag.answer(store, item["q"], k)
            text = "".join(tokens)
            ok = item["answer"].lower() in text.lower()
            correct += ok
            print(f"  [{'ok ' if ok else 'BAD'}] {item['q']} -> {text.strip()[:90]!r}")
    n = len(questions)
    return {"hit@k": hits / n, "mrr": rr / n, "answer_acc": (correct / n) if answers else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(HERE / "company_policy.pdf"))
    ap.add_argument("--questions", default=str(HERE / "eval_questions.json"))
    ap.add_argument("--size", type=int, default=800)
    ap.add_argument("--overlap", type=int, default=150)
    ap.add_argument("-k", type=int, default=4)
    ap.add_argument("--answers", action="store_true")
    ap.add_argument("--sweep", action="store_true", help="compare several chunk sizes (retrieval only)")
    args = ap.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    print(f"provider={rag.PROVIDER} embed={rag.EMBED_MODEL} chat={rag.CHAT_MODEL} questions={len(questions)}")

    configs = [(200, 40), (400, 80), (800, 150), (1500, 250)] if args.sweep else [(args.size, args.overlap)]
    for size, overlap in configs:
        store = build_store(Path(args.pdf), size, overlap)
        m = evaluate(store, questions, args.k, args.answers and not args.sweep)
        acc = f" answer_acc={m['answer_acc']:.2f}" if m["answer_acc"] is not None else ""
        print(f"chunk={size:<5} overlap={overlap:<4} chunks={len(store.chunks):<4} k={args.k} "
              f"hit@k={m['hit@k']:.2f} MRR={m['mrr']:.2f}{acc}")


if __name__ == "__main__":
    main()
