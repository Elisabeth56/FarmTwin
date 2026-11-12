// FarmTwin 3D farm: a procedural low-poly Nigerian smallholder farm.
// mountTwin() builds the scene into a canvas and returns a small API for the page.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

// Six plot slots in a 3 x 2 grid; the landing page fills them with all six crops, the app with a
// farm's own plantings. `badgePlot` is the slot the risk badge points at.
const SLOTS = [[-5, -1.85], [-1.5, -1.85], [2, -1.85], [-5, 1.85], [-1.5, 1.85], [2, 1.85]];
export const LANDING_PLOTS = ['maize', 'sorghum', 'rice', 'cassava', 'yam', 'cowpea'].map(crop => ({ crop }));

export function mountTwin({ frame, canvas, badge, chip, chipDot, chipText, autoRotate = true, onReady,
  plots: plotSpec = LANDING_PLOTS, badgePlot = 0, onDemand = false, onSelect = null }) {
// ---------- scene ----------
let renderer, scene, camera, controls, started = false;
const plots = [];
let rain = false, rainAmount = 0;
const tileMats = [];
const dryTile = new THREE.Color('#8B6B4A'), wetTile = new THREE.Color('#5C4632');
const dryGrass = new THREE.Color('#9DBA7E'), wetGrass = new THREE.Color('#7C9B60');

function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const rand = rng(7);
const mat = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.9, metalness: 0, flatShading: true, ...o });
const tmp = new THREE.Object3D();
function m4(x, y, z, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1) {
  tmp.position.set(x, y, z); tmp.rotation.set(rx, ry, rz); tmp.scale.set(sx, sy, sz); tmp.updateMatrix(); return tmp.matrix.clone();
}
function instanced(geo, material, list) {
  const im = new THREE.InstancedMesh(geo, material, list.length);
  list.forEach((mx, i) => im.setMatrixAt(i, mx));
  im.castShadow = true; im.receiveShadow = true; return im;
}
function mesh(geo, material, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geo, material); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; return m;
}

// shared geometry, origin at the base so instances scale upward
const stalkGeo = new THREE.CylinderGeometry(0.025, 0.04, 1, 5).translate(0, 0.5, 0);
const leafGeo = new THREE.BoxGeometry(0.5, 0.015, 0.09).translate(0.25, 0, 0);
const tufGeo = new THREE.ConeGeometry(0.045, 0.38, 4).translate(0, 0.19, 0);
const leafGreen = mat('#4E8A3E'), deepGreen = mat('#3E7A3A');

function plotBase(x, z, isWater) {
  const g = new THREE.Group(); g.position.set(x, 0, z);
  const tm = isWater ? mat('#7FB3BC', { roughness: 0.15, metalness: 0.1, flatShading: false }) : mat('#8B6B4A');
  if (!isWater) tileMats.push(tm);
  g.add(mesh(new RoundedBoxGeometry(3.0, 0.14, 3.2, 2, 0.06), tm, 0, 0.12, 0));
  if (isWater) {
    const bund = mat('#7A5D40');
    [[0, -1.55, 3.0, 0.1], [0, 1.55, 3.0, 0.1], [-1.45, 0, 0.1, 3.2], [1.45, 0, 0.1, 3.2]].forEach(([bx, bz, w, d]) => g.add(mesh(new THREE.BoxGeometry(w, 0.12, d), bund, bx, 0.22, bz)));
  }
  return g;
}

function cropFlag(g, color) {
  g.add(mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.75, 5).translate(0, 0.375, 0), mat('#EDE6D6'), 1.32, 0.19, 1.45));
  g.add(mesh(new RoundedBoxGeometry(0.32, 0.18, 0.03, 2, 0.02), mat(color), 1.49, 0.84, 1.45));
}

