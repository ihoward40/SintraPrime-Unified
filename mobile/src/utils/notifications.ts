import * as Notifications from 'expo-notifications';
import { addDays } from 'date-fns';

export type NotificationType =
  | 'case_deadline'
  | 'new_caselaw'
  | 'credit_change'
  | 'large_transaction'
  | 'ai_parliament'
  | 'document_expiring'
  | 'general';

export async function scheduleDeadlineAlert(
  caseTitle: string,
  deadlineDate: Date,
  caseId: string,
): Promise<void> {
  const sevenDaysBefore = addDays(deadlineDate, -7);
  const oneDayBefore = addDays(deadlineDate, -1);
  const now = new Date();

  if (sevenDaysBefore > now) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: '⚖️ Deadline in 7 Days',
        body: `${caseTitle} has a deadline in 7 days. Review your case.`,
        data: { type: 'case_deadline', caseId },
        color: '#D4AF37',
      },
      trigger: { date: sevenDaysBefore },
    });
  }

  if (oneDayBefore > now) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: '🚨 Deadline Tomorrow',
        body: `URGENT: ${caseTitle} has a deadline tomorrow!`,
        data: { type: 'case_deadline', caseId },
        color: '#EF4444',
      },
      trigger: { date: oneDayBefore },
    });
  }
}

export async function sendCreditAlertNotification(
  previousScore: number,
  newScore: number,
): Promise<void> {
  const change = newScore - previousScore;
  const direction = change > 0 ? 'increased' : 'decreased';
  const emoji = change > 0 ? '📈' : '📉';

  await Notifications.scheduleNotificationAsync({
    content: {
      title: `${emoji} Credit Score Update`,
      body: `Your credit score has ${direction} by ${Math.abs(change)} points to ${newScore}.`,
      data: { type: 'credit_change', change, newScore },
      color: change > 0 ? '#22C55E' : '#EF4444',
    },
    trigger: null,
  });
}

export async function sendLargeTransactionAlert(
  description: string,
  amount: number,
): Promise<void> {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: '💰 Large Transaction Detected',
      body: `${description}: $${Math.abs(amount).toFixed(2)}`,
      data: { type: 'large_transaction', amount },
      color: '#F59E0B',
    },
    trigger: null,
  });
}
