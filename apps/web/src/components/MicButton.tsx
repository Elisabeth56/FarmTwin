import { useEffect, useRef, useState } from "react";
import { transcribeAudio } from "../lib/api";

export type MicButtonProps = {
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
  onBusyChange?: (busy: boolean) => void;
  disabled?: boolean;
};

type MicState =
  | "idle"
  | "requesting-permission"
  | "recording"
  | "transcribing"
  | "error";

const MAX_RECORD_SECONDS = 15;

function isMediaSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function" &&
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined"
  );
}

function MicIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="3" width="6" height="12" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <rect x="6" y="6" width="12" height="12" rx="1.5" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className="animate-spin"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function formatTimer(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function MicButton({
  onTranscript,
  onError,
  onBusyChange,
  disabled,
}: MicButtonProps) {
  const [state, setState] = useState<MicState>("idle");
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const busy =
      state === "requesting-permission" ||
      state === "recording" ||
      state === "transcribing";
    onBusyChange?.(busy);
  }, [state, onBusyChange]);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const autoStopRef = useRef<number | null>(null);
  const autoStoppedRef = useRef(false);

  const supported = isMediaSupported();

  useEffect(() => {
    return () => {
      cleanupRecording();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function cleanupRecording() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (autoStopRef.current !== null) {
      window.clearTimeout(autoStopRef.current);
      autoStopRef.current = null;
    }
    const stream = streamRef.current;
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    mediaRecorderRef.current = null;
  }

  async function handleTranscribe(blob: Blob) {
    setState("transcribing");
    try {
      const result = await transcribeAudio(blob);
      onTranscript(result.text);
      setState("idle");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Transcription failed";
      onError(message);
      setState("idle");
    }
  }

  async function startRecording() {
    if (!supported) {
      onError("Voice input not supported in this browser.");
      return;
    }
    setState("requesting-permission");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      const name = err instanceof Error ? err.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        onError(
          "Microphone access denied. Enable microphone permissions for this site in your browser settings.",
        );
      } else {
        const message = err instanceof Error ? err.message : "Microphone unavailable";
        onError(`Could not access microphone: ${message}`);
      }
      setState("idle");
      return;
    }

    streamRef.current = stream;
    chunksRef.current = [];
    autoStoppedRef.current = false;

    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(stream);
    } catch (err) {
      const message = err instanceof Error ? err.message : "MediaRecorder failed";
      onError(`Recording failed to start: ${message}`);
      cleanupRecording();
      setState("idle");
      return;
    }
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };
    recorder.onstop = () => {
      const chunks = chunksRef.current;
      const mimeType = recorder.mimeType || "audio/webm";
      const blob = new Blob(chunks, { type: mimeType });
      cleanupRecording();
      if (autoStoppedRef.current) {
        onError(`Recording stopped at ${MAX_RECORD_SECONDS}s.`);
      }
      if (blob.size === 0) {
        onError("No audio captured. Try again.");
        setState("idle");
        return;
      }
      void handleTranscribe(blob);
    };

    recorder.start();
    setState("recording");
    setElapsed(0);
    timerRef.current = window.setInterval(() => {
      setElapsed((e) => e + 1);
    }, 1000);
    autoStopRef.current = window.setTimeout(() => {
      autoStoppedRef.current = true;
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    }, MAX_RECORD_SECONDS * 1000);
  }

  function stopRecording() {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  }

  function handleClick() {
    if (disabled) return;
    if (state === "idle" || state === "error") {
      void startRecording();
    } else if (state === "recording") {
      stopRecording();
    }
  }

  const isBusy = state === "requesting-permission" || state === "transcribing";
  const isRecording = state === "recording";
  const buttonDisabled = disabled || !supported || isBusy;

  const baseClasses =
    "flex items-center justify-center w-10 h-10 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2";
  const stateClasses = !supported
    ? "bg-bg text-ink-faint cursor-not-allowed"
    : buttonDisabled && !isBusy
      ? "bg-bg text-ink-faint cursor-not-allowed"
      : isRecording
        ? "bg-risk-high text-white animate-pulse"
        : isBusy
          ? "bg-primary-tint text-primary cursor-wait"
          : "bg-primary text-white hover:bg-primary/90";

  let title = "Voice input (Nigerian English)";
  if (!supported) title = "Voice input not supported in this browser";
  else if (disabled) title = "Voice input unavailable right now";
  else if (isRecording) title = "Stop recording";
  else if (state === "transcribing") title = "Transcribing…";
  else if (state === "requesting-permission") title = "Requesting microphone…";

  const ariaLabel = isRecording ? "Stop recording" : "Voice input (Nigerian English)";

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={buttonDisabled}
        title={title}
        aria-label={ariaLabel}
        className={`${baseClasses} ${stateClasses}`}
      >
        {isRecording ? (
          <StopIcon />
        ) : isBusy ? (
          <SpinnerIcon />
        ) : (
          <MicIcon />
        )}
      </button>
      {isRecording && (
        <div className="text-[11px] text-ink-muted flex items-center gap-1">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-risk-high animate-pulse" />
          <span>Listening… {formatTimer(elapsed)}</span>
        </div>
      )}
      {state === "transcribing" && (
        <div className="text-[11px] text-ink-muted">Transcribing…</div>
      )}
    </div>
  );
}
