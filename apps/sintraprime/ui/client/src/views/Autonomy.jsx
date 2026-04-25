import React, { useState } from "react";
import JsonViewer from "../components/JsonViewer.jsx";
import { sendCommand } from "../api.js";

export default function Autonomy() {
  const [out, setOut] = useState(null);

  async function quickCheck() {
    setOut(await sendCommand("/scheduler history"));
  }

  return (
    <div>
      <div style={{ opacity: 0.7, marginBottom: 8 }}>
        Autonomy artifacts live under runs/autonomy/* (this UI is read-only).
      </div>
      <button onClick={quickCheck}>Quick check (scheduler history)</button>
      <div style={{ marginTop: 10 }}>
        <JsonViewer value={out || { note: "Use Artifacts view to inspect autonomy summaries." }} />
      </div>
    </div>
  );
}
