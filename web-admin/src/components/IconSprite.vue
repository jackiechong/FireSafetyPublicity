<template>
  <svg width="0" height="0" style="position: absolute" aria-hidden="true" focusable="false">
    <defs>
      <g id="i-flame"><path d="M12 3c1.6 3.2.6 4.8-.6 6.1-1.2 1.3-2.1 2.3-2.1 3.9a3.7 3.7 0 0 0 7.4 0c0-1-.3-1.9-.8-2.7 2.3 1.4 3.7 3.6 3.7 6.1A7.6 7.6 0 0 1 12 24a7.6 7.6 0 0 1-7.6-7.6C4.4 11 8.6 8.4 12 3Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" /></g>
      <g id="i-grid"><rect x="3" y="3" width="7" height="7" rx="1.2" /><rect x="14" y="3" width="7" height="7" rx="1.2" /><rect x="3" y="14" width="7" height="7" rx="1.2" /><rect x="14" y="14" width="7" height="7" rx="1.2" /></g>
      <g id="i-list"><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01" /></g>
      <g id="i-radar"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4.5" /><path d="M12 12 18 7" /></g>
      <g id="i-users"><path d="M16 20v-1.6a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4V20" /><circle cx="9" cy="7.4" r="3.4" /><path d="M17.5 14.2a4 4 0 0 1 3.5 3.9V20M16.2 4.3a3.4 3.4 0 0 1 0 6.4" /></g>
      <g id="i-building"><path d="M3.5 21h17M5.5 21V6.2a1 1 0 0 1 .7-1l6-1.9a1 1 0 0 1 1.3 1V21M18.5 21V10.5a1 1 0 0 0-.7-1l-3.5-1" /><path d="M8.6 8.6h.01M8.6 12h.01M8.6 15.4h.01M11.6 8.6h.01M11.6 12h.01M11.6 15.4h.01" /></g>
      <g id="i-chart"><path d="M3.5 3.5v17h17" /><path d="M7.5 16v-4M12 16V8.5M16.5 16v-6" /></g>
      <g id="i-search"><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.4 15.4 21 21" /></g>
      <g id="i-book"><path d="M4 5.2A2.2 2.2 0 0 1 6.2 3H20v15.4H6.2A2.2 2.2 0 0 0 4 20.6V5.2Z" /><path d="M8 7.5h8M8 11h5.5" /></g>
      <g id="i-shield"><path d="M12 3 5 6v5.6c0 4.2 2.9 7.9 7 9.4 4.1-1.5 7-5.2 7-9.4V6l-7-3Z" /><path d="m9.2 11.8 2 2 3.6-3.9" /></g>
      <g id="i-sliders"><path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h9M17 17h3" /><circle cx="15" cy="7" r="2" /><circle cx="9" cy="12" r="2" /><circle cx="15" cy="17" r="2" /></g>
      <g id="i-bell"><path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6Z" /><path d="M10.4 19a2 2 0 0 0 3.2 0" /></g>
      <g id="i-help"><circle cx="12" cy="12" r="9" /><path d="M9.6 9.4a2.5 2.5 0 1 1 3.4 2.3c-.7.3-1 .9-1 1.6v.5" /><path d="M12 17h.01" /></g>
      <g id="i-chevron"><path d="m9 5 7 7-7 7" /></g>
      <g id="i-chevron-l"><path d="m15 5-7 7 7 7" /></g>
      <g id="i-chevron-d"><path d="m5 9 7 7 7-7" /></g>
      <g id="i-more"><circle cx="5.5" cy="12" r="1.5" fill="currentColor" stroke="none" /><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" /><circle cx="18.5" cy="12" r="1.5" fill="currentColor" stroke="none" /></g>
      <g id="i-refresh"><path d="M20 11a8 8 0 1 0-2.6 6.4" /><path d="M20 5v6h-6" /></g>
      <g id="i-download"><path d="M12 4v10M8 10.5l4 4 4-4M4.5 19h15" /></g>
      <g id="i-upload"><path d="M12 16V6M8 9.5l4-4 4 4M4.5 19h15" /></g>
      <g id="i-plus"><path d="M12 5v14M5 12h14" /></g>
      <g id="i-x"><path d="M6 6l12 12M18 6 6 18" /></g>
      <g id="i-check"><path d="m5 12.5 4.5 4.5L19 7" /></g>
      <g id="i-alert"><path d="M12 8.5v5" /><path d="M12 17h.01" /><path d="M10.3 3.9 2.6 17.4a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></g>
      <g id="i-trash"><path d="M4 7h16M9.5 7V4.6h5V7M6.5 7l.8 12.2a1.6 1.6 0 0 0 1.6 1.5h6.2a1.6 1.6 0 0 0 1.6-1.5L17.5 7" /></g>
      <g id="i-edit"><path d="M4 20h4L20 8l-4-4L4 16v4Z" /><path d="m14.5 5.5 4 4" /></g>
      <g id="i-clock"><circle cx="12" cy="12" r="9" /><path d="M12 7.5V12l3 2" /></g>
      <g id="i-pin"><path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z" /><circle cx="12" cy="10" r="2.6" /></g>
      <g id="i-qr"><rect x="3.5" y="3.5" width="6.5" height="6.5" rx="1" /><rect x="14" y="3.5" width="6.5" height="6.5" rx="1" /><rect x="3.5" y="14" width="6.5" height="6.5" rx="1" /><path d="M14 14h3v3h-3zM20.5 14v3M14 20.5h6.5" /></g>
      <g id="i-phone"><rect x="6.5" y="2.5" width="11" height="19" rx="2.4" /><path d="M10.5 5.2h3" /></g>
      <g id="i-logout"><path d="M15 17l5-5-5-5M20 12H9M12 4H5.5A1.5 1.5 0 0 0 4 5.5v13A1.5 1.5 0 0 0 5.5 20H12" /></g>
      <g id="i-inbox"><path d="M3.5 13h4l1.4 2.5h6.2L16.5 13h4" /><path d="M5.4 4.6 3.5 13v5.4A1.6 1.6 0 0 0 5.1 20h13.8a1.6 1.6 0 0 0 1.6-1.6V13l-1.9-8.4A1.6 1.6 0 0 0 17 3.4H7a1.6 1.6 0 0 0-1.6 1.2Z" /></g>
      <g id="i-trend"><path d="M3.5 17 9 11l3.5 3.5L20 7" /><path d="M15 7h5v5" /></g>
      <g id="i-key"><circle cx="8" cy="15.5" r="3.5" /><path d="m10.6 13 8-8M16 5.5 18.5 8l2-2L18 3.5" /></g>
      <g id="i-copy"><rect x="8.5" y="8.5" width="12" height="12" rx="1.8" /><path d="M15.5 5.5h-10a1.5 1.5 0 0 0-1.5 1.5v10" /></g>
      <g id="i-doc"><path d="M13.5 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.5L13.5 3Z" /><path d="M13 3v6h6" /></g>
      <g id="i-eye"><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" /><circle cx="12" cy="12" r="3" /></g>
      <g id="i-image"><rect x="3.5" y="4.5" width="17" height="15" rx="2" /><circle cx="8.5" cy="9.5" r="1.6" /><path d="m4.5 17 5-5 4 4 2.5-2.5 3.5 3.5" /></g>
      <g id="i-layers"><path d="m12 3 8.5 4.5L12 12 3.5 7.5 12 3Z" /><path d="m4 12 8 4.3 8-4.3M4 16.4l8 4.3 8-4.3" /></g>
      <g id="i-calendar"><rect x="3.5" y="5" width="17" height="16" rx="2" /><path d="M3.5 10h17M8 3v4M16 3v4" /></g>
      <g id="i-palette"><circle cx="12" cy="12" r="9" /><circle cx="9" cy="9" r="1.2" /><circle cx="15" cy="9" r="1.2" /><circle cx="16" cy="14.5" r="1.2" /></g>
    </defs>
  </svg>
</template>