function cereal(g, opts) {
  const stalks = [], leaves = [], heads = [];
  for (let i = 0; i < 6; i++) for (let j = 0; j < 7; j++) {
    const x = -1.1 + i * 0.44 + (rand() - 0.5) * 0.08, z = -1.3 + j * 0.43 + (rand() - 0.5) * 0.08;
    const h = opts.h + rand() * 0.25;
    stalks.push(m4(x, 0.19, z, 0, 0, (rand() - 0.5) * 0.08, 1, h, 1));
    for (let k = 0; k < 3; k++) leaves.push(m4(x, 0.19 + h * (0.3 + k * 0.2), z, 0, rand() * Math.PI * 2, 0.45 + rand() * 0.3, 0.8 + rand() * 0.3, 1, 1));
    heads.push(m4(x, 0.19 + h + opts.headY, z, (rand() - 0.5) * opts.droop, 0, (rand() - 0.5) * opts.droop, 1, opts.headS, 1));
  }
  g.add(instanced(stalkGeo, opts.stalkMat, stalks));
  g.add(instanced(leafGeo, leafGreen, leaves));
  g.add(instanced(opts.headGeo, mat(opts.headColor), heads));
}

function buildFarm() {
  const farm = new THREE.Group();

  // layered slab: grass, topsoil, subsoil
  const grassMat = mat('#9DBA7E');
  farm.add(mesh(new RoundedBoxGeometry(14.6, 0.24, 10.6, 3, 0.12), grassMat, 0, -0.07, 0));
  farm.add(mesh(new RoundedBoxGeometry(14.4, 0.7, 10.4, 3, 0.25), mat('#8E6E4E'), 0, -0.5, 0));
  farm.add(mesh(new RoundedBoxGeometry(14.2, 0.6, 10.2, 3, 0.25), mat('#6E5440'), 0, -1.05, 0));
  farm.userData.grass = grassMat;

  // paths
  const pathMat = mat('#D9C49B');
  farm.add(mesh(new THREE.BoxGeometry(11.2, 0.03, 0.55), pathMat, -1.4, 0.06, 0));
  farm.add(mesh(new THREE.BoxGeometry(0.55, 0.03, 4.6), pathMat, 4.0, 0.06, -0.6));

  const builders = {
    maize: { name: 'Maize', color: '#E3B341', build: g => cereal(g, { h: 0.95, headY: 0.06, headS: 1, droop: 0.2, headGeo: new THREE.ConeGeometry(0.06, 0.22, 5), headColor: '#E3B341', stalkMat: mat('#5E9A47') }) },
    sorghum: { name: 'Sorghum', color: '#B06A3B', build: g => cereal(g, { h: 1.2, headY: 0.12, headS: 2.2, droop: 0.5, headGeo: new THREE.SphereGeometry(0.08, 6, 5), headColor: '#B06A3B', stalkMat: mat('#6E9A4E') }) },
    rice: { name: 'Rice', color: '#5FA89A', water: true, build: g => {
      const t = [];
      for (let i = 0; i < 7; i++) for (let j = 0; j < 8; j++) for (let k = 0; k < 3; k++)
        t.push(m4(-1.15 + i * 0.38, 0.2, -1.3 + j * 0.37, (rand() - 0.5) * 0.5, rand() * 6, (rand() - 0.5) * 0.5, 1, 0.8 + rand() * 0.4, 1));
      g.add(instanced(tufGeo, mat('#7DB356'), t));
    } },
    cassava: { name: 'Cassava', color: '#CDA07A', build: g => {
      const mounds = [], stems = [], leaves = [];
      for (let i = 0; i < 3; i++) for (let j = 0; j < 4; j++) {
        const x = -0.9 + i * 0.9, z = -1.15 + j * 0.77;
        mounds.push(m4(x, 0.19, z, 0, 0, 0, 1, 0.55, 1));
        stems.push(m4(x, 0.3, z, (rand() - 0.5) * 0.15, 0, (rand() - 0.5) * 0.15, 1, 0.8, 1));
        for (let k = 0; k < 6; k++) leaves.push(m4(x, 1.1, z, 0, k * 1.05 + rand(), 0.35, 0.75, 1, 1));
      }
      g.add(instanced(new THREE.SphereGeometry(0.3, 8, 6), mat('#7E5F42'), mounds));
      g.add(instanced(stalkGeo, mat('#8C5A3C'), stems));
      g.add(instanced(new THREE.ConeGeometry(0.07, 0.42, 4).rotateZ(-Math.PI / 2).translate(0.21, 0, 0), deepGreen, leaves));
    } },
    yam: { name: 'Yam', color: '#8C6BB1', build: g => {
      const heaps = [], stakes = [], vine = [];
      for (let i = 0; i < 2; i++) for (let j = 0; j < 3; j++) {
        const x = -0.6 + i * 1.2, z = -1.0 + j * 1.0, lean = (rand() - 0.5) * 0.2;
        heaps.push(m4(x, 0.19, z));
        stakes.push(m4(x, 0.3, z, lean, 0, lean, 1, 1.6, 1));
        for (let k = 0; k < 7; k++) vine.push(m4(x + (rand() - 0.5) * 0.25, 0.65 + k * 0.17, z + (rand() - 0.5) * 0.25, 0, rand() * 6, 0, 1, 0.7, 1));
      }
      g.add(instanced(new THREE.ConeGeometry(0.44, 0.52, 8).translate(0, 0.26, 0), mat('#7A5A3E'), heaps));
      g.add(instanced(new THREE.CylinderGeometry(0.02, 0.025, 1, 4).translate(0, 0.5, 0), mat('#9A7B55'), stakes));
      g.add(instanced(new THREE.SphereGeometry(0.1, 5, 4), leafGreen, vine));
      g.add(instanced(new THREE.SphereGeometry(0.09, 6, 5), mat('#8C6BB1'), [m4(-0.25, 0.26, 1.2, 0, 0, 1.2, 1, 1.8, 1)]));
    } },
    cowpea: { name: 'Cowpea', color: '#4A77B4', build: g => {
      const bush = [], flowers = [];
      for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) {
        const x = -1.1 + i * 0.44, z = -1.15 + j * 0.46, s = 0.8 + rand() * 0.4;
        bush.push(m4(x, 0.3, z, rand(), rand(), rand(), s, s * 0.8, s));
        if (rand() > 0.4) flowers.push(m4(x + (rand() - 0.5) * 0.2, 0.47, z + (rand() - 0.5) * 0.2));
      }
      g.add(instanced(new THREE.IcosahedronGeometry(0.2, 0), mat('#5E8C46'), bush));
      g.add(instanced(new THREE.SphereGeometry(0.035, 4, 3), mat('#C9B6EE'), flowers));
    } },
  };
  // a farm can have more plantings than slots; the first six are drawn
  const defs = plotSpec.slice(0, SLOTS.length).map((p, i) => ({ ...builders[p.crop] || builders.maize, name: p.label || builders[p.crop]?.name || p.crop, x: SLOTS[i][0], z: SLOTS[i][1] }));

  const hitMat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
  defs.forEach((d, i) => {
    const g = plotBase(d.x, d.z, d.water);
    d.build(g); cropFlag(g, d.color);
    const hit = new THREE.Mesh(new THREE.BoxGeometry(3.0, 1.6, 3.2), hitMat); hit.position.y = 0.8; g.add(hit);
    g.userData = { name: d.name, color: d.color, delay: i * 90, lift: 0, hit };
    g.position.y = -0.6; g.scale.setScalar(0.001);
    plots.push(g); farm.add(g);
  });

  // homestead: mud house with zinc roof, granary, drum, mango tree, fence
  const home = new THREE.Group(); home.userData.delay = 600;
  const mud = mat('#C68B59'), mudDark = mat('#A9724A');
  home.add(mesh(new THREE.BoxGeometry(2.0, 1.0, 1.4), mud, 5.3, 0.5, -2.4));
  const gable = new THREE.Shape(); gable.moveTo(-0.7, 0); gable.lineTo(0.7, 0); gable.lineTo(0, 0.45); gable.closePath();
  const gableGeo = new THREE.ExtrudeGeometry(gable, { depth: 2.0, bevelEnabled: false }).rotateY(Math.PI / 2).translate(-1.0, 0, 0);
  home.add(mesh(gableGeo, mudDark, 5.3, 1.0, -2.4));
  const stripes = document.createElement('canvas'); stripes.width = 64; stripes.height = 8;
  const sc = stripes.getContext('2d'); for (let x = 0; x < 64; x += 8) { sc.fillStyle = '#B9C0C2'; sc.fillRect(x, 0, 4, 8); sc.fillStyle = '#8F979A'; sc.fillRect(x + 4, 0, 4, 8); }
  const zincTex = new THREE.CanvasTexture(stripes); zincTex.wrapS = THREE.RepeatWrapping; zincTex.repeat.set(5, 1); zincTex.colorSpace = THREE.SRGBColorSpace;
  const zinc = new THREE.MeshStandardMaterial({ map: zincTex, metalness: 0.55, roughness: 0.45 });
  [-1, 1].forEach(s => { const r = mesh(new THREE.BoxGeometry(2.3, 0.04, 0.95), zinc, 5.3, 1.24, -2.4 + s * 0.4); r.rotation.x = s * 0.57; home.add(r); });
  home.add(mesh(new THREE.BoxGeometry(0.34, 0.62, 0.03), mat('#5A3B28'), 5.0, 0.31, -1.69));
  home.add(mesh(new THREE.BoxGeometry(0.03, 0.3, 0.42), mat('#3B3A36'), 6.31, 0.6, -2.4));
  // granary (rumbu) on stones with thatch
  const stone = mat('#9C9A93');
  [[0.3, 0], [-0.15, 0.26], [-0.15, -0.26]].forEach(([dx, dz]) => home.add(mesh(new THREE.DodecahedronGeometry(0.16, 0), stone, 5.6 + dx, 0.12, 1.0 + dz)));
  home.add(mesh(new THREE.CylinderGeometry(0.5, 0.56, 0.85, 12), mat('#B5784A'), 5.6, 0.68, 1.0));
  home.add(mesh(new THREE.ConeGeometry(0.78, 0.72, 12), mat('#D2B46A'), 5.6, 1.45, 1.0));
  // blue water drum
  home.add(mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.46, 14), mat('#2F6FB3', { flatShading: false, roughness: 0.5 }), 6.4, 0.28, -0.7));
  // mango tree
  home.add(mesh(new THREE.CylinderGeometry(0.1, 0.16, 1.2, 6).translate(0, 0.6, 0), mat('#6B4A33'), 5.1, 0.05, 3.6));
  [[0, 1.55, 0, 0.7, '#4A7A44'], [0.4, 1.4, 0.2, 0.5, '#3F6B3A'], [-0.35, 1.45, -0.15, 0.55, '#557F48'], [0.05, 1.9, -0.1, 0.45, '#4A7A44']].forEach(([dx, y, dz, r, c]) => home.add(mesh(new THREE.IcosahedronGeometry(r, 0), mat(c), 5.1 + dx, y, 3.6 + dz)));
  // stick fence along the back edges
  const posts = [], fenceMat = mat('#8A6A4A');
  for (let x = -6.8; x <= 6.8; x += 0.6) posts.push(m4(x, 0.05, -4.95, 0, 0, (rand() - 0.5) * 0.1, 1, 0.55, 1));
  for (let z = -4.4; z <= 4.8; z += 0.6) posts.push(m4(-6.95, 0.05, z, (rand() - 0.5) * 0.1, 0, 0, 1, 0.55, 1));
  home.add(instanced(new THREE.CylinderGeometry(0.03, 0.035, 1, 4).translate(0, 0.5, 0), fenceMat, posts));
  home.add(mesh(new THREE.BoxGeometry(13.8, 0.04, 0.04), fenceMat, 0, 0.42, -4.95));
  home.add(mesh(new THREE.BoxGeometry(0.04, 0.04, 9.4), fenceMat, -6.95, 0.42, 0.2));
  home.scale.setScalar(0.001); farm.add(home); farm.userData.home = home;

  // rain cloud and drops (hidden until rain is logged)
  const cloud = new THREE.Group();
  const cloudMat = new THREE.MeshStandardMaterial({ color: '#F4F6F2', roughness: 1, transparent: true, opacity: 0, flatShading: true });
  [[0, 0, 0, 0.8], [0.9, -0.1, 0.15, 0.6], [-0.9, -0.05, -0.1, 0.65], [0.3, 0.3, -0.15, 0.55], [-0.4, 0.25, 0.25, 0.5], [1.6, -0.15, -0.1, 0.45], [-1.6, -0.12, 0.1, 0.45]].forEach(([x, y, z, r]) => cloud.add(new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), cloudMat)));
  cloud.scale.set(1.3, 0.7, 1.1); cloud.position.set(-3.3, 4.0, -1.85); farm.add(cloud);
  const N = 420, pos = new Float32Array(N * 6);
  for (let i = 0; i < N; i++) { const x = -6.2 + rand() * 5.8, z = -3.3 + rand() * 3, y = 0.3 + rand() * 3.4; pos.set([x, y, z, x - 0.04, y - 0.28, z], i * 6); }
  const dropGeo = new THREE.BufferGeometry(); dropGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const drops = new THREE.LineSegments(dropGeo, new THREE.LineBasicMaterial({ color: '#8FA9BC', transparent: true, opacity: 0 }));
  farm.add(drops);
  // puddles on the path
  const puddleMat = new THREE.MeshStandardMaterial({ color: '#8FB3C2', roughness: 0.1, metalness: 0.2, transparent: true, opacity: 0 });
  [[-3.2, 0.25], [0.6, -0.1], [4.0, -1.6]].forEach(([x, z]) => { const p = new THREE.Mesh(new THREE.CircleGeometry(0.32, 16), puddleMat); p.rotation.x = -Math.PI / 2; p.position.set(x, 0.085, z); p.scale.set(1, 0.6, 1); farm.add(p); });

  farm.userData.weather = { cloudMat, drops, pos, puddleMat };
  return farm;
}

