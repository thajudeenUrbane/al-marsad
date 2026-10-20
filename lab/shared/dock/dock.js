/* Dock: any floating panel can be minimised to a dot in a corner, and "full view" hides every panel
   behind a single dot, so the world can be seen whole. Shared by the al-Marṣad lab products.

   Dock.init({
     storeKey: "hijrah-night-2",            // localStorage namespace (state is per product, per browser)
     panels: [{ id, el, label, glyph, corner: "tl"|"tr"|"bl"|"br", buttonHost?, buttonClass?, prepend?, noButton? }],
     fullKey: "f",                          // keyboard toggle for full view (Escape also leaves it)
     onChange: state => {}                  // optional, after every change
   }) -> { minimise(id), restore(id), setFull(on), toggleFull(), state }

   Dots can be dragged to any corner (they snap to the nearest one) or moved with the arrow keys
   when focused; the chosen corner is remembered. Storage failures are ignored: the dock still works. */
(function () {
  "use strict";
  const CORNERS = ["tl", "tr", "bl", "br"];
  const load = (k, d) => { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } };
  const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode: keep going */ } };

  function init(opts) {
    const key = (opts.storeKey || "dock") + ":dock";
    const st = Object.assign({ min: {}, corners: {}, full: false }, load(key, {}));
    const panels = opts.panels.filter(p => p && p.el);
    const docks = {};
    CORNERS.forEach(c => {
      const d = document.createElement("div");
      d.className = "dock dock-" + c;
      d.setAttribute("role", "toolbar");
      d.setAttribute("aria-label", "Minimised panels");
      document.body.appendChild(d);
      docks[c] = d;
    });
    const full = { id: "__full", glyph: opts.fullGlyph || "⤢", label: opts.fullLabel || "all panels", corner: "br" };

    panels.forEach(p => {
      if (p.noButton) return;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "dock-min " + (p.buttonClass || "");
      b.title = "Minimise " + p.label;
      b.setAttribute("aria-label", "Minimise " + p.label);
      b.textContent = "–";
      b.addEventListener("click", e => { e.stopPropagation(); minimise(p.id); });
      const host = p.buttonHost || p.el;
      if (p.prepend) host.prepend(b); else host.appendChild(b);
    });

    const cornerOf = p => st.corners[p.id] || p.corner || "br";

    function dot(p, activate) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "dock-dot";
      b.dataset.id = p.id;
      b.textContent = p.glyph || "•";
      b.title = "Show " + p.label + " · drag to another corner";
      b.setAttribute("aria-label", "Show " + p.label);
      let start = null, moved = false;
      b.addEventListener("pointerdown", e => { start = { x: e.clientX, y: e.clientY }; moved = false; b.setPointerCapture(e.pointerId); });
      b.addEventListener("pointermove", e => {
        if (!start) return;
        if (!moved && Math.hypot(e.clientX - start.x, e.clientY - start.y) > 8) { moved = true; b.classList.add("dragging"); }
        if (moved) { b.style.position = "fixed"; b.style.left = (e.clientX - 20) + "px"; b.style.top = (e.clientY - 20) + "px"; }
      });
      b.addEventListener("pointerup", e => {
        if (!start) return;
        start = null;
        if (moved) {
          st.corners[p.id] = (e.clientY < innerHeight / 2 ? "t" : "b") + (e.clientX < innerWidth / 2 ? "l" : "r");
          save(key, st);
          render(p.id);
        }
      });
      b.addEventListener("click", e => { if (moved) { e.preventDefault(); moved = false; return; } activate(); });
      b.addEventListener("keydown", e => {
        const dir = { ArrowLeft: "l", ArrowRight: "r", ArrowUp: "t", ArrowDown: "b" }[e.key];
        if (!dir) return;
        e.preventDefault();
        const c = cornerOf(p);
        st.corners[p.id] = "tb".includes(dir) ? dir + c[1] : c[0] + dir;
        save(key, st);
        render(p.id);
      });
      return b;
    }

    function render(focusId) {
      CORNERS.forEach(c => { docks[c].textContent = ""; });
      panels.forEach(p => p.el.classList.toggle("dock-hidden", !!(st.full || st.min[p.id])));
      if (st.full) docks[cornerOf(full)].appendChild(dot(full, () => setFull(false)));
      else panels.forEach(p => { if (st.min[p.id]) docks[cornerOf(p)].appendChild(dot(p, () => restore(p.id))); });
      document.body.classList.toggle("dock-full", !!st.full);
      if (focusId) { const f = document.querySelector(`.dock-dot[data-id="${focusId}"]`); if (f) f.focus(); }
      if (opts.onChange) opts.onChange(st);
    }
    function minimise(id) { st.min[id] = true; save(key, st); render(id); }
    function restore(id) { delete st.min[id]; save(key, st); render(); }
    function setFull(on) { st.full = !!on; save(key, st); render(on ? "__full" : null); }

    document.addEventListener("keydown", e => {
      if (e.target.closest && e.target.closest("input, textarea, select, [contenteditable]")) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key.toLowerCase() === (opts.fullKey || "f")) setFull(!st.full);
      else if (e.key === "Escape" && st.full) setFull(false);
    });
    render();
    return { minimise, restore, setFull, toggleFull: () => setFull(!st.full), state: st };
  }

  window.Dock = { init };
})();
