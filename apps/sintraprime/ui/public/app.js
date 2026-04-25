const out = document.getElementById("out");

async function api(p) {
  const r = await fetch(p);
  return r.json();
}

async function cmd(message) {
  const r = await fetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return r.json();
}

async function show(tab) {
  if (tab === "approvals") {
    out.textContent = JSON.stringify(await api("/api/approvals"), null, 2);
  }
  if (tab === "runs") {
    out.textContent = JSON.stringify(await api("/api/receipts"), null, 2);
  }
  if (tab === "artifacts") {
    out.textContent = JSON.stringify(await api("/api/artifacts"), null, 2);
  }
  if (tab === "scheduler") {
    out.textContent = JSON.stringify(await cmd("/scheduler history"), null, 2);
  }
}
