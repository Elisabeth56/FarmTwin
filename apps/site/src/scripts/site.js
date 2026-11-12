// Floating nav, scroll reveals, pinned steps, accordions and the footer wordmark.
// floating nav: tighten, hide on scroll down, sliding active pill
(function () {
  var nav = document.getElementById('nav'), last = 0;
  addEventListener('scroll', function () {
    var y = scrollY; nav.classList.toggle('tight', y > 80);
    nav.classList.toggle('hide', y > last && y > 200); last = y;
  }, { passive: true });
  var links = document.getElementById('links'), pill = document.getElementById('navPill');
  function place(a) { if (!a) { pill.style.opacity = 0; return; } pill.style.opacity = 1; pill.style.left = a.offsetLeft + 'px'; pill.style.width = a.offsetWidth + 'px'; }
  var anchors = [].slice.call(links.querySelectorAll('a'));
  anchors.forEach(function (a) { a.addEventListener('mouseenter', function () { place(a); }); });
  links.addEventListener('mouseleave', function () { place(current()); });
  function current() {
    var found = null;
    ['how', 'crops', 'offline'].forEach(function (id, i) { var el = document.getElementById(id), r = el && el.getBoundingClientRect(); if (r && r.top < innerHeight * 0.4 && r.bottom > innerHeight * 0.4) found = anchors[i]; });
    return found;
  }
  addEventListener('scroll', function () { place(current()); }, { passive: true });
  var menu = document.getElementById('menuBtn'), sheet = document.getElementById('sheet');
  menu.addEventListener('click', function () { var open = !sheet.classList.contains('open'); sheet.classList.toggle('open', open); menu.setAttribute('aria-expanded', String(open)); sheet.setAttribute('aria-hidden', String(!open)); });
  sheet.addEventListener('click', function (e) { if (e.target.tagName === 'A') { sheet.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); } });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') sheet.classList.remove('open'); });
})();

// reveal on scroll
(function () {
  var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }); }, { threshold: 0.15 });
  document.querySelectorAll('.rv').forEach(function (el) { io.observe(el); });
})();

// pinned benefits: the step in view drives the sticky stage and the rail
(function () {
  var steps = [].slice.call(document.querySelectorAll('.step')), stage = document.getElementById('stage'), fill = document.getElementById('railFill');
  if (!stage) return; // only the landing page has the pinned steps
  var views = steps.map(function (s) { var v = document.createElement('div'); v.className = 'v'; v.innerHTML = s.querySelector('.v-inline').innerHTML; stage.appendChild(v); return v; });
  function set(i) {
    steps.forEach(function (s, j) { s.classList.toggle('on', j === i); views[j].classList.toggle('on', j === i); });
    fill.style.height = ((i + 1) / steps.length * 100) + '%';
    fill.style.background = getComputedStyle(steps[i]).getPropertyValue('--c');
    stage.style.background = 'color-mix(in srgb, ' + getComputedStyle(steps[i]).getPropertyValue('--c') + ' 14%, var(--surface))';
  }
  var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) set(steps.indexOf(e.target)); }); }, { rootMargin: '-45% 0px -45% 0px' });
  steps.forEach(function (s) { io.observe(s); }); set(0);
})();

// accordions (faq and troubleshooting)
document.querySelectorAll('.q button').forEach(function (b) {
  b.addEventListener('click', function () { var q = b.parentElement, open = !q.classList.contains('open'); q.classList.toggle('open', open); b.setAttribute('aria-expanded', String(open)); });
});

// footer wordmark: letters lift and turn green near the cursor
(function () {
  var mark = document.getElementById('mark');
  'farmtwin'.split('').forEach(function (ch) { var s = document.createElement('span'); s.textContent = ch; mark.appendChild(s); });
  var spans = [].slice.call(mark.children);
  mark.addEventListener('pointermove', function (e) { spans.forEach(function (s) { var r = s.getBoundingClientRect(); s.classList.toggle('up', Math.abs(e.clientX - (r.left + r.width / 2)) < r.width * 1.6); }); });
  mark.addEventListener('pointerleave', function () { spans.forEach(function (s) { s.classList.remove('up'); }); });
})();
