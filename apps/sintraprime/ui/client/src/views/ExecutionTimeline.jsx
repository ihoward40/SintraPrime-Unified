import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import JsonViewer from "../components/JsonViewer.jsx";

function classifyEventColor(kind, payload) {
  const k = String(kind || "");
  if (k === "approval_required" || k === "approved") return "#d4a017"; // yellow-ish
  if (k === "policy" && payload?.policy_denied) return "crimson";
  if (k === "completed" && String(payload?.status || "") !== "success") return "crimson";
  return "#2ecc71"; // green-ish
}

function inferEvents(data) {
  const receipt = data?.receipt || null;
  const approval = data?.approval || null;
  const prestatePaths = Array.isArray(data?.prestate_paths) ? data.prestate_paths : [];
  const artifacts = Array.isArray(data?.artifact_items) ? data.artifact_items : [];

  const events = [];

  const startedAt = receipt?.started_at || approval?.started_at || receipt?.created_at || approval?.created_at || null;
  const finishedAt = receipt?.finished_at || null;

  if (approval?.command) {
    events.push({
      timestamp: approval?.created_at || startedAt || "",
      kind: "command",
      label: "Command",
      payload: { command: approval.command, original_command: approval.original_command || null, domain_id: approval.domain_id || null },
    });
  }

  if (approval?.plan) {
    events.push({
      timestamp: approval?.created_at || startedAt || "",
      kind: "planning",
      label: "Plan created",
      payload: { plan_hash: approval.plan_hash || receipt?.plan_hash || null, plan: approval.plan },
    });
  } else {
    events.push({
      timestamp: startedAt || "",
      kind: "planning",
      label: "Plan (not persisted)",
      payload: {
        note: "This execution has no runs/approvals/<execution_id>.json; the engine does not persist plans for non-approved runs.",
      },
    });
  }

  events.push({
    timestamp: startedAt || "",
    kind: "policy",
    label: receipt?.policy_denied ? "Policy denied" : receipt?.approval_required ? "Policy: approval required" : "Policy checked",
    payload: {
      policy_denied: receipt?.policy_denied || null,
      policy_code: receipt?.policy_code || null,
      approval_required: receipt?.approval_required || null,
      plan_hash: receipt?.plan_hash || approval?.plan_hash || null,
    },
  });

  if (receipt?.approval_required) {
    events.push({
      timestamp: receipt?.finished_at || receipt?.started_at || startedAt || "",
      kind: "approval_required",
      label: "Approval required",
      payload: receipt.approval_required,
    });

    // If we have a later success receipt, treat it as approved+executed.
    if (String(receipt?.status || "") === "success") {
      events.push({
        timestamp: receipt?.started_at || startedAt || "",
        kind: "approved",
        label: "Approved (inferred)",
        payload: { note: "Approval happened prior to execution; approval timestamp is not persisted." },
      });
    }
  }

  for (const p of prestatePaths) {
    events.push({
      timestamp: startedAt || "",
      kind: "artifact_written",
      label: `Prestate captured: ${p}`,
      payload: { path: p },
    });
  }

  for (const a of artifacts) {
    events.push({
      timestamp: a?.timestamp || finishedAt || startedAt || "",
      kind: "artifact_written",
      label: `Artifact: ${a?.path || "(unknown)"}`,
      payload: { path: a?.path || null, inferred_kind: a?.kind || null },
    });
  }

  if (finishedAt || startedAt) {
    events.push({
      timestamp: finishedAt || startedAt || "",
      kind: "completed",
      label: `Completed: ${receipt?.status || "unknown"}`,
      payload: {
        status: receipt?.status || null,
        started_at: receipt?.started_at || null,
        finished_at: receipt?.finished_at || null,
        execution_id: receipt?.execution_id || data?.execution_id || null,
        plan_hash: receipt?.plan_hash || approval?.plan_hash || null,
      },
    });
  }

  // Sort events by timestamp if available, stable fallback to label.
  const toMs = (iso) => {
    const t = Date.parse(String(iso || ""));
    return Number.isFinite(t) ? t : null;
  };

  return events
    .map((e, idx) => ({ ...e, _idx: idx, _ms: toMs(e.timestamp) }))
    .sort((a, b) => {
      if (a._ms !== null && b._ms !== null) return a._ms - b._ms;
      if (a._ms !== null) return -1;
      if (b._ms !== null) return 1;
      return String(a.label).localeCompare(String(b.label));
    })
    .map(({ _idx, _ms, ...rest }) => rest);
}

