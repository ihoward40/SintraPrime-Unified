import React, { useEffect, useRef, useState } from "react";
import JsonViewer from "../components/JsonViewer.jsx";
import { sendCommand } from "../api.js";

export default function SchedulerExplain({
  jobId,
  at,
  onJobIdChange,
  onAtChange,
  autoRunSignal,
}) {
  const [jobIdLocal, setJobIdLocal] = useState("notion_tax_cases_daily_scan");
  const [atLocal, setAtLocal] = useState("");
  const [out, setOut] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const lastAutoRunSignalRef = useRef(null);

  const effectiveJobId = (jobId ?? jobIdLocal);
  const effectiveAt = (at ?? atLocal);

  function setJobId(next) {
    if (typeof onJobIdChange === "function") onJobIdChange(next);
    else setJobIdLocal(next);
  }

  function setAt(next) {
    if (typeof onAtChange === "function") onAtChange(next);
    else setAtLocal(next);
  }

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      const trimmedJobId = String(effectiveJobId ?? "").trim();
      const trimmedAt = String(effectiveAt ?? "").trim();

      const cmd = trimmedAt
        ? `/scheduler explain ${trimmedJobId} --at ${trimmedAt}`
        : `/scheduler explain ${trimmedJobId}`;

      const r = await sendCommand(cmd);
      setOut(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (typeof autoRunSignal !== "number") return;
    if (lastAutoRunSignalRef.current === autoRunSignal) return;
    lastAutoRunSignalRef.current = autoRunSignal;
    if (!String(effectiveJobId ?? "").trim()) return;
    if (busy) return;
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRunSignal]);

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input
          value={effectiveJobId}
          onChange={(e) => setJobId(e.target.value)}
          placeholder="job_id"
          style={{ minWidth: 260 }}
        />
        <input
          value={effectiveAt}
          onChange={(e) => setAt(e.target.value)}
          placeholder="--at (optional ISO)"
          style={{ minWidth: 260 }}
        />
        <button disabled={busy || !String(effectiveJobId ?? "").trim()} onClick={run}>
          {busy ? "Running…" : "Explain"}
        </button>
        {err && <span style={{ color: "crimson" }}>{err}</span>}
      </div>

      <JsonViewer
        value={
          out || {
            note: "Runs /scheduler explain via /api/command",
            example: "/scheduler explain notion_tax_cases_daily_scan --at 2024-01-10T09:15:30Z",
          }
        }
      />
    </div>
  );
}
