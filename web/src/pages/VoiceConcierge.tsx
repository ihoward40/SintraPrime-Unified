import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Mic,
  MicOff,
  RefreshCw,
  Send,
  ShieldCheck,
  Square,
  Volume2,
  VolumeX,
  XCircle,
} from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge, { BadgeVariant } from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { voiceApi, VoiceCommandResponse, VoiceSource } from '../api/voice';

/**
 * SP-VOICE-001 Increment Two — Voice Concierge panel.
 *
 * Mock/sandbox only: every command submitted here is classified, policy
 * checked, and (if allowed) executed against a mock provider — never a real
 * phone, calendar, messaging, filing, or payment backend. Browser microphone
 * input only creates a transcript preview; existing SintraPrime policy decides,
 * records, approves, executes, or refuses after explicit submission.
 */

type CaptureMode = 'desktop_voice' | 'remote_voice' | 'transcript_import';
type SpeechStatus = 'idle' | 'requesting_permission' | 'listening' | 'processing' | 'unsupported' | 'denied' | 'error';

type SpeechRecognitionErrorCode =
  | 'aborted'
  | 'audio-capture'
  | 'bad-grammar'
  | 'language-not-supported'
  | 'network'
  | 'no-speech'
  | 'not-allowed'
  | 'phrases-not-supported'
  | 'service-not-allowed';

interface SpeechRecognitionAlternative {
  transcript: string;
}

interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionResultList {
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  readonly error: SpeechRecognitionErrorCode;
  readonly message: string;
}

interface BrowserSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  abort(): void;
  start(): void;
  stop(): void;
}

interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: new () => BrowserSpeechRecognition;
  webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
}

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

const CAPTURE_OPTIONS: Array<{ value: CaptureMode; label: string; description: string }> = [
  { value: 'desktop_voice', label: 'Desktop voice', description: 'Browser microphone transcript' },
  { value: 'remote_voice', label: 'Telephony mock', description: 'Remote transcript simulation' },
  { value: 'transcript_import', label: 'Text fallback', description: 'Typed transcript import' },
];

function StateBadge({ state }: { state: string }) {
  return (
    <Badge variant={STATE_BADGE[state] ?? 'slate'} size="sm">
      {state.replace(/_/g, ' ')}
    </Badge>
  );
}

function getSpeechRecognitionConstructor() {
  if (typeof window === 'undefined') return undefined;
  const speechWindow = window as SpeechRecognitionWindow;
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
}

function buildConfirmationPrompt(command: VoiceCommandResponse): string {
  const target = command.target_resource ? ` for ${command.target_resource}` : '';
  return `Confirmation required. ${command.resolved_capability} is classified as ${command.risk_class}${target}. Review the ledger, then confirm, deny, or cancel.`;
}

function commandAnnouncementKey(command: VoiceCommandResponse): string {
  return `${command.command_id}:${command.session_state}:${command.provider_resource_id ?? ''}`;
}

function buildResultAnnouncement(command: VoiceCommandResponse): string | null {
  if (command.session_state === 'awaiting_confirmation') return buildConfirmationPrompt(command);
  if (command.session_state === 'completed') {
    const resource = command.provider_resource_id ? ` Receipt ${command.provider_resource_id}.` : '';
    return `Mock command completed.${resource}`;
  }
  if (command.session_state === 'refused') return `Command refused. ${command.reason ?? 'Policy did not allow execution.'}`;
  if (command.session_state === 'cancelled') return 'Command cancelled.';
  if (command.session_state === 'failed') return `Command failed. ${command.reason ?? 'Review the ledger for details.'}`;
  return null;
}

