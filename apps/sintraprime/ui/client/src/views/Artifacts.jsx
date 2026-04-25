import React, { useEffect, useMemo, useState } from "react";
import { getArtifacts, getFile } from "../api.js";
import JsonViewer from "../components/JsonViewer.jsx";

export default function Artifacts() {
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(null);
  const [json, setJson] = useState(null);

  useEffect(() => {
    (async () => {
      const r = await getArtifacts("");
      setList(Array.isArray(r) ? r : []);
    })();
  }, []);

  const filtered = useMemo(() => {
    if (!q) return list;
    return list.filter((x) => String(x?.path || "").toLowerCase().includes(q.toLowerCase()));
  }, [list, q]);

  async function open(p) {
    setSel(p);
    setJson(await getFile(p));
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      <div>
        <input
          placeholder="search path…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ width: "100%" }}
        />
        <div style={{ marginTop: 10, border: "1px solid #333", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ maxHeight: "65vh", overflow: "auto" }}>
            {filtered.map((x, i) => (
              <div
                key={i}
                onClick={() => open(x.path)}
                style={{ padding: 10, borderBottom: "1px solid #222", cursor: "pointer" }}
              >
                <div style={{ fontWeight: 700 }}>{x.path}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>{sel || "Artifact JSON"}</div>
        <JsonViewer value={json || { note: "Select an artifact" }} />
      </div>
    </div>
  );
}
