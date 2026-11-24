import { useEffect, useRef, useState } from "react";

// Empty in local dev (Vite proxies /api); set VITE_API_URL to the backend URL in production.
const API = import.meta.env.VITE_API_URL || "";

export default function App() {
  const [docs, setDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/api/documents`).then((r) => r.json()).then(setDocs).catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function upload(e) {
    const files = e.target.files;
    if (!files.length) return;
    const form = new FormData();
    for (const f of files) form.append("files", f);
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/upload`, { method: "POST", body: form });
      if (!res.ok) throw new Error((await res.json()).detail);
      setDocs(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  async function ask(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setError("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text: question }, { role: "assistant", text: "", sources: [] }]);

    const update = (fn) =>
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = fn(copy[copy.length - 1]);
        return copy;
      });

    try {
      const res = await fetch(`${API}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error((await res.json()).detail);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (!line) continue;
          const msg = JSON.parse(line);
          if (msg.sources) update((a) => ({ ...a, sources: msg.sources }));
          if (msg.token) update((a) => ({ ...a, text: a.text + msg.token }));
        }
      }
    } catch (err) {
      setError(err.message);
      setMessages((m) => m.slice(0, -2));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <aside>
        <h2>Documents</h2>
        <label className="upload">
          Upload PDFs
          <input type="file" accept="application/pdf" multiple onChange={upload} hidden />
        </label>
        <ul>
          {docs.map((d) => (
            <li key={d.name}>
              {d.name} <span>({d.chunks} chunks)</span>
            </li>
          ))}
        </ul>
      </aside>

      <main>
        <h1>Document Q&A</h1>
        <div className="chat">
          {messages.length === 0 && <p className="hint">Upload a PDF, then ask a question.</p>}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <p>{m.text || (busy && i === messages.length - 1 ? "..." : "")}</p>
              {m.sources?.length > 0 && (
                <details>
                  <summary>Sources</summary>
                  {m.sources.map((s, j) => (
                    <div key={j} className="source">
                      <strong>
                        [{j + 1}] {s.source}, p.{s.page}
                      </strong>{" "}
                      <span>(similarity {s.score})</span>
                      <p>{s.text}</p>
                    </div>
                  ))}
                </details>
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>
        {error && <div className="error">{error}</div>}
        <form onSubmit={ask}>
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about your documents" />
          <button disabled={busy || !input.trim()}>Send</button>
        </form>
      </main>
    </div>
  );
}
