import React, { useState } from "react";
import JsonViewer from "../components/JsonViewer.jsx";
import { sendCommand } from "../api.js";

export default function Audit() {
  const [out, setOut] = useState(null);
  const [since, setSince] = useState("1970-01-01T00:00:00Z");

  async function run() {
    const msg = `/audit export ${JSON.stringify({ since, redact: true, include_artifacts: true })}`;
    setOut(await sendCommand(msg));
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input value={since} onChange={(e) => setSince(e.target.value)} style={{ width: 280 }} />
        <button onClick={run}>Export audit</button>
      </div>
      <div style={{ marginTop: 10 }}>
        <JsonViewer value={out || { note: "Runs /audit export via /api/command" }} />
      </div>
    </div>
  );
}
