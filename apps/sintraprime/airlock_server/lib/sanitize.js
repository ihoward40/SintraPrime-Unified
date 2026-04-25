export function sanitizeReceipt(payload) {
  const copy = JSON.parse(JSON.stringify(payload));
  
  // Strip base64 file bodies before forwarding/storing in Notion
  if (Array.isArray(copy.files)) {
    copy.files = copy.files.map(f => ({
      name: f.name,
      mime: f.mime,
      bytes: f.bytes,
      sha256: f.sha256
    }));
  }
  
  return copy;
}
