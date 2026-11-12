// The hero farm: picks 3D, video or still for this device, and the rain toggle.
// 3D farm: pick a version before loading anything heavy
const $ = id => document.getElementById(id);
const frame = $('frame'), note = $('tierNote'), vid = $('liteVid'), badge = $('badge');
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
let twin = null, rain = false, tier = 'still';

function detect() {
  if (reduce) return 'still';
  if (!document.createElement('canvas').getContext('webgl2')) return 'still';
  const c = navigator.connection;
  if (c && c.saveData) return 'lite';
  if (navigator.deviceMemory && navigator.deviceMemory < 4) return 'lite';
  if ((navigator.hardwareConcurrency || 4) < 4) return 'lite';
  return 'full';
}
const read = () => { try { return localStorage.getItem('ft-tier') || 'auto'; } catch (e) { return 'auto'; } };
const save = v => { try { localStorage.setItem('ft-tier', v); } catch (e) {} };

function setVideo() {
  const n = rain ? 'farm-rain' : 'farm-dry';
  vid.innerHTML = `<source src="/assets/${n}.webm" type="video/webm"><source src="/assets/${n}.mp4" type="video/mp4">`;
  vid.poster = `/assets/${n}.webp`; vid.load(); vid.play().catch(() => {});
}
function setStill() {
  const n = rain ? 'farm-rain' : 'farm-dry';
  $('stillWebp').srcset = `/assets/${n}.webp`; $('stillImg').src = `/assets/${n}.jpg`;
}

async function apply(choice) {
  tier = choice === 'auto' ? detect() : choice;
  frame.dataset.tier = tier;
  document.querySelectorAll('.tbtn').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.t === choice)));
  $('liteBtn').setAttribute('aria-pressed', String(choice === 'still'));
  setStill();
  if (tier === 'full') {
    note.textContent = '3D · drag to turn';
    if (!twin) {
      const { mountTwin } = await import('@farmtwin/twin');
      twin = mountTwin({ frame, canvas: $('c'), badge, chip: $('chip'), chipDot: $('chipDot'), chipText: $('chipText'), autoRotate: !reduce, onReady: () => frame.classList.add('live') });
    } else { twin.resume(); frame.classList.add('live'); }
    twin.setRain(rain);
  } else {
    if (twin) twin.pause();
    frame.classList.remove('live'); badge.classList.remove('on');
    if (tier === 'lite') { note.textContent = 'Video · lighter version'; setVideo(); } else { note.textContent = 'Still · lightest version'; vid.pause(); }
  }
}

$('rain').addEventListener('click', () => {
  rain = !rain;
  $('rain').setAttribute('aria-pressed', String(rain));
  $('rainLabel').textContent = rain ? '65 mm of rain logged' : 'Log 65 mm of rain';
  if (tier === 'full' && twin) twin.setRain(rain); else if (tier === 'lite') setVideo(); else setStill();
});
document.querySelectorAll('.tbtn').forEach(b => b.addEventListener('click', () => { save(b.dataset.t); apply(b.dataset.t); }));
$('liteBtn').addEventListener('click', () => { const v = read() === 'still' ? 'auto' : 'still'; save(v); apply(v); });
apply(read());
