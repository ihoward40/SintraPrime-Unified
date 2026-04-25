export async function getApprovals() {
  const r = await fetch("/api/approvals");
  return r.json();
}

export async function getReceipts(limit = 200) {
  const r = await fetch(`/api/receipts?limit=${encodeURIComponent(limit)}`);
  return r.json();
}

export async function getArtifacts(prefix = "") {
  const r = await fetch(`/api/artifacts?prefix=${encodeURIComponent(prefix)}`);
  return r.json();
}

export async function getFile(relPath) {
  const r = await fetch(`/api/file?path=${encodeURIComponent(relPath)}`);
  return r.json();
}

export async function sendCommand(message) {
  const r = await fetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return r.json();
}
