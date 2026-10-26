/* Small inline SVGs, shared across controls without another runtime. */
(() => {
  const svg=path=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
  window.DirectorIcons={
    chevron:svg('<path d="m6 9 6 6 6-6"/>'),
    close:svg('<path d="m6 6 12 12M6 18 18 6"/>'),
    plus:svg('<path d="M12 5v14M5 12h14"/>'),
    pencil:svg('<path d="m16 3 5 5-12 12-6 1 1-6ZM14 5l5 5"/>'),
    trash:svg('<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>'),
    left:svg('<path d="m14 6-6 6 6 6"/>'),
    right:svg('<path d="m10 6 6 6-6 6"/>'),
    play:svg('<path d="m9 5 11 7-11 7Z"/>'),
    skip:svg('<path d="m5 5 10 7-10 7Z"/><path d="M19 5v14"/>'),
    pause:svg('<path d="M8 5v14M16 5v14"/>'),
    waveform:svg('<path d="M3 10v4M7 6v12M11 3v18M15 7v10M19 5v14M23 10v4"/>'),
    mic:svg('<rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>'),
    advanced:svg('<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>'),
    upscale:svg('<path d="M14 3h7v7M21 3l-9 9M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>'),
    save:svg('<path d="M5 3h14v18l-7-4-7 4Z"/>'),
    download:svg('<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>'),
    reset:svg('<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>'),
    image:svg('<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 6-6 4 4 3-3 5 5"/>'),
  };
})();
