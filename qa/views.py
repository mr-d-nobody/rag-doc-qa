import io
import json

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from rag import VectorStore, answer

# In-memory state (resets when the server restarts).
store = VectorStore()
indexed = {}  # filename -> number of chunks


def _doc_list():
    return [{"name": n, "chunks": c} for n, c in indexed.items()]


@require_GET
def documents(request):
    return JsonResponse(_doc_list(), safe=False)


@csrf_exempt  # the React app is a separate client; no Django-rendered form / CSRF token
@require_POST
def upload(request):
    for f in request.FILES.getlist("files"):
        if f.name in indexed:
            continue
        try:
            indexed[f.name] = store.add_document(io.BytesIO(f.read()), f.name)
        except Exception as e:
            return JsonResponse({"detail": f"{f.name}: {e}"}, status=400)
    return JsonResponse(_doc_list(), safe=False)


@csrf_exempt
@require_POST
def ask(request):
    body = json.loads(request.body or "{}")
    question = (body.get("question") or "").strip()
    if not question:
        return JsonResponse({"detail": "Question is empty."}, status=400)
    if not indexed:
        return JsonResponse({"detail": "Upload a PDF first."}, status=400)

    hits, tokens = answer(store, question, int(body.get("k", 4)))

    def generate():
        sources = [
            {"source": c.source, "page": c.page, "score": round(s, 2), "text": c.text}
            for c, s in hits
        ]
        yield json.dumps({"sources": sources}) + "\n"
        for t in tokens:
            yield json.dumps({"token": t}) + "\n"

    return StreamingHttpResponse(generate(), content_type="application/x-ndjson")
