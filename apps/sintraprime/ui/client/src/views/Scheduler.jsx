import React, { useState } from "react";
import JsonViewer from "../components/JsonViewer.jsx";
import { sendCommand } from "../api.js";
import SchedulerExplain from "./SchedulerExplain.jsx";

export default function Scheduler() {
  const [out, setOut] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState("notion_tax_cases_daily_scan");
  const [selectedAt, setSelectedAt] = useState("");
  const [autoRunSignal, setAutoRunSignal] = useState(0);

  async function history() {
    setOut(await sendCommand("/scheduler history"));
  }

  const historyRows = (out && out.kind === "SchedulerHistory" && Array.isArray(out.rows)) ? out.rows : null;

  function explainRow(row) {
    const jid = String(row?.job_id ?? "");
    const at = String(row?.started_at ?? "");
    if (jid) setSelectedJobId(jid);
    setSelectedAt(at);
    setAutoRunSignal((x) => x + 1);
  }

  return (
    <div>
      <div style={{ display: "grid", gap: 14 }}>
        <div>
          <button onClick={history}>/scheduler history</button>
          <div style={{ marginTop: 10 }}>
            <JsonViewer value={out || { note: "Run scheduler history" }} />
          </div>

          {historyRows && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Recent windows</div>
              <div style={{ overflow: "auto", border: "1px solid #ddd", borderRadius: 10 }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #eee" }}>job_id</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #eee" }}>started_at</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #eee" }}>window</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #eee" }}>outcome</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #eee" }} />
                    </tr>
                  </thead>
                  <tbody>
                    {historyRows.map((r, idx) => {
                      const outcome = r?.outcome?.kind || (r?.outcome?.skipped ? "skipped" : "");
                      return (
                        <tr key={`${String(r?.job_id ?? "")}.${String(r?.window_id ?? idx)}`}>
                          <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>{String(r?.job_id ?? "")}</td>
                          <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>{String(r?.started_at ?? "")}</td>
                          <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>{String(r?.window_id ?? "")}</td>
                          <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>{outcome}</td>
                          <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>
                            <button onClick={() => explainRow(r)}>Explain</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <div>
          <div style={{ fontWeight: 800, marginBottom: 6 }}>/scheduler explain</div>
          <SchedulerExplain
            jobId={selectedJobId}
            at={selectedAt}
            onJobIdChange={setSelectedJobId}
            onAtChange={setSelectedAt}
            autoRunSignal={autoRunSignal}
          />
        </div>
      </div>
    </div>
  );
}