async function fetchExecution(executionId) {
  const r = await fetch(`/api/execution/${encodeURIComponent(executionId)}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

async function fetchJsonFile(pathRel) {
  const r = await fetch(`/api/file?path=${encodeURIComponent(pathRel)}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

export default function ExecutionTimeline() {
  const { executionId } = useParams();
  const [searchParams] = useSearchParams();

  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  const [selectedIdx, setSelectedIdx] = useState(0);
  const [detail, setDetail] = useState(null);
  const [detailErr, setDetailErr] = useState(null);

  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState(null);
  const [exportResult, setExportResult] = useState(null);
  const [zipSha256, setZipSha256] = useState(null);
  const [zipShaErr, setZipShaErr] = useState(null);
  const [zipShaComputing, setZipShaComputing] = useState(false);

  const returnTab = searchParams.get("tab") || "runs";

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const r = await fetchExecution(executionId);
        if (!alive) return;
        setData(r);
      } catch (e) {
        if (!alive) return;
        setErr(String(e));
      } finally {
        if (!alive) return;
        setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [executionId]);

  const events = useMemo(() => (data ? inferEvents(data) : []), [data]);

  useEffect(() => {
    // Keep selection in range.
    if (selectedIdx >= events.length) setSelectedIdx(0);
  }, [events.length, selectedIdx]);

  const selected = events[selectedIdx] || null;

  useEffect(() => {
    let alive = true;
    (async () => {
      setDetail(null);
      setDetailErr(null);
      if (!selected) return;

      const p = selected?.payload;
      const rel = p?.path;
      if (!rel) {
        setDetail(p || null);
        return;
      }

      try {
        const json = await fetchJsonFile(rel);
        if (!alive) return;
        setDetail(json);
      } catch (e) {
        if (!alive) return;
        // Not all artifacts are JSON; fall back to the payload itself.
        setDetail(p || null);
        setDetailErr(String(e));
      }
    })();

    return () => {
      alive = false;
    };
  }, [selected]);

  function copyDetail() {
    const text = JSON.stringify(detail ?? {}, null, 2);
    navigator.clipboard?.writeText(text).catch(() => {});
  }

  function downloadDetailAsJson() {
    const text = JSON.stringify(detail ?? {}, null, 2);
    const blob = new Blob([text], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${executionId}.${selected?.kind || "event"}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function exportAuditBundle() {
    setExporting(true);
    setExportErr(null);
    setExportResult(null);
    setZipSha256(null);
    setZipShaErr(null);
    setZipShaComputing(false);

    try {
      const r = await fetch("/api/audit/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ execution_id: executionId }),
      });
      const json = await r.json().catch(() => null);
      if (!r.ok) {
        throw new Error(json?.error ? String(json.error) : `HTTP ${r.status}`);
      }
      if (!json?.ok) {
        throw new Error(json?.error ? String(json.error) : "audit export failed");
      }
      setExportResult(json?.result || null);
      if (json?.result?.zip_path) {
        // Also copy a CLI-equivalent instruction for operator convenience.
        navigator.clipboard?.writeText(`/audit export ${executionId}`).catch(() => {});
      }
    } catch (e) {
      setExportErr(String(e));
    } finally {
      setExporting(false);
    }
  }

  async function computeZipSha256(zipPath) {
    const p = String(zipPath || "").trim();
    if (!p) return;
    if (!globalThis.crypto?.subtle) {
      setZipShaErr("WebCrypto unavailable (cannot compute SHA-256 in browser)");
      return;
    }

    setZipShaComputing(true);
    setZipShaErr(null);
    try {
      const r = await fetch(`/api/export?path=${encodeURIComponent(p)}`, {
        method: "GET",
        cache: "no-store",
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const buf = await r.arrayBuffer();
      const digest = await globalThis.crypto.subtle.digest("SHA-256", buf);
      const bytes = new Uint8Array(digest);
      const hex = Array.from(bytes)
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
      setZipSha256(hex);
    } catch (e) {
      setZipShaErr(String(e));
    } finally {
      setZipShaComputing(false);
    }
  }

  const zipFileName = useMemo(() => {
    const p = String(exportResult?.zip_path || "");
    if (!p) return null;
    const parts = p.split("/").filter(Boolean);
    return parts.length ? parts[parts.length - 1] : p;
  }, [exportResult?.zip_path]);

  const verifyCommand = useMemo(() => {
    const zip = String(exportResult?.zip_path || "").trim();
    if (zip) {
      return `node scripts/verify.js \"${zip.replace(/\"/g, "\\\"")}\" --strict --json`;
    }

    const dir = String(exportResult?.export_dir || "").trim();
    if (dir) {
      return `node scripts/verify.js \"${dir.replace(/\"/g, "\\\"")}\" --strict --json`;
    }

    return null;
  }, [exportResult?.zip_path, exportResult?.export_dir]);

  const header = (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
      <div>
        <div style={{ fontWeight: 900, fontSize: 18 }}>Execution Timeline</div>
        <div style={{ opacity: 0.75 }}>{executionId}</div>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link to={`/?tab=${encodeURIComponent(returnTab)}`} style={{ color: "#9ecbff" }}>
          ← Back
        </Link>
        <button onClick={exportAuditBundle} disabled={exporting} style={{ padding: "6px 10px" }}>
          {exporting ? "Exporting…" : "Export audit bundle"}
        </button>
        <button
          onClick={() => navigator.clipboard?.writeText(executionId).catch(() => {})}
          style={{ padding: "6px 10px" }}
        >
          Copy ID
        </button>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div>
        {header}
        <div style={{ marginTop: 12, opacity: 0.75 }}>Loading…</div>
      </div>
    );
  }

  if (err) {
    return (
      <div>
        {header}
        <div style={{ marginTop: 12, color: "crimson" }}>{err}</div>
      </div>
    );
  }

  return (
    <div>
      {header}
      {(exportErr || exportResult) && (
        <div style={{ marginTop: 10, padding: 10, border: "1px solid #333", borderRadius: 12 }}>
          {exportErr && <div style={{ color: "crimson" }}>{exportErr}</div>}
          {exportResult && (
            <div style={{ display: "grid", gap: 10 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <div style={{ fontWeight: 800 }}>Audit bundle ready</div>
                {zipFileName && <div style={{ opacity: 0.9 }}>File: <code>{zipFileName}</code></div>}
                {exportResult?.zip_path && (
                  <a
                    href={`/api/export?path=${encodeURIComponent(exportResult.zip_path)}`}
                    style={{ color: "#9ecbff" }}
                  >
                    Download zip
                  </a>
                )}
              </div>

              <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                {verifyCommand && (
                  <>
                    <button onClick={() => navigator.clipboard?.writeText(verifyCommand).catch(() => {})}>
                      Copy verify command
                    </button>
                    <div style={{ opacity: 0.8 }}><code>{verifyCommand}</code></div>
                  </>
                )}

                {exportResult?.export_dir && (
                  <button onClick={() => navigator.clipboard?.writeText(String(exportResult.export_dir)).catch(() => {})}>
                    Copy export dir
                  </button>
                )}
              </div>

              {exportResult?.zip_path && (
                <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                  <div style={{ fontWeight: 700 }}>SHA-256</div>
                  {zipShaErr && <div style={{ color: "crimson" }}>{zipShaErr}</div>}
                  {zipSha256 && (
                    <>
                      <code>{zipSha256.slice(0, 8)}</code>
                      <button onClick={() => navigator.clipboard?.writeText(zipSha256).catch(() => {})}>
                        Copy full SHA-256
                      </button>
                    </>
                  )}
                  {!zipSha256 && (
                    <button
                      onClick={() => computeZipSha256(exportResult.zip_path)}
                      disabled={zipShaComputing}
                    >
                      {zipShaComputing ? "Computing…" : "Compute checksum"}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, alignItems: "start" }}>
        <div style={{ border: "1px solid #333", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ padding: 10, borderBottom: "1px solid #222", fontWeight: 800 }}>Timeline</div>
          <div style={{ maxHeight: "70vh", overflow: "auto" }}>
            {events.map((e, idx) => {
              const active = idx === selectedIdx;
              const color = classifyEventColor(e.kind, e.payload);
              return (
                <div
                  key={idx}
                  onClick={() => setSelectedIdx(idx)}
                  style={{
                    padding: 10,
                    cursor: "pointer",
                    borderBottom: "1px solid #222",
                    background: active ? "#141414" : "transparent",
                    display: "grid",
                    gridTemplateColumns: "14px 1fr",
                    gap: 10,
                    alignItems: "start",
                  }}
                >
                  <div style={{ width: 10, height: 10, borderRadius: 999, background: color, marginTop: 3 }} />
                  <div>
                    <div style={{ fontWeight: 800 }}>{e.label}</div>
                    <div style={{ opacity: 0.75, fontSize: 12 }}>{e.timestamp || "(no timestamp)"}</div>
                  </div>
                </div>
              );
            })}
            {!events.length && <div style={{ padding: 12, opacity: 0.7 }}>No timeline events found.</div>}
          </div>
        </div>

        <div style={{ border: "1px solid #333", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ padding: 10, borderBottom: "1px solid #222", display: "flex", justifyContent: "space-between" }}>
            <div style={{ fontWeight: 800 }}>Details</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button onClick={copyDetail} disabled={!detail}>
                Copy
              </button>
              <button onClick={downloadDetailAsJson} disabled={!detail}>
                Download JSON
              </button>
              {selected?.payload?.path && (
                <a
                  href={`/api/raw?path=${encodeURIComponent(selected.payload.path)}`}
                  style={{ color: "#9ecbff", alignSelf: "center" }}
                >
                  Download raw
                </a>
              )}
            </div>
          </div>
          {detailErr && <div style={{ padding: 10, color: "#d4a017" }}>Note: {detailErr}</div>}
          <div style={{ padding: 10 }}>
            <JsonViewer value={detail || selected?.payload || { note: "Select an event" }} />
          </div>
        </div>
      </div>
    </div>
  );
}
