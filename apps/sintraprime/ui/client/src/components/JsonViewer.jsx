import React from "react";

export default function JsonViewer({ value }) {
  return (
    <pre
      style={{
        background: "#0b0b0b",
        color: "#00ff66",
        padding: 12,
        borderRadius: 12,
        overflow: "auto",
        minHeight: 220,
      }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
