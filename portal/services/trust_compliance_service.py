
import os
import re
from typing import List, Dict

class TrustComplianceService:
    def __init__(self):
        self.risk_tags = self._load_policy_data("apps/sintraprime/src/modules/trust-compliance/policies/risk-tags.ts", "RISK_TAG_DEFINITIONS")
        self.safety_gates = self._load_policy_data("apps/sintraprime/src/modules/trust-compliance/policies/safety-gates.ts", "SAFETY_GATE_DEFINITIONS")
        self.forbidden_phrases = self._load_policy_data("apps/sintraprime/src/modules/trust-compliance/policies/forbidden-phrases.ts", "FORBIDDEN_PHRASES")

    def _read_file_content(self, file_path: str) -> str:
        full_path = os.path.join("/tmp/sp_task", file_path)
        try:
            with open(full_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Policy file not found: {full_path}")
            return ""

    def _load_policy_data(self, file_path: str, var_name: str) -> List[str]:
        content = self._read_file_content(file_path)
        policies = []

        if var_name == "RISK_TAG_DEFINITIONS":
            match = re.search(r'export const RISK_TAG_DEFINITIONS: Record<RiskTag, string> = {([^}]+)};', content, re.DOTALL)
            if match:
                keys_content = match.group(1)
                policies = [key.strip() for key in re.findall(r'(\w+):', keys_content)]
        elif var_name == "SAFETY_GATE_DEFINITIONS":
            always_block_tags_match = re.search(r'const ALWAYS_BLOCK_TAGS: RiskTag\[\] = \[(\s*\'[^\]]+\'(?:,\s*\'[^\]]+\')*\s*)\];', content)
            if always_block_tags_match:
                policies.extend([item.strip().strip("\'") for item in always_block_tags_match.group(1).split(',') if item.strip()])
            rewrite_tags_match = re.search(r'const REWRITE_TAGS: RiskTag\[\] = \[(\s*\'[^\]]+\'(?:,\s*\'[^\]]+\')*\s*)\];', content)
            if rewrite_tags_match:
                policies.extend([item.strip().strip("\'") for item in rewrite_tags_match.group(1).split(',') if item.strip()])
        elif var_name == "FORBIDDEN_PHRASES":
            match = re.search(r'export const FORBIDDEN_PHRASES: ForbiddenPhrase\[\] = \[(\s*{[^}]+}(?:,\s*{[^}]+})*\s*)\];', content, re.DOTALL)
            if match:
                phrases_content = match.group(1)
                policies = [phrase.strip().strip("\'") for phrase in re.findall(r"phrase: \'([^\']+)\'", phrases_content)]
        return policies

    def analyze_document(self, document_text: str, document_type: str) -> Dict:
        triggered_risk_tags = []
        for tag in self.risk_tags:
            if tag.lower() in document_text.lower():
                triggered_risk_tags.append(tag)

        triggered_safety_gates = []
        for gate in self.safety_gates:
            if gate.lower() in document_text.lower():
                triggered_safety_gates.append(gate)

        forbidden_phrases_found = []
        for phrase in self.forbidden_phrases:
            if phrase.lower() in document_text.lower():
                forbidden_phrases_found.append(phrase)

        compliance_score = 1.0 - (len(triggered_risk_tags) * 0.1) - (len(forbidden_phrases_found) * 0.15)
        compliance_score = max(0.0, min(1.0, compliance_score))

        recommendations = []
        if compliance_score < 0.7:
            recommendations.append("Review document for compliance issues.")
        if triggered_risk_tags:
            recommendations.append(f"Address triggered risk tags: {', '.join(triggered_risk_tags)}.")
        if forbidden_phrases_found:
            recommendations.append(f"Remove or rephrase forbidden phrases: {', '.join(forbidden_phrases_found)}.")

        return {
            "risk_tags": triggered_risk_tags,
            "safety_gates": triggered_safety_gates,
            "compliance_score": compliance_score,
            "recommendations": recommendations
        }

    def get_policies(self) -> Dict:
        return {
            "risk_tags": self.risk_tags,
            "safety_gates": self.safety_gates,
            "forbidden_phrases": self.forbidden_phrases
        }

    def rewrite_document(self, document_text: str, risk_tags: List[str]) -> Dict:
        rewritten_text = document_text
        changes_made = []
        for tag in risk_tags:
            if tag in rewritten_text:
                rewritten_text = rewritten_text.replace(tag, "[REDACTED]")
                changes_made.append(f"Replaced '{tag}' with '[REDACTED]'")
        return {"rewritten_text": rewritten_text, "changes_made": changes_made}
