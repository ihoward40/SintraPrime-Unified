import React, { useMemo, useState } from "react";
import { Routes, Route, useSearchParams } from "react-router-dom";
import Tabs from "./components/Tabs.jsx";
import Inbox from "./views/Inbox.jsx";
import Runs from "./views/Runs.jsx";
import Artifacts from "./views/Artifacts.jsx";
import Scheduler from "./views/Scheduler.jsx";
import Autonomy from "./views/Autonomy.jsx";
import Audit from "./views/Audit.jsx";
import ExecutionTimeline from "./views/ExecutionTimeline.jsx";

function ConsoleHome() {
  const tabs = useMemo(
    () => [
      { id: "inbox", label: "Approvals", node: <Inbox /> },
      { id: "runs", label: "Runs", node: <Runs /> },
      { id: "artifacts", label: "Artifacts", node: <Artifacts /> },
      { id: "scheduler", label: "Scheduler", node: <Scheduler /> },
      { id: "autonomy", label: "Autonomy", node: <Autonomy /> },
      { id: "audit", label: "Audit", node: <Audit /> },
    ],
    []
  );

  const [searchParams] = useSearchParams();
  const initial = searchParams.get("tab") || "inbox";
  const [active, setActive] = useState(initial);
  const current = tabs.find((t) => t.id === active)?.node;

  return (
    <div
      style={{
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
        padding: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Operator Console</h2>
        <div style={{ opacity: 0.7 }}>UI forwards commands via /api/command</div>
      </div>
      <Tabs tabs={tabs} active={active} onChange={setActive} />
      <div style={{ marginTop: 12 }}>{current}</div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ConsoleHome />} />
      <Route path="/execution/:executionId" element={<ExecutionTimeline />} />
    </Routes>
  );
}
