/**
 * Credit Dispute Prompts
 * 
 * Prompt templates for AI-powered dispute letter generation
 */

export interface DisputeData {
  id: string;
  beneficiary_id: string;
  creditor_name: string;
  dispute_reason: string;
  dispute_type: 'identity_theft' | 'not_mine' | 'inaccurate' | 'duplicate' | 'paid' | 'other';
  status: string;
  account_number?: string;
  amount?: number;
  date_opened?: string;
}

export interface BeneficiaryInfo {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  address?: string;
}

/**
 * Generate prompt for dispute letter
 */
export function getDisputeLetterPrompt(
  dispute: DisputeData,
  beneficiary: BeneficiaryInfo
): string {
  return `Generate a professional credit dispute letter with the following information:

Beneficiary Information:
- Name: ${beneficiary.first_name} ${beneficiary.last_name}
- Email: ${beneficiary.email}
- Phone: ${beneficiary.phone || 'Not provided'}
${beneficiary.address ? `- Address: ${beneficiary.address}` : ''}

Dispute Information:
- Creditor: ${dispute.creditor_name}
- Dispute Type: ${dispute.dispute_type}
- Reason: ${dispute.dispute_reason}
${dispute.account_number ? `- Account Number: ${dispute.account_number}` : ''}
${dispute.amount ? `- Amount: $${dispute.amount}` : ''}
${dispute.date_opened ? `- Date Opened: ${dispute.date_opened}` : ''}

Requirements:
1. Use professional business letter format
2. Include proper legal language for credit disputes
3. Reference Fair Credit Reporting Act (FCRA) rights
4. Request investigation and removal of inaccurate information
5. Request written confirmation of results
6. Include a 30-day response deadline
7. Be firm but professional in tone

The letter should be ready to print and mail to the credit bureau.`;
}

/**
 * Generate prompt for dispute analysis
 */
export function getDisputeAnalysisPrompt(dispute: DisputeData): string {
  return `Analyze this credit dispute and provide strategic guidance:

Dispute Details:
- Creditor: ${dispute.creditor_name}
- Type: ${dispute.dispute_type}
- Reason: ${dispute.dispute_reason}
- Current Status: ${dispute.status}

Provide:
1. Strength of the dispute case (Strong/Moderate/Weak)
2. Key legal points to emphasize
3. Required documentation
4. Estimated timeline for resolution
5. Likelihood of successful removal
6. Alternative strategies if initial dispute fails
7. Red flags or concerns

Be specific and actionable.`;
}

/**
 * Generate prompt for follow-up letter
 */
export function getFollowUpLetterPrompt(
  dispute: DisputeData,
  beneficiary: BeneficiaryInfo,
  daysSinceInitial: number
): string {
  return `Generate a follow-up letter for a credit dispute that was filed ${daysSinceInitial} days ago:

Original Dispute:
- Creditor: ${dispute.creditor_name}
- Type: ${dispute.dispute_type}
- Reason: ${dispute.dispute_reason}

Beneficiary: ${beneficiary.first_name} ${beneficiary.last_name}

Requirements:
1. Reference the original dispute letter and date
2. Note that the 30-day response period has ${daysSinceInitial > 30 ? 'expired' : 'not been met'}
3. Request immediate action and written response
4. Cite FCRA violation if applicable (over 30 days)
5. Maintain professional but firm tone
6. Include threat of escalation to CFPB if appropriate

The letter should be ready to print and mail.`;
}

/**
 * Generate prompt for dispute success probability
 */
export function getSuccessProbabilityPrompt(dispute: DisputeData): string {
  return `Assess the probability of success for this credit dispute:

Dispute Type: ${dispute.dispute_type}
Creditor: ${dispute.creditor_name}
Reason: ${dispute.dispute_reason}

Provide:
1. Success probability percentage (0-100%)
2. Key factors affecting success
3. Strongest arguments in favor
4. Potential challenges
5. Recommended approach
6. Timeline estimate

Base your assessment on typical credit dispute outcomes and FCRA provisions.`;
}

/**
 * Generate prompt for bulk dispute strategy
 */
export function getBulkDisputeStrategyPrompt(disputes: DisputeData[]): string {
  const summary = disputes.map((d, i) => 
    `${i + 1}. ${d.creditor_name} - ${d.dispute_type}`
  ).join('\n');

  return `Develop a strategy for handling multiple credit disputes:

Disputes to Address (${disputes.length} total):
${summary}

Provide:
1. Recommended filing order (which disputes to prioritize)
2. Grouping strategy (which can be filed together)
3. Timeline for filing (spacing between disputes)
4. Resource requirements
5. Expected outcomes
6. Risk assessment for bulk filing

Consider the impact on credit score and the strategic advantage of the filing order.`;
}

/**
 * Generate prompt for creditor-specific strategy
 */
export function getCreditorStrategyPrompt(creditorName: string, disputeHistory: DisputeData[]): string {
  return `Analyze dispute history with ${creditorName} and develop a targeted strategy:

Previous Disputes with ${creditorName}:
${disputeHistory.map((d, i) => 
  `${i + 1}. ${d.dispute_type} - Status: ${d.status}`
).join('\n')}

Provide:
1. Pattern analysis of previous disputes
2. Creditor's typical response behavior
3. Most effective dispute types for this creditor
4. Recommended approach for new disputes
5. Escalation tactics if needed
6. Alternative resolution methods

Be specific to this creditor's known practices.`;
}
