import React, { useEffect, useState } from "react";
import { getApprovals } from "../api.js";
import ApprovalCard from "../components/ApprovalCard.jsx";

export default function Inbox() {
  const [items, setItems] = useState([]);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    setErr(null);
    try {
      const r = await getApprovals();
      setItems(Array.isArray(r) ? r : []);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button onClick={refresh} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
        <div style={{ opacity: 0.7 }}>{items.length} approval(s)</div>
        {err && <div style={{ color: "crimson" }}>{err}</div>}
      </div>
      <div style={{ marginTop: 12, display: "grid", gap: 10 }}>
        {items.map((it, idx) => (
          <ApprovalCard key={it?.execution_id || idx} item={it} onActionDone={refresh} />
        ))}
        {!items.length && <div style={{ opacity: 0.7, marginTop: 10 }}>No pending approvals.</div>}
      </div>
    </div>
  );
}
