import { Router } from 'express';
import { asyncHandler } from '../middleware/errorHandler';
import { handleStripeWebhook } from '../webhooks/stripe.webhook';
import { handleMakeWebhook } from '../webhooks/make.webhook';
import { 
  handleSendGridWebhook, 
  handlePostmarkWebhook, 
  handleInboundEmail 
} from '../webhooks/email.webhook';
import { handleBillingAlert } from '../webhooks/billing.webhook';
import express from 'express';

const router = Router();

// Stripe webhook requires raw body for signature verification
router.post(
  '/stripe',
  express.raw({ type: 'application/json' }),
  asyncHandler(handleStripeWebhook)
);

// Make.com webhook
router.post('/make', asyncHandler(handleMakeWebhook));

// Email provider webhooks
router.post('/sendgrid', asyncHandler(handleSendGridWebhook));
router.post('/postmark', asyncHandler(handlePostmarkWebhook));
router.post('/inbound-email', asyncHandler(handleInboundEmail));

// Generic billing alert webhook
router.post('/billing-alert', asyncHandler(handleBillingAlert));

export default router;