let sizer, farm, raycaster, pointer = new THREE.Vector2(), hovered = null, selected = null, viewGoal = null, home0 = null, t0 = 0, idleTimer = 0;
const badgeAnchor = new THREE.Vector3(SLOTS[badgePlot][0], 1.9, SLOTS[badgePlot][1]);

function start() {
  if (started) return; started = true;
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(28, 1, 0.1, 200);
  camera.position.set(18.5, 13.4, 18.5);
  scene.add(new THREE.HemisphereLight('#F4F7EE', '#6E5A45', 1.15));
  const sun = new THREE.DirectionalLight('#FFF3DC', 2.2);
  sun.position.set(8, 14, 6); sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024); sun.shadow.camera.left = -10; sun.shadow.camera.right = 10; sun.shadow.camera.top = 10; sun.shadow.camera.bottom = -10;
  sun.shadow.bias = -0.0005; sun.shadow.radius = 4;
  scene.add(sun);

  farm = buildFarm(); farm.position.y = -0.4; scene.add(farm);
  // soft contact shadow under the slab
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(7.6, 48), new THREE.MeshBasicMaterial({ color: '#1F3328', transparent: true, opacity: 0.06 }));
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = -1.8; shadow.scale.set(1, 0.75, 1); scene.add(shadow);

  controls = new OrbitControls(camera, canvas);
  controls.enablePan = false; controls.enableZoom = false; controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.minPolarAngle = 0.75; controls.maxPolarAngle = 1.12;
  controls.autoRotate = autoRotate; controls.autoRotateSpeed = 0.5;
  controls.target.set(0, -0.6, 0);
  controls.addEventListener('start', () => { controls.autoRotate = false; clearTimeout(idleTimer); dragging = true; wake(); });
  controls.addEventListener('change', () => wake());
  controls.addEventListener('end', () => { dragging = false; idleTimer = setTimeout(() => { controls.autoRotate = autoRotate; wake(); }, 4000); });

  raycaster = new THREE.Raycaster();
  canvas.addEventListener('pointermove', e => { const r = canvas.getBoundingClientRect(); pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1; pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1; pointer.px = e.clientX - r.left; pointer.py = e.clientY - r.top; pointer.active = true; wake(); });
  canvas.addEventListener('pointerleave', () => { pointer.active = false; wake(); });

  // a click (not a drag) on a plot selects it; anywhere else clears the selection
  let downAt = null;
  canvas.addEventListener('pointerdown', e => { downAt = [e.clientX, e.clientY]; });
  canvas.addEventListener('pointerup', e => {
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 6) return;
    const r = canvas.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const hit = raycaster.intersectObjects(plots.map(p => p.userData.hit), false)[0]?.object.parent ?? null;
    choose(hit === selected ? null : hit);
  });
  canvas.addEventListener('keydown', e => {
    const keys = { ArrowLeft: () => turn(-0.4), ArrowRight: () => turn(0.4), '+': () => zoom(0.85), '=': () => zoom(0.85), '-': () => zoom(1.18), '0': () => resetView(), Escape: () => choose(null) };
    if (keys[e.key]) { e.preventDefault(); keys[e.key](); }
  });

  home0 = { az: controls.getAzimuthalAngle(), polar: controls.getPolarAngle(), r: camera.position.distanceTo(controls.target) };
  resize(); sizer = new ResizeObserver(resize); sizer.observe(frame);
  t0 = performance.now(); loop();
  if (onReady) onReady();
}

