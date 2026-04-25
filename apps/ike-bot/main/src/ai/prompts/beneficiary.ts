/**
 * Beneficiary Analysis Prompts
 * 
 * Prompt templates for AI-powered beneficiary analysis
 */

export interface BeneficiaryData {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  relationship: string;
  created_at: string;
  credit_disputes?: any[];
  billing_events?: any[];
}

/**
 * Generate prompt for beneficiary analysis
 */
export function getBeneficiaryAnalysisPrompt(beneficiary: BeneficiaryData): string {
  return `Analyze the following beneficiary profile and provide insights:

Beneficiary Information:
- Name: ${beneficiary.first_name} ${beneficiary.last_name}
- Email: ${beneficiary.email}
- Phone: ${beneficiary.phone || 'Not provided'}
- Relationship: ${beneficiary.relationship}
- Account Created: ${beneficiary.created_at}
- Credit Disputes: ${beneficiary.credit_disputes?.length || 0}
- Billing Events: ${beneficiary.billing_events?.length || 0}

Please provide:
1. A summary of the beneficiary's current status
2. Any patterns or concerns identified
3. Recommended next actions
4. Risk assessment (low, medium, high)
5. Priority level for follow-up

Format your response as a professional analysis suitable for case management.`;
}

/**
 * Generate prompt for portfolio analysis (multiple beneficiaries)
 */
export function getPortfolioAnalysisPrompt(beneficiaries: BeneficiaryData[]): string {
  const summary = beneficiaries.map((b, i) => 
    `${i + 1}. ${b.first_name} ${b.last_name} - ${b.relationship} - ${b.credit_disputes?.length || 0} disputes`
  ).join('\n');

  return `Analyze the following portfolio of beneficiaries and identify patterns:

Beneficiary Portfolio (${beneficiaries.length} total):
${summary}

Please provide:
1. Overall portfolio health assessment
2. Common patterns across beneficiaries
3. High-priority cases requiring immediate attention
4. Trends in credit disputes
5. Resource allocation recommendations
6. Potential systemic issues

Format your response as an executive summary suitable for management review.`;
}

/**
 * Generate prompt for beneficiary risk assessment
 */
export function getRiskAssessmentPrompt(beneficiary: BeneficiaryData): string {
  const disputeCount = beneficiary.credit_disputes?.length || 0;
  const recentDisputes = beneficiary.credit_disputes?.slice(0, 5) || [];

  return `Assess the risk level for this beneficiary:

Beneficiary: ${beneficiary.first_name} ${beneficiary.last_name}
Total Credit Disputes: ${disputeCount}

Recent Disputes:
${recentDisputes.map((d: any, i: number) => 
  `${i + 1}. ${d.creditor_name} - ${d.dispute_type} - Status: ${d.status}`
).join('\n') || 'None'}

Provide a risk assessment including:
1. Overall risk level (Low/Medium/High/Critical)
2. Key risk factors
3. Likelihood of escalation
4. Recommended monitoring frequency
5. Preventive measures

Be concise and actionable.`;
}

/**
 * Generate prompt for personalized communication
 */
export function getPersonalizedMessagePrompt(
  beneficiary: BeneficiaryData,
  messageType: 'welcome' | 'update' | 'alert' | 'reminder',
  context?: string
): string {
  const templates: Record<string, string> = {
    welcome: `Write a warm, professional welcome message for a new beneficiary named ${beneficiary.first_name}. Explain what they can expect from our trust automation services.`,
    update: `Write a status update message for ${beneficiary.first_name} ${beneficiary.last_name} about their account. Context: ${context || 'General update'}`,
    alert: `Write an important alert message for ${beneficiary.first_name} regarding: ${context || 'Account activity'}. Be clear and actionable.`,
    reminder: `Write a friendly reminder message for ${beneficiary.first_name} about: ${context || 'Pending action'}. Keep it brief and helpful.`,
  };

  return templates[messageType] || templates.update;
}

/**
 * Generate prompt for data extraction from unstructured text
 */
export function getDataExtractionPrompt(text: string): string {
  return `Extract beneficiary information from the following text:

${text}

Extract and structure the following information if present:
- First name
- Last name
- Email address
- Phone number
- Relationship type
- Any mentioned disputes or issues
- Important dates
- Action items

Return the information in a structured format. If information is not present, indicate "Not found".`;
}
