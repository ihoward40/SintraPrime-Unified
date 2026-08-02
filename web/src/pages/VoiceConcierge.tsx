import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Mic, ShieldCheck, RefreshCw, Send, XCircle, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge, { BadgeVariant } from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { voiceApi, VoiceCommandResponse, VoiceSource } from '../api/voice';

/**
 * SP-VOICE-001 Increment Two — Voice Concierge panel.
 *
 * Mock/sandbox only: every command submitted here is classified, policy
 * checked, and (if allowed) executed against a mock provider — never a real
 * phone, calendar, messaging, filing, or payment backend. Voice requests and
 * coordinates; existing SintraPrime policy decides, records, approves,
 * executes, or refuses.
 */

const STATE_BADGE: Record<string, BadgeVariant> = {
  planning: 'blue',
  awaiting_confirmation: 'amber',
  executing: 'blue',
  completed: 'green',
  refused: 'red',
  cancelled: 'slate',
  failed: 'red',
};

const RESULT_ICON: Record<string, React.ElementType> = {
  completed: CheckCircle2,
  refused: XCircle,
  cancelled: XCircle,
  failed: AlertTriangle,
};

function StateBadge({ state }: { state: string }) {
  return (
    <Badge variant={STATE_BADGE[state] ?? 'slate'} size="sm">
      {state.replace(/_/g, ' ')}
    </Badge>
  );
}

export default function VoiceConcierge() {
  const [transcript, setTranscript] = useState('');
  const [source, setSource] = useState<VoiceSource>('desktop_voice');
  const [commands, setCommands] = useState<VoiceCommandResponse[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await voiceApi.list();
      setCommands(next);
      setError('');
    } catch {
      setError('Voice command ledger is unavailable. No commands are being inferred.');
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 15_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const submit = async () => {
    if (!transcript.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      await voiceApi.submit({ raw_transcript: transcript.trim(), source });
      setTranscript('');
      await refresh();
    } catch {
      setError('Unable to submit the voice command. It was not recorded.');
    } finally {
      setSubmitting(false);
    }
  };

  const confirm = async (commandId: string, utterance: string) => {
    setBusyId(commandId);
    try {
      await voiceApi.confirm(commandId, { utterance });
      await refresh();
    } catch {
      setError(`Unable to resolve confirmation for ${commandId}.`);
    } finally {
      setBusyId(null);
    }
  };

  const cancel = async (commandId: string) => {
    setBusyId(commandId);
    try {
      await voiceApi.cancel(commandId);
      await refresh();
    } catch {
      setError(`Unable to cancel ${commandId}.`);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-slate-100">
            <Mic className="h-5 w-5 text-gold" /> Voice Concierge
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            SP-VOICE-001 — governed, mock-first voice operations. All actions below execute against
            sandboxed mock providers only; nothing here places a real call, sends a real message,
            books a real calendar event, files a real document, or moves real money.
          </p>
        </div>
        <Badge variant="green" dot>
          <ShieldCheck className="h-3 w-3" /> Mock / sandbox only
        </Badge>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
          <AlertTriangle className="h-4 w-4" /> {error}
        </div>
      )}

      <Card>
        <CardHeader
          title="Submit a voice command"
          subtitle="Simulates a transcribed utterance. Governed by risk classification, policy, and confirmation rules."
        />
        <div className="flex flex-col gap-3 sm:flex-row">
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="e.g. schedule a mock follow-up call with the client"
            maxLength={8000}
            rows={2}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-900/60 p-3 text-sm text-slate-200 placeholder:text-slate-500 focus:border-gold/50 focus:outline-none"
          />
          <div className="flex flex-col gap-2 sm:w-48">
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as VoiceSource)}
              className="rounded-lg border border-slate-700 bg-slate-900/60 p-2 text-sm text-slate-200 focus:border-gold/50 focus:outline-none"
            >
              <option value="desktop_voice">Desktop voice</option>
              <option value="mobile_voice">Mobile voice</option>
              <option value="telephony">Telephony (mock)</option>
              <option value="text_fallback">Text fallback</option>
            </select>
            <Button icon={Send} onClick={submit} loading={submitting} disabled={!transcript.trim()}>
              Submit
            </Button>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Command ledger"
          subtitle="Tenant-scoped, hash-chained lifecycle of every submitted voice command."
          action={
            <Button variant="ghost" size="sm" icon={RefreshCw} onClick={refresh}>
              Refresh
            </Button>
          }
        />
        {commands.length === 0 ? (
          <div className="py-8 text-center text-sm text-slate-500">No voice commands yet.</div>
        ) : (
          <div className="space-y-3">
            {commands.map((cmd) => {
              const ResultIcon = RESULT_ICON[cmd.session_state] ?? Clock;
              const awaiting = cmd.session_state === 'awaiting_confirmation';
              return (
                <div
                  key={cmd.command_id}
                  className="rounded-lg border border-slate-800 bg-slate-900/40 p-4"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-200">{cmd.normalized_intent}</p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {cmd.command_id} · {cmd.risk_class} · {cmd.resolved_capability}
                        {cmd.target_resource ? ` · ${cmd.target_resource}` : ''}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <ResultIcon className="h-4 w-4 text-slate-400" />
                      <StateBadge state={cmd.session_state} />
                    </div>
                  </div>

                  {cmd.reason && <p className="mt-2 text-xs text-slate-500">{cmd.reason}</p>}

                  {cmd.provider_mock !== null && (
                    <p className="mt-2 text-xs text-emerald-400/80">
                      Mock provider result{cmd.provider_resource_id ? ` · ${cmd.provider_resource_id}` : ''}
                    </p>
                  )}

                  {awaiting && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="success"
                        loading={busyId === cmd.command_id}
                        onClick={() => confirm(cmd.command_id, 'yes')}
                      >
                        Confirm
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        loading={busyId === cmd.command_id}
                        onClick={() => confirm(cmd.command_id, 'no')}
                      >
                        Deny
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        loading={busyId === cmd.command_id}
                        onClick={() => cancel(cmd.command_id)}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}

                  {!awaiting && !['completed', 'refused', 'cancelled', 'failed'].includes(cmd.session_state) && (
                    <div className="mt-3">
                      <Button
                        size="sm"
                        variant="ghost"
                        loading={busyId === cmd.command_id}
                        onClick={() => cancel(cmd.command_id)}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </motion.div>
  );
}
