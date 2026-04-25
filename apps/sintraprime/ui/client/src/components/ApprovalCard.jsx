import React, { useState } from "react";
import { Link } from "react-router-dom";
import JsonViewer from "./JsonViewer.jsx";
import { sendCommand } from "../api.js";

export default function ApprovalCard({ item, onActionDone }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);

  const executionId = item?.execution_id || item?.executionId || item?.id || null;

  async function run(msg) {
    setBusy(true);
    try {
      const r = await sendCommand(msg);
      setLast(r);
      onActionDone?.();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ border: "1px solid #333", borderRadius: 14, padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 800 }}>{executionId || "(no execution_id)"}</div>
          <div style={{ opacity: 0.75, fontSize: 12 }}>status: {item?.status || "(none)"}</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button disabled={busy || !executionId} onClick={() => run(`/approve ${executionId}`)}>Approve</button>
          <button disabled={busy || !executionId} onClick={() => run(`/rollback ${executionId}`)}>Rollback</button>
          {executionId && (
            <Link to={`/execution/${encodeURIComponent(executionId)}?tab=inbox`} style={{ color: "#9ecbff", alignSelf: "center" }}>
              View Timeline
            </Link>
          )}
          <button onClick={() => setOpen((o) => !o)}>{open ? "Hide" : "View"} JSON</button>
        </div>
      </div>
      {open && (
        <div style={{ marginTop: 10 }}>
          <JsonViewer value={item} />
        </div>
      )}
      {last && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontWeight: 700 }}>Last response</div>
          <JsonViewer value={last} />
        </div>
      )}
    </div>
  );
}