export default function VoiceConcierge() {
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [captureMode, setCaptureMode] = useState<CaptureMode>('desktop_voice');
  const [commands, setCommands] = useState<VoiceCommandResponse[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [speechStatus, setSpeechStatus] = useState<SpeechStatus>('idle');
  const [speechMessage, setSpeechMessage] = useState('');
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const shouldStopRef = useRef(false);
  const announcedStatesRef = useRef<Set<string>>(new Set());

  const speechSupported = useMemo(() => Boolean(getSpeechRecognitionConstructor()), []);
  const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const transcriptPreview = `${transcript}${interimTranscript ? ` ${interimTranscript}` : ''}`.trim();

  const speak = useCallback(
    (message: string) => {
      if (!ttsEnabled || !ttsSupported || !message.trim()) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.rate = 0.95;
      utterance.pitch = 1;
      window.speechSynthesis.speak(utterance);
    },
    [ttsEnabled, ttsSupported],
  );

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

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      if (ttsSupported) window.speechSynthesis.cancel();
    };
  }, [ttsSupported]);

  const announceCommand = useCallback(
    (command: VoiceCommandResponse) => {
      const announcement = buildResultAnnouncement(command);
      if (!announcement) return false;

      const key = commandAnnouncementKey(command);
      if (announcedStatesRef.current.has(key)) return false;

      announcedStatesRef.current.add(key);
      speak(announcement);
      return true;
    },
    [speak],
  );

  const handleCommandsChanged = useCallback(
    (nextCommands: VoiceCommandResponse[]) => {
      for (const command of nextCommands) {
        if (announceCommand(command)) break;
      }
    },
    [announceCommand],
  );

  useEffect(() => {
    handleCommandsChanged(commands);
  }, [commands, handleCommandsChanged]);

  const startListening = async () => {
    const Recognition = getSpeechRecognitionConstructor();
    if (!Recognition) {
      setSpeechStatus('unsupported');
      setSpeechMessage('Browser speech recognition is not available. Use text fallback.');
      return;
    }

    recognitionRef.current?.abort();
    shouldStopRef.current = false;
    setError('');
    setSpeechStatus('requesting_permission');
    setSpeechMessage('Requesting microphone permission. Audio stays in the browser speech service; only transcript text is submitted.');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
    } catch {
      setSpeechStatus('denied');
      setSpeechMessage('Microphone permission was denied or unavailable. Use text fallback or allow microphone access.');
      return;
    }

    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.onstart = () => {
      setSpeechStatus('listening');
      setSpeechMessage('Listening. Release stop, then review the transcript before submitting.');
    };
    recognition.onresult = (event) => {
      let finalText = '';
      let interimText = '';
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const phrase = result[0]?.transcript ?? '';
        if (result.isFinal) {
          finalText += phrase;
        } else {
          interimText += phrase;
        }
      }
      if (finalText.trim()) {
        setTranscript((current) => `${current} ${finalText}`.trim());
      }
      setInterimTranscript(interimText.trim());
    };
    recognition.onerror = (event) => {
      const permissionError = event.error === 'not-allowed' || event.error === 'service-not-allowed';
      setSpeechStatus(permissionError ? 'denied' : 'error');
      setSpeechMessage(event.message || `Speech recognition error: ${event.error}`);
      setInterimTranscript('');
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      setInterimTranscript('');
      if (shouldStopRef.current) {
        setSpeechStatus('idle');
        setSpeechMessage('Transcript captured. Review it, then submit or cancel.');
      } else {
        setSpeechStatus((current) => (current === 'denied' || current === 'error' ? current : 'idle'));
      }
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setSpeechStatus('error');
      setSpeechMessage('Unable to start speech recognition. Use text fallback.');
    }
  };

  const stopListening = () => {
    shouldStopRef.current = true;
    setSpeechStatus('processing');
    setSpeechMessage('Finalizing transcript.');
    recognitionRef.current?.stop();
  };

  const cancelTranscript = () => {
    shouldStopRef.current = true;
    recognitionRef.current?.abort();
    setTranscript('');
    setInterimTranscript('');
    setSpeechStatus('idle');
    setSpeechMessage('Transcript cleared. No command was submitted.');
  };

  const submit = async () => {
    const rawTranscript = transcript.trim();
    if (!rawTranscript) return;
    setSubmitting(true);
    setError('');
    try {
      const result = await voiceApi.submit({ raw_transcript: rawTranscript, source: captureMode as VoiceSource });
      setTranscript('');
      setInterimTranscript('');
      const next = [result, ...commands.filter((command) => command.command_id !== result.command_id)];
      setCommands(next);
      announceCommand(result);
      await refresh();
    } catch {
      setError('Unable to submit the voice command. It was not recorded.');
      speak('Unable to submit the voice command. It was not recorded.');
    } finally {
      setSubmitting(false);
    }
  };

  const confirm = async (commandId: string, utterance: string) => {
    setBusyId(commandId);
    try {
      const result = await voiceApi.confirm(commandId, { utterance });
      announceCommand(result);
      await refresh();
    } catch {
      setError(`Unable to resolve confirmation for ${commandId}.`);
      speak('Unable to resolve confirmation.');
    } finally {
      setBusyId(null);
    }
  };

  const cancel = async (commandId: string) => {
    setBusyId(commandId);
    try {
      const result = await voiceApi.cancel(commandId);
      announceCommand(result);
      await refresh();
    } catch {
      setError(`Unable to cancel ${commandId}.`);
      speak('Unable to cancel the command.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-slate-100">
            <Mic className="h-5 w-5 text-gold" /> Voice Concierge
          </h1>
          <p className="mt-1 max-w-4xl text-sm text-slate-400">
            SP-VOICE-001 — governed, mock-first voice operations. Browser speech only creates a transcript preview.
            Classification, policy, confirmation, tenant isolation, RBAC, ledger persistence, and mock providers remain authoritative.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="green" dot>
            <ShieldCheck className="h-3 w-3" /> Mock / sandbox only
          </Badge>
          <Badge variant={ttsEnabled ? 'blue' : 'slate'}>
            {ttsEnabled ? <Volume2 className="h-3 w-3" /> : <VolumeX className="h-3 w-3" />}
            Speech output {ttsEnabled ? 'on' : 'off'}
          </Badge>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
          <AlertTriangle className="h-4 w-4" /> {error}
        </div>
      )}

      <Card>
        <CardHeader
          title="Capture transcript"
          subtitle="Push-to-talk only prepares editable text. Nothing is classified or recorded until Submit is pressed."
          action={
            <Button
              variant="ghost"
              size="sm"
              icon={ttsEnabled ? Volume2 : VolumeX}
              onClick={() => {
                const next = !ttsEnabled;
                setTtsEnabled(next);
                if (!next && ttsSupported) window.speechSynthesis.cancel();
              }}
            >
              {ttsEnabled ? 'Mute' : 'Unmute'}
            </Button>
          }
        />

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_220px]">
          <div className="space-y-3">
            <textarea
              value={transcriptPreview}
              onChange={(event) => {
                setTranscript(event.target.value);
                setInterimTranscript('');
              }}
              placeholder="e.g. schedule a mock follow-up call with the client"
              maxLength={8000}
              rows={4}
              className="min-h-28 w-full resize-y rounded-lg border border-slate-700 bg-slate-900/60 p-3 text-sm text-slate-200 placeholder:text-slate-500 focus:border-gold/50 focus:outline-none"
            />

            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <Badge variant={speechStatus === 'listening' ? 'green' : speechStatus === 'denied' || speechStatus === 'error' ? 'red' : 'slate'} size="sm">
                {speechStatus.replace(/_/g, ' ')}
              </Badge>
              <span>{speechMessage || 'Ready for push-to-talk or text fallback.'}</span>
            </div>
          </div>

          <div className="space-y-3">
            <select
              value={captureMode}
              onChange={(event) => setCaptureMode(event.target.value as CaptureMode)}
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 p-2 text-sm text-slate-200 focus:border-gold/50 focus:outline-none"
            >
              {CAPTURE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <div className="grid grid-cols-2 gap-2">
              <Button
                icon={speechStatus === 'listening' ? Square : Mic}
                variant={speechStatus === 'listening' ? 'danger' : 'outline'}
                onClick={speechStatus === 'listening' ? stopListening : startListening}
                disabled={!speechSupported || captureMode === 'transcript_import' || submitting}
              >
                {speechStatus === 'listening' ? 'Stop' : 'Talk'}
              </Button>
              <Button icon={MicOff} variant="ghost" onClick={cancelTranscript} disabled={!transcriptPreview && speechStatus !== 'listening'}>
                Cancel
              </Button>
            </div>

            <Button icon={Send} onClick={submit} loading={submitting} disabled={!transcript.trim() || speechStatus === 'listening'} fullWidth>
              Submit
            </Button>

            <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-500">
              {CAPTURE_OPTIONS.find((option) => option.value === captureMode)?.description}
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Command ledger"
          subtitle="Tenant-scoped, hash-chained lifecycle of every submitted voice command. Confirmation controls remain explicit."
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
                <div key={cmd.command_id} className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
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
                      <Button size="sm" variant="success" loading={busyId === cmd.command_id} onClick={() => confirm(cmd.command_id, 'yes')}>
                        Confirm
                      </Button>
                      <Button size="sm" variant="danger" loading={busyId === cmd.command_id} onClick={() => confirm(cmd.command_id, 'no')}>
                        Deny
                      </Button>
                      <Button size="sm" variant="ghost" loading={busyId === cmd.command_id} onClick={() => cancel(cmd.command_id)}>
                        Cancel
                      </Button>
                      <Button size="sm" variant="ghost" icon={Volume2} onClick={() => speak(buildConfirmationPrompt(cmd))}>
                        Prompt
                      </Button>
                    </div>
                  )}

                  {!awaiting && !['completed', 'refused', 'cancelled', 'failed'].includes(cmd.session_state) && (
                    <div className="mt-3">
                      <Button size="sm" variant="ghost" loading={busyId === cmd.command_id} onClick={() => cancel(cmd.command_id)}>
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
