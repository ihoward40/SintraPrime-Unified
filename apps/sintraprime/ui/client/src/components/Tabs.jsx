import React from "react";

export default function Tabs({ tabs, active, onChange }) {
  return (
    <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          style={{
            padding: "8px 10px",
            borderRadius: 10,
            border: "1px solid #333",
            background: t.id === active ? "#111" : "#fff",
            color: t.id === active ? "#0f0" : "#111",
            cursor: "pointer",
          }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
