// Turns a browser recording into the 16 kHz mono 16-bit WAV whisper.cpp reads, so the app
// ships no audio converter (ADR-017).

const RATE = 16_000;

/** Decodes whatever MediaRecorder produced (webm/opus, mp4/aac) and resamples it to WAV. */
export async function toWav(recording: Blob): Promise<Blob> {
  const ctx = new AudioContext();
  const decoded = await ctx.decodeAudioData(await recording.arrayBuffer()).finally(() => void ctx.close());
  // an offline context at 16 kHz with one channel does the resampling and the downmix
  const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * RATE), RATE);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const samples = (await offline.startRendering()).getChannelData(0);
  return new Blob([encode(samples)], { type: "audio/wav" });
}

function encode(samples: Float32Array): ArrayBuffer {
  const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
  const ascii = (at: number, s: string) => [...s].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)));
  // RIFF header for PCM, 1 channel, 16-bit
  ascii(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  ascii(8, "WAVE");
  ascii(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, RATE, true);
  view.setUint32(28, RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  ascii(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((x, i) => view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x)) * 0x7fff, true));
  return view.buffer;
}
