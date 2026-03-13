// ─── AR namespace & shared state ──────────────────────────────────────────────
window.AR = window.AR || {};

// ─── Mutable application state ───────────────────────────────────────────────
AR.state = {
  midiAccess:       null,
  rytmInput:        null,
  rytmOutput:       null,
  sysexBuf:         [],
  inSysex:          false,
  lastRaw:          null,    // decoded pattern bytes
  lastKit:          null,    // decoded kit bytes
  lastKitSyx:       null,    // original kit sysex bytes (for saving)
  lastSyxMeta:      null,    // { devId, dumpId, verHi, verLo, objNr }
  plockValues:      null,    // plockValues[track] = Map<plockType, Uint8Array[64]>
  plockFineValues:  null,    // plockFineValues[track] = Map<plockType, Uint8Array[64]> (0x80 companions)
  stepPage:         0,
  openPanel:        null,    // { t, s, el }
  openTrackPanel:   null,    // { t, el }
  soundPool:        new Map(),      // slot (0-127) → decoded raw sound bytes
  soundPoolSyx:     new Map(),      // slot (0-127) → original sysex bytes (for saving)
  pendingSoundReqs: new Set(),      // slot numbers awaiting response
  savePending:      false,          // true while waiting for full pool before saving
  lastPatName:      '',             // pattern name for meta display
};

// ─── UI element references (populated by AR.initUI after DOM ready) ──────────
AR.ui = {};

AR.initUI = function() {
  AR.ui.btnConnect  = document.getElementById('btn-connect');
  AR.ui.btnRefresh  = document.getElementById('btn-refresh');
  AR.ui.btnLoadSyx  = document.getElementById('btn-load-syx');
  AR.ui.btnSaveSyx  = document.getElementById('btn-save-syx');
  AR.ui.btnSend     = document.getElementById('btn-send');
  AR.ui.syxFileIn   = document.getElementById('syx-file');
  AR.ui.btnPage0    = document.getElementById('btn-page0');
  AR.ui.btnPage1    = document.getElementById('btn-page1');
  AR.ui.statusEl    = document.getElementById('status');
  AR.ui.portInfoEl  = document.getElementById('port-info');
  AR.ui.metaEl      = document.getElementById('pattern-meta');
  AR.ui.gridEl      = document.getElementById('grid');
};

// ─── UI helpers ──────────────────────────────────────────────────────────────
AR.setStatus = function(msg, cls) {
  AR.ui.statusEl.textContent = msg;
  AR.ui.statusEl.className   = cls || '';
};
