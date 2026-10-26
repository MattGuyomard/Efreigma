// Keep this layer outside Streamlit's rerendered content during navigation.
(() => {
  if (!window.efreigmaTransition) {
    const layer = document.createElement('div');
    layer.id = 'efreigma-page-transition';
    layer.hidden = true;
    layer.setAttribute('role', 'status');
    layer.setAttribute('aria-live', 'polite');
    layer.innerHTML = `<style>
      #efreigma-page-transition { position:fixed; inset:0; z-index:999999;
        display:grid; place-items:center; background-color:#8b9983; color:#eee8d5;
        background-image:radial-gradient(ellipse at center, #a2ae94 0%, #7b8975 100%);
        opacity:1; transition:opacity 220ms ease; pointer-events:auto; }
      #efreigma-page-transition[hidden] { display:none; }
      #efreigma-page-transition.leaving { opacity:0; pointer-events:none; }
      #efreigma-page-transition .note { position:relative; padding:28px 40px 24px;
        background:#305b4d; border:7px solid #b89c77; border-radius:12px;
        box-shadow:0 3px 0 #806c54, 0 12px 28px #35493840,
          inset 0 0 0 2px #24473d;
        font:700 19px 'Comic Sans MS','Trebuchet MS',sans-serif; text-align:center;
        max-width:calc(100vw - 64px); box-sizing:border-box; }
      #efreigma-page-transition .note::after { content:''; position:absolute;
        width:24px; height:5px; bottom:6px; right:20px;
        border-radius:2px; background:#dcd9c8; transform:rotate(-3deg); }
      #efreigma-page-transition .dots { display:block; margin-top:16px; }
      #efreigma-page-transition .dots span { display:inline-block; width:8px;
        height:6px; margin:0 5px; border-radius:50%; background:#c4d3b6;
        animation:efreigma-dot 900ms ease-in-out infinite alternate; }
      #efreigma-page-transition .dots span:nth-child(2) { animation-delay:150ms; }
      #efreigma-page-transition .dots span:nth-child(3) { animation-delay:300ms; }
      @keyframes efreigma-dot { to { transform:translateY(-4px); opacity:.45; } }
      @media(prefers-reduced-motion:reduce) {
        #efreigma-page-transition { transition:none; }
        #efreigma-page-transition .dots span { animation:none; }
      }
    </style><div class="note">Un instant…<span class="dots" aria-hidden="true"><span></span><span></span><span></span></span></div>`;
    document.body.appendChild(layer);
    const state = { layer, target: null, started: 0, timer: null, cleanup: null };
    const dismiss = () => {
      clearTimeout(state.timer);
      state.target = null;
      layer.classList.add('leaving');
      state.cleanup = setTimeout(() => { layer.hidden = true; }, 230);
    };
    state.ready = (path) => {
      if (state.target !== path) return;
      // Let the completed page paint behind the layer before revealing it.
      requestAnimationFrame(() => requestAnimationFrame(() => {
        clearTimeout(state.timer);
        state.timer = setTimeout(dismiss, Math.max(0, 180 - (performance.now() - state.started)));
      }));
    };
    document.addEventListener('click', (event) => {
      const link = event.target.closest?.('[data-testid="stPageLink"] a');
      if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const destination = new URL(link.href, location.href);
      if (destination.origin !== location.origin || destination.pathname === location.pathname) return;
      clearTimeout(state.timer);
      clearTimeout(state.cleanup);
      state.target = destination.pathname;
      state.started = performance.now();
      layer.classList.remove('leaving');
      layer.hidden = false;
      // A failed navigation must never leave the interface covered indefinitely.
      state.timer = setTimeout(dismiss, 8000);
    }, true);
    window.efreigmaTransition = state;
  }
})();
