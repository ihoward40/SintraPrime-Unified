import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getReceipts } from "../api.js";
import JsonViewer from "../components/JsonViewer.jsx";

export default function Runs() {
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    (async () => {
      const r = await getReceipts(250);
      setRows(Array.isArray(r) ? r : []);
    })();
  }, []);

  const filtered = useMemo(() => {
    if (!status) return rows;
    return rows.filter((r) => String(r?.status || "").toLowerCase().includes(status.toLowerCase()));
  }, [rows, status]);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      <div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input placeholder="filter status…" value={status} onChange={(e) => setStatus(e.target.value)} />
          <div style={{ opacity: 0.7 }}>
            {filtered.length}/{rows.length}
          </div>
        </div>
        <div style={{ marginTop: 10, border: "1px solid #333", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ maxHeight: "65vh", overflow: "auto" }}>
            {filtered.map((r, i) => (
              <div
                key={i}
                onClick={() => setSelected(r)}
                style={{ padding: 10, borderBottom: "1px solid #222", cursor: "pointer" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "baseline" }}>
                  <div style={{ fontWeight: 800 }}>{r?.execution_id || "(no execution_id)"}</div>
                  {r?.execution_id && (
                    <Link
                      to={`/execution/${encodeURIComponent(r.execution_id)}?tab=runs`}
                      onClick={(e) => e.stopPropagation()}
                      style={{ color: "#9ecbff", fontSize: 12 }}
                    >
                      View Timeline
                    </Link>
                  )}
                </div>
                <div style={{ opacity: 0.75, fontSize: 12 }}>
                  {r?.status || "(no status)"} • {r?.finished_at || r?.started_at || ""}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>Receipt JSON</div>
        <JsonViewer value={selected || { note: "Select a receipt" }} />
      </div>
    </div>
  );
}
