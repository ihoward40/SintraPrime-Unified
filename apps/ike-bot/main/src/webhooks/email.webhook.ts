import { Request, Response } from 'express';
import { supabase } from '../config/supabase';

/**
 * Handle webhooks from email providers (SendGrid, Postmark)
 */

// SendGrid webhook handler
export const handleSendGridWebhook = async (req: Request, res: Response) => {
  try {
    const events = req.body;

    if (!Array.isArray(events)) {
      return res.status(400).json({ error: 'Invalid payload format' });
    }

    console.log(`SendGrid webhook received: ${events.length} events`);

    for (const event of events) {
      await processSendGridEvent(event);
    }

    res.json({ success: true });
  } catch (error: any) {
    console.error('Error processing SendGrid webhook:', error);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
};

async function processSendGridEvent(event: any) {
  // Log the event
  await supabase.from('agent_logs').insert({
    trace_id: crypto.randomUUID(),
    level: 'info',
    message: `SendGrid event: ${event.event}`,
    action: 'email_event',
    metadata: {
      event_type: event.event,
      email: event.email,
      timestamp: event.timestamp,
      sg_event_id: event.sg_event_id,
    },
  });

  // Handle specific event types
  switch (event.event) {
    case 'delivered':
      console.log(`Email delivered to: ${event.email}`);
      break;
    case 'bounce':
    case 'dropped':
      console.log(`Email failed for: ${event.email} - ${event.reason}`);
      break;
    case 'open':
      console.log(`Email opened by: ${event.email}`);
      break;
    case 'click':
      console.log(`Email link clicked by: ${event.email}`);
      break;
  }
}

// Postmark webhook handler
export const handlePostmarkWebhook = async (req: Request, res: Response) => {
  try {
    const event = req.body;

    console.log('Postmark webhook received:', event.RecordType);

    await processPostmarkEvent(event);

    res.json({ success: true });
  } catch (error: any) {
    console.error('Error processing Postmark webhook:', error);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
};

async function processPostmarkEvent(event: any) {
  // Log the event
  await supabase.from('agent_logs').insert({
    trace_id: crypto.randomUUID(),
    level: 'info',
    message: `Postmark event: ${event.RecordType}`,
    action: 'email_event',
    metadata: {
      record_type: event.RecordType,
      email: event.Email,
      message_id: event.MessageID,
      tag: event.Tag,
    },
  });

  // Handle specific record types
  switch (event.RecordType) {
    case 'Delivery':
      console.log(`Email delivered to: ${event.Email}`);
      break;
    case 'Bounce':
      console.log(`Email bounced for: ${event.Email} - ${event.Description}`);
      break;
    case 'Open':
      console.log(`Email opened by: ${event.Email}`);
      break;
    case 'Click':
      console.log(`Email link clicked by: ${event.Email}`);
      break;
  }
}

// Generic inbound email handler (for both SendGrid and Postmark)
export const handleInboundEmail = async (req: Request, res: Response) => {
  try {
    const email = req.body;

    console.log('Inbound email received from:', email.from || email.From);

    // Log the inbound email
    await supabase.from('agent_logs').insert({
      trace_id: crypto.randomUUID(),
      level: 'info',
      message: 'Inbound email received',
      action: 'inbound_email',
      metadata: {
        from: email.from || email.From,
        to: email.to || email.To,
        subject: email.subject || email.Subject,
        timestamp: new Date().toISOString(),
      },
    });

    // Here you could add logic to:
    // - Parse email content
    // - Extract attachments
    // - Create billing events or disputes from email content
    // - Trigger automation workflows

    res.json({ success: true, message: 'Inbound email processed' });
  } catch (error: any) {
    console.error('Error processing inbound email:', error);
    res.status(500).json({ error: 'Email processing failed' });
  }
};
