export async function callMake(endpoint: string, body: any) {
  const base = process.env.MAKE_BASE_URL || "https://api.make.com/v2";
  const token = process.env.MAKE_API_TOKEN;
  if (!token) throw new Error("MAKE_API_TOKEN not set");

  const url = `${base}${endpoint}`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Make API error: ${res.status} ${text}`);
  }
  return res.json();
}