function resize() {
  const w = frame.clientWidth, h = frame.clientHeight;
  renderer.setSize(w, h, false); camera.aspect = w / h;
  // frame the whole slab on narrow screens
  camera.fov = w < 600 ? 40 : 28; camera.updateProjectionMatrix();
}

const ease = t => 1 - Math.pow(1 - Math.min(Math.max(t, 0), 1), 3.2);
let running = false, visible = true, last = performance.now(), dragging = false, settled = 0;
function loop() {
  if (!visible || !active) { running = false; return; }
  running = true;
  const now = performance.now(), dt = Math.min((now - last) / 1000, 0.05); last = now;
  const el = now - t0;

  // entrance: plots rise one by one, then the homestead
  plots.forEach(g => { const k = ease((el - g.userData.delay) / 900); g.position.y = -0.6 * (1 - k) + g.userData.lift; g.scale.setScalar(Math.max(k, 0.001)); });
  const hk = ease((el - farm.userData.home.userData.delay) / 900); farm.userData.home.scale.setScalar(Math.max(hk, 0.001));
  farm.position.y = -0.4 + 0.4 * ease(el / 1200);

  // hover: lift the plot under the pointer and label it
  let hit = null;
  if (pointer.active) { raycaster.setFromCamera(pointer, camera); const hits = raycaster.intersectObjects(plots.map(p => p.userData.hit), false); if (hits.length) hit = hits[0].object.parent; }
  if (hit !== hovered) { hovered = hit; chip.style.display = hit ? 'flex' : 'none'; if (hit) { chipDot.style.background = hit.userData.color; chipText.textContent = hit.userData.name; } }
  plots.forEach(g => { g.userData.lift += (liftFor(g) - g.userData.lift) * Math.min(dt * 10, 1); });
  if (hovered) chip.style.transform = `translate(${pointer.px + 14}px, ${pointer.py - 36}px)`;

  // weather
  rainAmount += ((rain ? 1 : 0) - rainAmount) * Math.min(dt * 2.2, 1);
  const w = farm.userData.weather;
  w.cloudMat.opacity = rainAmount * 0.95; w.drops.material.opacity = rainAmount * 0.75; w.puddleMat.opacity = rainAmount * 0.8;
  if (rainAmount > 0.01) {
    for (let i = 0; i < w.pos.length; i += 6) {
      w.pos[i + 1] -= dt * 7; w.pos[i + 4] -= dt * 7;
      if (w.pos[i + 4] < 0.2) { w.pos[i + 1] += 3.4; w.pos[i + 4] += 3.4; }
    }
    w.drops.geometry.attributes.position.needsUpdate = true;
  }
  tileMats.forEach(m => m.color.copy(dryTile).lerp(wetTile, rainAmount));
  farm.userData.grass.color.copy(dryGrass).lerp(wetGrass, rainAmount * 0.7);

  if (viewGoal) easeView(dt);
  controls.update();
  renderer.render(scene, camera);

  // risk badge follows the maize plot on screen
  const p = badgeAnchor.clone().add(new THREE.Vector3(0, farm.position.y, 0)).project(camera);
  const bx = (p.x * 0.5 + 0.5) * frame.clientWidth, by = (-p.y * 0.5 + 0.5) * frame.clientHeight;
  badge.style.transform = `translate(${bx}px, ${by}px) translate(-50%, -100%)`;

  // on demand: after a second of nothing moving, stop drawing until input or a state change
  if (onDemand) {
    const moving = el < 1600 || dragging || controls.autoRotate || pointer.active || Math.abs((rain ? 1 : 0) - rainAmount) > 0.002
      || viewGoal !== null || plots.some(g => Math.abs(liftFor(g) - g.userData.lift) > 0.002);
    settled = moving ? now : settled;
    if (now - settled > 1000) { running = false; return; }
  }
  requestAnimationFrame(loop);
}


  let active = true;
  const wake = () => { if (visible && active && started && !running) { last = performance.now(); loop(); } };
  // pause when the frame is offscreen or the tab is hidden
  const seen = new IntersectionObserver(([e]) => { visible = e.isIntersecting && !document.hidden; wake(); });
  seen.observe(frame);
  const onVisibility = () => { visible = !document.hidden; wake(); };
  document.addEventListener('visibilitychange', onVisibility);

  function liftFor(g) { return g === selected ? 0.45 : g === hovered ? 0.18 : 0; }
  function choose(g) {
    selected = g; wake();
    if (onSelect) onSelect(g ? plots.indexOf(g) : null);
  }
  function view() { return { az: controls.getAzimuthalAngle(), polar: controls.getPolarAngle(), r: camera.position.distanceTo(controls.target) }; }
  function place({ az, polar, r }) {
    const t = controls.target;
    camera.position.set(t.x + Math.sin(polar) * Math.sin(az) * r, t.y + Math.cos(polar) * r, t.z + Math.sin(polar) * Math.cos(az) * r);
  }
  // turn, zoom and reset glide to a goal view instead of jumping
  function easeView(dt) {
    const v = view(), k = Math.min(dt * 7, 1);
    let dAz = viewGoal.az - v.az; dAz = Math.atan2(Math.sin(dAz), Math.cos(dAz));
    const next = { az: v.az + dAz * k, polar: v.polar + (viewGoal.polar - v.polar) * k, r: v.r + (viewGoal.r - v.r) * k };
    place(next);
    if (Math.abs(dAz) < 0.002 && Math.abs(viewGoal.r - v.r) < 0.01 && Math.abs(viewGoal.polar - v.polar) < 0.002) viewGoal = null;
  }
  function turn(delta) { const v = viewGoal || view(); viewGoal = { ...v, az: v.az + delta }; controls.autoRotate = false; wake(); }
  function zoom(factor) { const v = viewGoal || view(); viewGoal = { ...v, r: Math.min(home0.r * 1.25, Math.max(home0.r * 0.6, v.r * factor)) }; wake(); }
  function resetView() { viewGoal = { ...home0 }; wake(); }

  start();
  return {
    select(index) { selected = index === null ? null : plots[index] ?? null; wake(); },
    turn, zoom, resetView,
    setRain(on) { rain = on; badge.classList.toggle('on', on); wake(); },
    pause() { active = false; chip.style.display = 'none'; hovered = null; },
    resume() { active = true; wake(); },
    // the app mounts one twin per farm screen and tears it down on navigation
    dispose() {
      active = false; clearTimeout(idleTimer);
      seen.disconnect(); sizer?.disconnect(); document.removeEventListener('visibilitychange', onVisibility);
      controls?.dispose();
      scene?.traverse(o => { o.geometry?.dispose(); [].concat(o.material || []).forEach(m => m.dispose()); });
      renderer?.dispose();
    },
    // capture hooks for rendering the lite loop and stills
    setView(azimuth, polar = 1.0) {
      controls.autoRotate = false; controls.enableDamping = false;
      const r = camera.position.distanceTo(controls.target);
      camera.position.set(Math.sin(polar) * Math.sin(azimuth) * r, Math.cos(polar) * r - 0.6, Math.sin(polar) * Math.cos(azimuth) * r);
      controls.update();
    },
    get azimuth() { return controls.getAzimuthalAngle(); },
    get polar() { return controls.getPolarAngle(); },
  };
}
