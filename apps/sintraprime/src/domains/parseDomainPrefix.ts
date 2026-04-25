export type DomainPrefixParseResult = {
  domain_id: string;
  inner_command: string;
  original_command: string;
};

export function parseDomainPrefix(command: string): DomainPrefixParseResult | null {
  const trimmed = String(command ?? "").trim();
  const m = trimmed.match(/^\/domain\s+(\S+)\s+([\s\S]+)$/i);
  if (!m?.[1] || !m?.[2]) return null;

  const domain_id = String(m[1]).trim();
  const inner_command = String(m[2]).trim();

  if (!domain_id || !inner_command) return null;

  return {
    domain_id,
    inner_command,
    original_command: trimmed,
  };
}
