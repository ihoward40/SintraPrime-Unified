import type { Tool } from '../../types/index.js';
import {
  browserL0DomExtract,
  browserL0Navigate,
  browserL0Screenshot,
} from '../../browserOperator/l0.js';

export class BrowserL0Tool implements Tool {
  name = 'browser.l0';
  description = 'Evidence-producing, allowlisted browser navigation, screenshot, and DOM extraction. No form submission or mutation.';

  async execute(args: any): Promise<any> {
    const operation = String(args?.operation ?? '').trim();
    const input = {
      execution_id: String(args?.execution_id ?? `amr_${Date.now()}`),
      step_id: String(args?.step_id ?? `step_${Date.now()}`),
      url: String(args?.url ?? ''),
      timeoutMs: Number(args?.timeoutMs ?? 30_000),
    };

    if (!input.url) throw new Error('browser.l0 requires url');

    switch (operation) {
      case 'navigate':
        return browserL0Navigate(input);
      case 'screenshot':
        return browserL0Screenshot({ ...input, fullPage: args?.fullPage !== false });
      case 'extract':
        return browserL0DomExtract({ ...input, maxChars: Number(args?.maxChars ?? 250_000) });
      default:
        throw new Error(`Unsupported browser.l0 operation: ${operation}`);
    }
  }
}
