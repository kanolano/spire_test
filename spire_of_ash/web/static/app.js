"use strict";
let S = null, prev = null, sel = null, busy = false;
let lastScreen = null, lastTurn = -1;   // so animations only fire on real changes
let pendingFx = false;                  // a fresh state to animate, not a re-render
let offline = false;
let dailyMode = false;                  // share today's seed with everyone else
let SHOP_KEYS = {};                     // letter -> action, rebuilt by renderShop

const SPRITE = {
  "Jaw Worm":"🪱","Cultist":"🧙","Red Louse":"🐜","Fungi Beast":"🍄","Acid Slime":"🟢",
  "Spike Slime":"🔵","Slime Spawn":"🫧","Mad Gremlin":"👺","Sneaky Gremlin":"🗡️",
  "Fat Gremlin":"👹","Shield Gremlin":"🛡️","Sentry":"🗿","Byrd":"🦅","Chosen":"🧛",
  "Mystic":"🧝","Gremlin Nob":"👺","Lagavulin":"🐛","Book of Stabbing":"📕",
  "Taskmaster":"🪓","The Guardian":"🤖","Hexaghost":"👻","Slime Boss":"🟩","The Champ":"⚔️",
  "Ash Warden":"🛡️","The Ashen Sovereign":"👑"
};
const RELIC_ICON = {
  "Burning Blood":"🩸","Bag of Marbles":"🔮","Anchor":"⚓","Vajra":"🔱",
  "Oddly Smooth Stone":"🥚","Bronze Scales":"⚖️","Blood Vial":"🧪","Lantern":"🏮",
  "Happy Flower":"🌼","Pen Nib":"🖋️","Strawberry":"🍓","Meat on the Bone":"🍖",
  "Kunai":"🗡️","Bag of Preparation":"🎒","Art of War":"📜","Ash Phial":"⚱️",
  "Emberheart":"🫀","Ashglass Vial":"🫙","Smoulder Stone":"🪨","Grave Ash":"⚰️",
  "Bone Dice":"🎲","Oathkeeper":"🕯️","Hollow Lantern":"🏮"
};
const POTION_ICON = {
  "Fire Potion":"🔥","Block Potion":"🛡️","Strength Potion":"💪","Energy Potion":"⚡",
  "Swift Potion":"💨","Explosive Potion":"💥","Weak Potion":"🌀","Fear Potion":"😱",
  "Blood Potion":"🩸"
};
const NODE = {
  monster:{g:"⚔",c:"#c8503f",t:"Combat"}, elite:{g:"☠",c:"#a874d4",t:"Elite"},
  event:{g:"?",c:"#4e9ec4",t:"Unknown"},  rest:{g:"♨",c:"#6fbf73",t:"Campfire"},
  shop:{g:"$",c:"#e3b86a",t:"Merchant"},  treasure:{g:"◈",c:"#e3b86a",t:"Treasure"},
  boss:{g:"♛",c:"#c8503f",t:"Boss"}
};
const LETTERS = "abcdefgh";
const POTION_KEYS = "qwrtyu";          // was hardcoded as "qwr" in three places
// The shop needs its own letters: POTION_KEYS[2] is "r", which the relic wants.
const SHOP_POTION_KEYS = "qwe";
// Anything carrying these two attributes gets the hover/focus/tap tooltip.
const tipAttrs = (name, desc) =>
  ` data-tip="${esc(name)}" data-tip-desc="${esc(desc || "")}"`;
const statusChip = s =>
  `<span class="chip st" data-k="${esc(s.key)}" tabindex="0"` +
  tipAttrs(s.name || s.label, s.desc) +
  ` aria-label="${esc(s.name || s.label)} ${s.value}: ${esc(s.desc || "")}">` +
  `${esc(s.label)} ${s.value}</span>`;
// The centred continue/skip/leave button was copy-pasted six times.
function ctaButton(label, onclick, cls){
  const b = el("button", cls || "tbtn", label);
  b.style.cssText = "display:block;margin:24px auto";
  b.onclick = onclick;
  return b;
}
const $ = s => document.querySelector(s);
const el = (tag, cls, html) => { const d=document.createElement(tag);
  if(cls) d.className=cls; if(html!=null) d.innerHTML=html; return d; };
// Quotes matter: esc() output is interpolated into double-quoted attributes.
const ESCAPES = {"<":"&lt;", ">":"&gt;", "&":"&amp;", '"':"&quot;", "'":"&#39;"};
const esc = s => String(s).replace(/[<>&"']/g, m => ESCAPES[m]);

/* ── connection state ──────────────────────────────────────
   The original UI reported nothing: a failed request went to console.error, a
   failed boot left a permanently blank stage, and a dead server looked exactly
   like a working one. */
function toast(message, kind){
  const box = $("#toasts");
  const node = el("div", "toast" + (kind ? " " + kind : ""), esc(message));
  box.appendChild(node);
  setTimeout(() => node.remove(), 4200);
}
function setBusy(on){
  busy = on;
  document.body.classList.toggle("busy", on);
}
function setOffline(on, message){
  offline = on;
  const curtain = $("#curtain");
  if(message) $("#curtain-msg").textContent = message;
  curtain.hidden = !on;
}

/* ── tooltips ───────────────────────────────────────────────
   Status chips were cursor:help with nothing behind them — the label is a
   four-letter abbreviation and the game never said anywhere what it meant.
   Relics and potions had native title=, which is slow to appear and shows
   nothing at all on touch. Both now feed one element. */
let tipFor = null;

function showTip(node){
  const name = node.getAttribute("data-tip");
  if(!name) return;
  const desc = node.getAttribute("data-tip-desc");
  const tip = $("#tip");
  tip.innerHTML = `<b>${esc(name)}</b>` + (desc ? `<span>${esc(desc)}</span>` : "");
  tip.hidden = false;
  tipFor = node;
  placeTip(node);
}
function placeTip(node){
  const tip = $("#tip"), r = node.getBoundingClientRect(), pad = 8;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  const left = Math.min(Math.max(pad, r.left + r.width/2 - w/2),
                        window.innerWidth - w - pad);
  // below the chip, unless that would run off the bottom
  let top = r.bottom + pad;
  if(top + h > window.innerHeight - pad) top = r.top - h - pad;
  tip.style.left = Math.round(left) + "px";
  tip.style.top = Math.round(Math.max(pad, top)) + "px";
}
function hideTip(){
  if(!tipFor) return;
  $("#tip").hidden = true;
  tipFor = null;
}

async function api(path, options){
  const r = await fetch(path, options);          // throws only on network failure
  const text = await r.text();
  let body = null;
  if(text){
    try{ body = JSON.parse(text); }
    catch(e){ body = null; }
  }
  if(!r.ok){
    const err = new Error((body && body.error) || `Request failed (${r.status})`);
    err.status = r.status;
    throw err;
  }
  return body;
}

/* Throwing a run away had a server route and no way at all to reach it, so
   changing class meant dying first — and even then "Climb again" silently
   restarted the class you had just finished with. */
async function abandon(){
  if(busy || offline) return;
  setBusy(true);
  try{
    const next = await api("/abandon", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:"{}"
    });
    prev = null; S = next; sel = null; pendingFx = false;
    lastScreen = null; lastTurn = -1;
    setOffline(false);
    render();
  }catch(e){
    if(e.status) toast(e.message);
    else setOffline(true, "Lost contact with the Spire.");
  }finally{
    setBusy(false);
  }
}

function confirmQuit(){
  if(!S || S.screen === "select") return;
  const ending = S.screen === "gameover" || S.screen === "win";
  $("#overlay-title").textContent = "Abandon this climb";
  const body = $("#overlay-body");
  body.innerHTML = "";
  body.appendChild(el("h2","title", ending ? "Choose another class"
                                           : "Abandon this climb?"));
  body.appendChild(el("div","sub", ending
    ? "You will go back to the character select."
    : `You are on floor ${S.floor} of act ${S.act}. The run ends here, is not `+
      `recorded, and you go back to the character select.`));
  const box = el("div","choices");
  const yes = el("button","choice",
    `<span class="k">1</span> <b>${ending ? "Pick a class" : "Abandon the run"}</b>`);
  yes.onclick = ()=>{ closeOverlay(); abandon(); };
  const no = el("button","choice",
    `<span class="k">esc</span> <b>${ending ? "Stay here" : "Keep climbing"}</b>`);
  no.onclick = closeOverlay;
  box.appendChild(yes); box.appendChild(no);
  body.appendChild(box);
  overlayConfirm = abandon;
  showOverlay();
}

async function send(action){
  if(busy || offline) return;
  setBusy(true);
  try{
    const next = await api("/action", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(action)
    });
    prev = S; S = next; sel = null; pendingFx = true;
    setOffline(false);
    render();
  }catch(e){
    if(e.status){
      // The engine refused the action and said why — show it and stay put.
      toast(e.message);
      sel = null;
      render();
    }else{
      setOffline(true, "Lost contact with the Spire.");
    }
  }finally{
    setBusy(false);
  }
}

async function boot(){
  setBusy(true);
  try{
    S = await api("/state");
    setOffline(false);
    render();
  }catch(e){
    setOffline(true, e.status
      ? "The Spire could not start a run."
      : "Could not reach the Spire. Is the server running?");
  }finally{
    setBusy(false);
  }
}

/* ── card element ───────────────────────────────────────── */
function cardEl(c, opts={}){
  const d = el("div", "card t-"+c.type + (c.upgraded?" up":"") +
                      (opts.dim||c.playable===false&&opts.combat?" unplayable":"") +
                      (opts.static?" static":"") + (opts.pick?" pick":""));
  d.innerHTML =
    `<div class="cost">${c.cost}</div>` +
    (opts.kbd!=null?`<div class="kbd">${opts.kbd}</div>`:"") +
    `<div class="cname">${esc(c.name)}</div><div class="ctype">${c.type}</div>` +
    `<div class="cdesc">${esc(c.desc)}</div>` +
    (opts.price!=null?`<div class="price">${opts.price} gold</div>`:"");
  if(opts.onclick){
    // Cards are divs, so they need the button contract spelled out.
    d.onclick = opts.onclick;
    d.tabIndex = 0;
    d.setAttribute("role", "button");
    d.addEventListener("keydown", ev => {
      if(ev.key === "Enter" || ev.key === " "){ ev.preventDefault(); opts.onclick(); }
    });
  }
  d.setAttribute("aria-label",
    `${c.name}, ${c.type.toLowerCase()}, cost ${c.cost}. ${c.desc}` +
    (opts.price != null ? ` Price ${opts.price} gold.` : "") +
    (c.playable === false && opts.combat ? " Not playable right now." : ""));
  if(opts.selected){ d.classList.add("sel"); d.setAttribute("aria-pressed", "true"); }
  return d;
}

/* ── top bar ────────────────────────────────────────────── */
function renderTop(){
  const p = S.player;
  // no run in progress yet — the placeholder player behind the select screen is not yours
  $("#top").style.visibility = S.screen === "select" ? "hidden" : "visible";
  $("#s-act").textContent = `Act ${S.act}` + (S.floor>0?` · Floor ${S.floor}`:"");
  const pct = Math.max(0,p.hp)/p.max_hp*100;
  $("#s-hp").style.width = pct+"%";
  $("#s-hpwrap").classList.toggle("low", pct<35);
  $("#s-hptext").textContent = `${p.hp} / ${p.max_hp}`;
  $("#s-gold").innerHTML = `<span class="ic" style="color:var(--gold)">◉</span> ${p.gold}`;
  $("#s-decksize").textContent = `(${p.deck_size})`;
  $("#s-status").innerHTML = p.statuses.map(statusChip).join("");
  // native title= is slow and invisible on touch, so these use the same tooltip
  // as the status chips and stay buttons that open the overlay
  $("#s-relics").innerHTML = p.relics.map((r,i) =>
    `<button class="icon" data-act="relic" data-i="${i}"`+
    tipAttrs(r.name, r.desc) + ` aria-label="${esc(r.name)}: ${esc(r.desc)}">`+
    `${RELIC_ICON[r.name] || "◈"}</button>`).join("");
  $("#s-potions").innerHTML = p.potions.map((q,i) =>
    `<button class="icon potion" data-act="potion" data-i="${i}"`+
    tipAttrs(q.name, q.desc) + ` aria-label="${esc(q.name)}: ${esc(q.desc)}">`+
    `${POTION_ICON[q.name] || "🧪"}`+
    `<span class="key" aria-hidden="true">${POTION_KEYS[i] || ""}</span></button>`).join("");
}

/* ── map ────────────────────────────────────────────────── */
function renderMap(st){
  const m = S.map, W = 640, ROW = 58, H = m.floors.length*ROW + 36;
  const x = (f,i) => 26 + (i+0.5) * (W-40) / m.floors[f].length;
  const y = f => H - 28 - f*ROW;
  const isBoss = f => f === m.floors.length-1;
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">
    <defs>
      <!-- userSpaceOnUse, because a percentage filter region is a percentage of
           the bounding box: a perfectly vertical edge has zero width, so its
           glow region collapsed and the line vanished entirely. -->
      <filter id="glow" filterUnits="userSpaceOnUse"
              x="0" y="0" width="${W}" height="${H}">
        <feGaussianBlur stdDeviation="3.4" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <radialGradient id="ndisc" cx="35%" cy="28%">
        <stop offset="0" stop-color="#3a3052"/><stop offset="1" stop-color="#15111e"/>
      </radialGradient>
      <radialGradient id="ncur" cx="35%" cy="28%">
        <stop offset="0" stop-color="#7a63ad"/><stop offset="1" stop-color="#2a2140"/>
      </radialGradient>
      <radialGradient id="nseen" cx="35%" cy="28%">
        <stop offset="0" stop-color="#241f30"/><stop offset="1" stop-color="#120f19"/>
      </radialGradient>
    </defs>`;
  // floor ticks
  m.floors.forEach((row,f) => {
    svg += `<text x="8" y="${y(f)+4}" font-size="10" fill="#4a4260"
             font-family="Georgia,serif">${f+1}</text>`;
  });
  /* Unexplored edges used to be #332c47 at .6 opacity on a near-black
     background — you could not trace where a path went. Every edge now gets a
     dark casing underneath so it reads against the mottled backdrop, and the
     three states are separated by brightness and dash rather than by opacity. */
  const EDGE = {
    done: {stroke:"#e6bd6c", width:3,   dash:"",     glow:true},
    open: {stroke:"#c0a8f0", width:2.8, dash:"8 5",  glow:true},
    far:  {stroke:"#6b5f92", width:2,   dash:"5 5",  glow:false},
  };
  for(let f=0; f<m.floors.length-1; f++)
    m.floors[f].forEach((n,i) => n.edges.forEach(t => {
      const done = m.visited.some(v=>v[0]===f&&v[1]===i) &&
                   m.visited.some(v=>v[0]===f+1&&v[1]===t);
      const open = f === m.cur_floor && i === m.cur_idx && m.reachable.includes(t);
      const e = EDGE[done ? "done" : (open ? "open" : "far")];
      const ends = `x1="${x(f,i)}" y1="${y(f)}" x2="${x(f+1,t)}" y2="${y(f+1)}"`;
      svg += `<line ${ends} stroke="#0b0812" stroke-width="${e.width + 2.5}"
                stroke-linecap="round" opacity=".85"/>`
          +  `<line ${ends} stroke="${e.stroke}" stroke-width="${e.width}"
                stroke-linecap="round"
                ${e.dash ? `stroke-dasharray="${e.dash}"` : ""}
                ${e.glow ? 'filter="url(#glow)"' : ""}/>`;
    }));
  m.floors.forEach((row,f) => row.forEach((n,i) => {
    const k = NODE[n.type], cur = (f===m.cur_floor && i===m.cur_idx);
    const can = (f === m.cur_floor+1) && m.reachable.includes(i);
    const seen = m.visited.some(v=>v[0]===f&&v[1]===i);
    const r = isBoss(f) ? 23 : 17;
    const fill = cur ? "url(#ncur)" : (seen ? "url(#nseen)" : "url(#ndisc)");
    svg += `<g class="node${can?" can":""}"${can?` data-node="${i}"`:""}>`
        +  `<title>${k.t}${can?" — press "+LETTERS[i]:""}</title>`
        +  (can ? `<circle class="ring" cx="${x(f,i)}" cy="${y(f)}" r="${r+4}" fill="none"
                    stroke="${k.c}" stroke-width="1.5" filter="url(#glow)" opacity=".6"/>` : "")
        +  `<circle class="disc" cx="${x(f,i)}" cy="${y(f)}" r="${r}" fill="${fill}"
              stroke="${cur ? "#f3e2be" : (can ? "#e8c07a" : "#3a3250")}"
              stroke-width="${cur || can ? 2.2 : 1.3}"/>`
        +  `<text x="${x(f,i)}" y="${y(f)+ (isBoss(f)?7:6)}" text-anchor="middle"
              font-size="${isBoss(f)?22:17}" fill="${seen&&!cur ? "#584f6e" : k.c}"
              opacity="${seen || can || cur ? 1 : .85}">${k.g}</text>`
        +  (can ? `<text x="${x(f,i)+r+7}" y="${y(f)+5}" font-size="13" fill="#e8c07a"
                    font-family="Georgia,serif">${LETTERS[i]}</text>` : "")
        + `</g>`;
  }));
  svg += `</svg>`;
  st.appendChild(el("h2","title","Choose your path"));
  st.appendChild(el("div","sub", S.map.cur_floor<0
      ? "The Spire waits. Pick a starting route."
      : "Click a lit node, or press its letter."));
  const wrap = el("div"); wrap.id = "mapwrap"; wrap.innerHTML = svg;
  wrap.addEventListener("click", ev => {
    const g = ev.target.closest("g.node[data-node]");
    if(g) send({type:"map", idx:Number(g.dataset.node)});
  });
  st.appendChild(wrap);
  st.appendChild(el("div","legend", Object.entries(NODE).map(([k,v]) =>
    `<span><span style="color:${v.c}">${v.g}</span>&nbsp;${v.t}</span>`).join("")));
  requestAnimationFrame(()=>{
    const target = wrap.scrollHeight - (Math.max(0,S.map.cur_floor+1)*58) - 280;
    wrap.scrollTop = Math.max(0, target);
  });
}

/* ── combat ─────────────────────────────────────────────── */
function renderCombat(st){
  const cb = S.combat, p = S.player;
  st.appendChild(el("div","sub",`${esc(cb.label)} &nbsp;·&nbsp; turn ${cb.turn}`));

  const foes = el("div"); foes.id = "enemies";
  cb.enemies.forEach((e,i) => {
    const d = el("div","foe"+(e.alive?"":" dead")+(sel&&sel.mode==="target"&&e.alive?" targetable":""));
    d.dataset.foe = i;
    const it = e.intent;
    // Non-attack intents used to read "▲ buff". The move's own name says far
    // more, and the tooltip carries the kind and whatever note it has.
    const GLYPH = {attack:"⚔", block:"🛡", buff:"▲", debuff:"▼"};
    const KIND_TIP = {attack:"It will attack.", block:"It is defending.",
                      buff:"It is strengthening itself.",
                      debuff:"It will weaken you."};
    const badge = !it ? "" :
      `<div class="intent ${it.kind}"` +
      tipAttrs(it.name, it.note || KIND_TIP[it.kind] || "") + `>` +
      (it.kind==="attack"
        ? `${GLYPH.attack} ${it.dmg}${it.hits>1?` × ${it.hits}`:""}${it.extra?" +":""}`
        : `${GLYPH[it.kind]||"●"} ${esc(it.name)}`) +
      `</div>`;
    d.innerHTML =
      (e.alive?badge:"<div class='intent'>slain</div>") +
      `<div class="sprite">${SPRITE[e.name]||"👾"}</div><div class="shadow"></div>` +
      `<div class="fname">${e.alive?`<span style="color:var(--gold)">${LETTERS[i]}</span> · `:""}`+
        `${esc(e.name)}${e.block?`<span class="block-badge">🛡 ${e.block}</span>`:""}</div>` +
      `<div class="fbar"><i style="width:${Math.max(0,e.hp)/e.max_hp*100}%"></i>` +
        `<span class="fnum">${Math.max(0,e.hp)} / ${e.max_hp}</span></div>` +
      `<div class="chips" style="justify-content:center;margin-top:6px">` +
        e.statuses.map(statusChip).join("") + `</div>`;
    if(e.alive){
      d.onclick = () => clickFoe(i);
      d.tabIndex = 0;
      d.setAttribute("role", "button");
      const hp = `${Math.max(0,e.hp)} of ${e.max_hp} hit points`;
      d.setAttribute("aria-label", `${e.name}, ${hp}` +
        (it ? `, intent ${it.kind}${it.kind==="attack"?` ${it.dmg} damage`:""}` : ""));
      d.addEventListener("keydown", ev => {
        if(ev.target !== d) return;   // a focused status chip is not a target pick
        if(ev.key === "Enter" || ev.key === " "){ ev.preventDefault(); clickFoe(i); }
      });
    }
    foes.appendChild(d);
  });
  st.appendChild(foes);

  const bar = el("div"); bar.id = "playerbar";
  bar.innerHTML =
    `<div class="barlog">${cb.log.slice(-3).map(l=>`<div>${esc(l)}</div>`).join("")}</div>` +
    `<div class="barmain">
       <div class="orb">${p.energy}<span style="font-size:12px;opacity:.6">/${p.max_energy}</span></div>
       <div>
         <div class="pname">${esc(p.name)}
           ${p.block?`<span class="block-badge">🛡 ${p.block}</span>`:""}</div>
         <div class="hpwrap" style="width:230px;margin-top:5px">
           <i class="hpfill" style="width:${Math.max(0,p.hp)/p.max_hp*100}%"></i>
           <span class="hptext">${p.hp} / ${p.max_hp}</span></div>
       </div>
     </div>`;
  const right = el("div", "barright");
  right.innerHTML =
    `<div class="piles">
       <button data-act="pile" data-pile="draw_pile">draw ${cb.draw}</button>
       <button data-act="pile" data-pile="discard_pile">discard ${cb.discard}</button>
       <button data-act="pile" data-pile="exhaust_pile">exhaust ${cb.exhaust}</button>
     </div>`;
  bar.appendChild(right);
  st.appendChild(bar);

  const hand = el("div"); hand.id = "hand";
  if(cb.turn !== lastTurn){ hand.className = "deal"; lastTurn = cb.turn; }  // new hand only
  cb.hand.forEach((c,i) => hand.appendChild(cardEl(c, {
    combat:true, kbd:(i+1)%10,
    selected: sel && sel.kind==="card" && sel.idx===i,
    pick: sel && sel.mode==="hand" && i!==sel.idx,
    onclick: () => clickCard(i)
  })));
  st.appendChild(hand);

  const btn = el("button", sel ? "cancel" : null, sel ? "Cancel <kbd>Esc</kbd>"
                                                      : "End turn <kbd>E</kbd>");
  btn.id = "endturn";
  btn.onclick = sel ? (()=>{ sel=null; render(); }) : (()=> send({type:"end_turn"}));
  right.appendChild(btn);
}

function clickCard(i){
  const c = S.combat.hand[i];
  if(sel && sel.mode === "hand"){                     // picking a card to exhaust
    if(i === sel.idx) return;
    send({type:"play", idx:sel.idx, target:sel.target ?? null, exhaust:i});
    return;
  }
  if(!c.playable) return;
  const alive = S.combat.enemies.map((e,j)=>e.alive?j:-1).filter(j=>j>=0);
  if(c.targeted && alive.length > 1){ sel = {kind:"card", idx:i, mode:"target"}; render(); return; }
  const target = c.targeted ? alive[0] : null;
  if(c.needs_hand && S.combat.hand.length > 1){
    sel = {kind:"card", idx:i, mode:"hand", target}; render(); return;
  }
  send({type:"play", idx:i, target, exhaust:null});
}
function clickPotion(i){
  if(S.screen!=="combat") return;
  const q = S.player.potions[i]; if(!q) return;
  const alive = S.combat.enemies.map((e,j)=>e.alive?j:-1).filter(j=>j>=0);
  if(q.targeted && alive.length > 1){ sel = {kind:"potion", idx:i, mode:"target"}; render(); return; }
  send({type:"potion", idx:i, target:q.targeted?alive[0]:null});
}
function clickFoe(i){
  if(!sel || sel.mode!=="target") return;
  if(sel.kind==="potion"){ send({type:"potion", idx:sel.idx, target:i}); return; }
  const c = S.combat.hand[sel.idx];
  if(c.needs_hand && S.combat.hand.length > 1){ sel={...sel, mode:"hand", target:i}; render(); return; }
  send({type:"play", idx:sel.idx, target:i, exhaust:null});
}

/* ── other screens ──────────────────────────────────────── */
/* Rewards used to be granted the instant the last enemy died and reported as
   one run-on sentence. Each one is now a row you take or leave, and the screen
   stays put until you say you are done. */
const REWARD_TITLE = {monster:"Victory", elite:"Elite slain", boss:"Boss slain"};

function rewardRow(icon, name, desc, opts){
  const row = el("div","item reward-row");
  row.innerHTML = `<span class="rico" aria-hidden="true">${icon}</span>` +
    `<span class="nm">${esc(name)}</span><span class="ds">${esc(desc)}</span>`;
  if(opts.taken){
    row.appendChild(el("span","ghost taken","Taken"));
    row.classList.add("done");
    return row;
  }
  const b = el("button","buy", `Take <kbd>${opts.kbd}</kbd>`);
  b.onclick = opts.onclick;
  if(opts.blocked){ b.disabled = true; b.title = opts.blocked; }
  row.appendChild(b);
  return row;
}

function renderReward(st){
  const r = S.reward;
  st.appendChild(el("h2","title", REWARD_TITLE[r.kind] || "Victory"));
  if(r.log && r.log.length){
    st.appendChild(el("div","combatlog", r.log.map(esc).join("<br>")));
  }
  st.appendChild(el("div","sub", `You find ${r.gold} gold.`));

  const items = el("div","rewards");
  if(r.relic){
    items.appendChild(rewardRow(RELIC_ICON[r.relic.name] || "◈", r.relic.name,
      r.relic.desc, {kbd:"R", taken:r.relic_taken,
                     onclick:()=>send({type:"reward", what:"relic"})}));
  }
  if(r.potion){
    items.appendChild(rewardRow(POTION_ICON[r.potion.name] || "🧪", r.potion.name,
      r.potion.desc, {kbd:"P", taken:r.potion_taken,
                      blocked: r.potions_full ? "Your potion slots are full" : null,
                      onclick:()=>send({type:"reward", what:"potion"})}));
  }
  if(items.children.length) st.appendChild(items);

  if(r.card_taken){
    st.appendChild(el("div","center ghost","Card added to your deck."));
  }else{
    st.appendChild(el("div","center ghost","Choose one card to add to your deck"));
    const row = el("div","row"); row.style.marginTop = "16px";
    r.cards.forEach((c,i) => row.appendChild(cardEl(c,{kbd:i+1,
      onclick:()=>send({type:"reward", what:"card", idx:i})})));
    st.appendChild(row);
  }
  const left = (r.relic && !r.relic_taken)
            || (r.potion && !r.potion_taken && !r.potions_full)
            || !r.card_taken;
  st.appendChild(ctaButton((left ? "Leave the rest" : "Continue") + " <kbd>Enter</kbd>",
                           ()=> send({type:"reward_done"}), left ? "tbtn" : "cta"));
}

function renderChoose(st){
  const ch = S.choose;
  st.appendChild(el("h2","title",esc(ch.title)));
  const row = el("div","row"); row.style.marginTop="14px";
  ch.cards.forEach((c,i) => row.appendChild(cardEl(c,{pick:true,
    kbd:i<9?i+1:null, onclick:()=>send({type:"choose", idx:i})})));
  st.appendChild(row);
  if(ch.kind === "remove"){
    st.appendChild(ctaButton("Change my mind <kbd>Esc</kbd>",
                             ()=> send({type:"choose", idx:null})));
  }
}

function renderRest(st){
  const p = S.player, full = p.hp >= p.max_hp;
  st.appendChild(el("h2","title","A campfire"));
  st.appendChild(el("div","sub","The embers are warm. You have time for one thing."));
  const heal = Math.min(p.max_hp - p.hp, Math.max(1, Math.floor(p.max_hp*0.3)));
  const box = el("div","choices");
  const opt = (kbd, label, note, action, disabled) => {
    const b = el("button","choice",
      `<span class="k">${kbd}</span> <b>${label}</b> — ${note}`);
    // Rest was offered as a live option at full HP, healing nothing.
    if(disabled){ b.disabled = true; b.classList.add("spent"); }
    else b.onclick = ()=> send(action);
    box.appendChild(b);
  };
  opt(1, "Rest", full ? `you are already at ${p.hp}/${p.max_hp}`
                      : `heal ${heal} HP <span class="ghost">(you are at `+
                        `${p.hp}/${p.max_hp})</span>`,
      {type:"rest"}, full);
  opt(2, "Smith", "upgrade a card", {type:"smith"});
  opt(3, "Purge", "remove a card from your deck", {type:"purge"});
  st.appendChild(box);
}

function renderShop(st){
  const sh = S.shop, gold = S.player.gold;
  st.appendChild(el("h2","title","The merchant"));
  st.appendChild(el("div","sub",`Your gold: ${gold}`));
  const row = el("div","row"); row.style.margin="18px 0 26px";
  sh.cards.forEach((c,i) => row.appendChild(cardEl(c,{price:c.price, kbd:i+1,
    dim: c.price>gold, onclick: ()=> c.price<=gold && send({type:"shop_buy",what:"card",idx:i})})));
  st.appendChild(row);
  // Everything below the cards used to be mouse-only, and its "not enough gold"
  // was a native title= that never appeared on touch.
  const stall = (kbd, name, desc, price, action, blocked) => {
    const it = el("div","item",
      `<span class="nm">${esc(name)}</span><span class="ds">${esc(desc)}</span>`);
    const b = el("button","buy",`<kbd>${kbd}</kbd> ${price} gold`);
    const why = blocked || (gold < price ? "Not enough gold" : "");
    b.disabled = Boolean(why);
    if(why) b.setAttribute("data-tip", why);
    else b.onclick = ()=> send(action);
    it.appendChild(b); st.appendChild(it);
    SHOP_KEYS[kbd] = why ? null : action;
  };
  SHOP_KEYS = {};
  if(sh.relic){
    stall("r", sh.relic.name, sh.relic.desc, sh.relic_price,
          {type:"shop_buy", what:"relic"});
  }
  const full = S.player.potions.length >= S.player.max_potions;
  sh.potions.forEach((q,i) =>
    stall(SHOP_POTION_KEYS[i], q.name, q.desc, q.price,
          {type:"shop_buy", what:"potion", idx:i},
          full ? "Your potion slots are full" : ""));
  if(!sh.removed){
    stall("x", "Card removal", "Purge one card from your deck.", sh.removal_price,
          {type:"shop_buy", what:"removal"});
  }
  st.appendChild(ctaButton("Leave <kbd>Esc</kbd>", ()=> send({type:"shop_leave"})));
}

function renderEvent(st){
  const ev = S.event;
  st.appendChild(el("h2","title",esc(ev.title)));
  st.appendChild(el("div","narrative",esc(ev.text)));
  if(ev.result === null){
    const box = el("div","choices");
    ev.options.forEach((o,i) => {
      // the label is flavour; the preview is what the choice actually costs
      const b = el("button","choice",`<span class="k">${i+1}</span> ${esc(o.label)}` +
        (o.preview ? `<span class="preview">${esc(o.preview)}</span>` : ""));
      b.onclick = ()=> send({type:"event_choose", idx:i});
      box.appendChild(b);
    });
    st.appendChild(box);
  }else{
    st.appendChild(el("div","result",esc(ev.result)));
    st.appendChild(ctaButton("Continue <kbd>Enter</kbd>", ()=> send({type:"event_done"})));
  }
}

function renderTreasure(st){
  const t = S.treasure;
  st.appendChild(el("h2","title","A chest"));
  st.appendChild(el("div","sub",`${t.gold} gold spills out.`));
  st.appendChild(el("div","item",
    `<span class="nm">${esc(t.relic.name)}</span><span class="ds">${esc(t.relic.desc)}</span>`));
  st.appendChild(ctaButton("Continue <kbd>Enter</kbd>", ()=> send({type:"treasure_done"})));
}

function renderSelect(st){
  st.appendChild(el("h1","title big","Choose your climber"));
  st.appendChild(el("div","sub","Each class brings its own deck, relic and card pool."));
  const row = el("div","classes");
  (S.classes||[]).forEach((c,i) => {
    const b = el("button","cls");
    b.innerHTML =
      `<div class="cls-name"><span class="k">${i+1}</span>${esc(c.name)}</div>`+
      `<div class="cls-stats">${c.hp} HP<span>${c.energy} energy</span>`+
      `<span>${c.cards} cards in pool</span></div>`+
      `<div class="cls-blurb">${esc(c.blurb)}</div>`+
      `<div class="cls-line"><b>${esc(c.relic.name)}</b> — ${esc(c.relic.desc)}</div>`+
      `<div class="cls-line">Starting deck: ${esc(c.deck.join(", "))}</div>`;
    b.onclick = ()=> send({type:"new_run", cls:c.key, daily:dailyMode});
    row.appendChild(b);
  });
  st.appendChild(row);
  const toggle = ctaButton(
    dailyMode ? "Daily climb: <b>on</b> — everyone gets the same Spire today"
              : "Daily climb: off — each run is freshly seeded",
    ()=>{ dailyMode = !dailyMode; render(); });
  toggle.setAttribute("aria-pressed", String(dailyMode));
  st.appendChild(toggle);
}

function renderEnd(st, won){
  st.appendChild(el("h1","title big", won ? "You have ascended the Spire"
                                          : "You died"));
  if(!won) st.appendChild(el("div","sub",
    `Slain by ${esc(S.killer)} on floor ${S.floor} of act ${S.act}.`));
  st.appendChild(el("div","center",
    `${esc(S.player.name)} · Act ${S.act} · ${S.floors_cleared} combats won · `+
    `${S.elites_killed} elites slain · ${S.player.deck_size} cards · ${S.player.gold} gold`));
  const relics = el("div","chips");
  relics.style.cssText = "justify-content:center;margin:18px 0";
  relics.innerHTML = S.player.relics.map(r=>`<span class="chip relic">${esc(r.name)}</span>`).join("");
  st.appendChild(relics);
  // This used to be one button sending new_run with no class, which quietly
  // restarted whatever DEFAULT_CLASS happens to be rather than what you played.
  const again = ctaButton(`Climb again as ${esc(S.player.name)} <kbd>Enter</kbd>`,
                          ()=> send({type:"new_run", cls:S.player.cls}));
  again.style.cssText += ";padding:12px 28px;font-size:16px";
  st.appendChild(again);
  st.appendChild(ctaButton("Choose another class <kbd>C</kbd>", abandon));
  api("/records").then(recs=>{
    if(!recs || !recs.length) return;
    const d = el("div","center ghost");
    d.style.marginTop = "26px";
    d.innerHTML = "<b>Best runs</b><br>" + recs.slice(0,5).map(r =>
      `act ${r.act} · floor ${r.floors} · ${r.won?"<span style='color:var(--leaf)'>ascended</span>"
        :"died to "+esc(r.killer)}`).join("<br>");
    st.appendChild(d);
  });
}

/* ── overlays ───────────────────────────────────────────── */
let overlayReturn = null;              // focus goes back where it came from
let overlayConfirm = null;             // set while the overlay is asking a yes/no

function openOverlay(title, cards, note){
  const b = $("#overlay-body"); b.innerHTML = "";
  b.appendChild(el("h2","title",esc(title)));
  $("#overlay-title").textContent = title;
  if(note) b.appendChild(el("div","sub",esc(note)));
  const row = el("div","row");
  (cards||[]).forEach(c => row.appendChild(cardEl(c,{static:true})));
  b.appendChild(row);
  showOverlay();
}
function showOverlay(){
  hideTip();
  overlayReturn = overlayOpen() ? overlayReturn : document.activeElement;
  $("#overlay").classList.add("on");
  $("#overlay .close").focus();
}
function overlayOpen(){ return $("#overlay").classList.contains("on"); }
function showDeck(){
  openOverlay(`Your deck — ${S.deck.length} cards`, S.deck,
    "Relics: " + S.player.relics.map(r=>r.name).join(", "));
}
function showRelics(){
  const b = $("#overlay-body"); b.innerHTML = "";
  b.appendChild(el("h2","title","Your relics"));
  $("#overlay-title").textContent = "Your relics";
  S.player.relics.forEach(r => b.appendChild(el("div","item",
    `<span class="nm">${esc(r.name)}</span><span class="ds">${esc(r.desc)}</span>`)));
  showOverlay();
}
async function showPile(k, title){
  // Pile contents are fetched on demand rather than riding along with every
  // single state response.
  openOverlay(title, [], "Loading…");
  try{
    const piles = await api("/piles");
    const pile = piles[k] || [];
    openOverlay(`${title} — ${pile.length} cards`, pile,
      k === "draw_pile" ? "Sorted; the real draw order is hidden." : "");
  }catch(e){
    toast(e.status ? e.message : "Could not reach the Spire.");
    closeOverlay();
  }
}
function showHelp(){
  $("#overlay-title").textContent = "How to play";
  $("#overlay-body").innerHTML = `
    <h2 class="title">How to play</h2>
    <div style="max-width:660px;margin:16px auto;line-height:1.8">
      <p>Click a card to play it, or press its number. Cards cost <b>Energy</b> (the orb);
         you get 3 per turn. <kbd>E</kbd> ends the turn — your hand is discarded and the
         enemies act.</p>
      <p><b>Block</b> 🛡 absorbs damage and disappears at the start of your next turn.
         An enemy's intent shows what it will do: ⚔ is the damage you would take,
         already adjusted for your statuses.</p>
      <p>Targeted cards ask you to click an enemy (or press <kbd>a</kbd>–<kbd>d</kbd>).
         Potions are the chips in the top-right: click them or press
         <kbd>q</kbd> <kbd>w</kbd> <kbd>r</kbd>.</p>
      <p>The small chips on you and on each enemy are <b>statuses</b>. Hover one —
         or tap it on a phone — and it will tell you exactly what it does. Relics
         and potions in the top bar work the same way.</p>
      <p class="ghost">Keys: <kbd>1</kbd>–<kbd>9</kbd> cards or options ·
        <kbd>E</kbd> end turn · <kbd>a</kbd>–<kbd>d</kbd> target / path ·
        <kbd>i</kbd> deck · <kbd>Esc</kbd> cancel · <kbd>Enter</kbd> continue</p>
    </div>`;
  showOverlay();
}
function closeOverlay(){
  $("#overlay").classList.remove("on");
  if(overlayReturn && overlayReturn.focus) overlayReturn.focus();
  overlayReturn = null;
  overlayConfirm = null;
}

/* ── floating damage numbers ────────────────────────────── */
function floaters(){
  // only the render that follows a server response animates; selecting or
  // cancelling a card re-renders against the same prev/S pair and must not replay
  if(!pendingFx) return;
  pendingFx = false;
  if(!prev || !prev.combat || !S.combat) return;
  const stage = $("#stage");
  S.combat.enemies.forEach((e,i) => {
    const before = prev.combat.enemies[i]; if(!before) return;
    const d = Math.max(0, before.hp) - Math.max(0, e.hp);
    const node = document.querySelector(`.foe[data-foe="${i}"]`);
    if(d > 0 && node) pop(node, `-${d}`, "dmg");
  });
  const dp = prev.player.hp - S.player.hp, bar = $("#playerbar");
  if(bar && dp > 0){ pop(bar, `-${dp}`, "dmg"); bar.classList.add("shake");
    setTimeout(()=>bar.classList.remove("shake"), 320); }
  if(bar && dp < 0) pop(bar, `+${-dp}`, "heal");
  const db = S.player.block - prev.player.block;
  if(bar && db > 0) pop(bar, `+${db} 🛡`, "blk");
  function pop(node, text, cls){
    const r = node.getBoundingClientRect(), s = stage.getBoundingClientRect();
    const f = el("div","float "+cls, text);
    f.style.left = (r.left - s.left + r.width/2 - 12) + "px";
    f.style.top  = (r.top  - s.top  + 10) + "px";
    stage.appendChild(f);
    setTimeout(()=>f.remove(), 1000);
  }
}

/* ── screens ─────────────────────────────────────────────
   One table per screen: how to draw it, what the hint bar says, and which keys
   it answers to. These used to be three separate if-chains that had to be kept
   in sync by hand. */
const SCREENS = {
  select: {
    render: renderSelect,
    hint: "1–9 pick a class",
    keys: (k, num) => { const cs = S.classes || [];
      if(num >= 0 && num < cs.length) send({type:"new_run", cls:cs[num].key}); },
  },
  map: {
    render: renderMap,
    hint: "click a node or press its letter · i deck · ? help",
    keys: k => { const i = LETTERS.indexOf(k);
      if(i >= 0 && S.map.reachable.includes(i)) send({type:"map", idx:i}); },
  },
  combat: {
    render: renderCombat,
    hint: () => `1–9 play · e end turn · a–d target · ` +
                `${POTION_KEYS.slice(0, S.player.max_potions).split("").join(" ")} potions · ` +
                `esc cancel · i deck`,
    keys: combatKeys,
  },
  reward: {
    render: renderReward,
    hint: () => {
      const r = S.reward;
      return [!r.card_taken ? "1–3 take a card" : null,
              r.relic && !r.relic_taken ? "r relic" : null,
              r.potion && !r.potion_taken && !r.potions_full ? "p potion" : null,
              "enter continue"].filter(Boolean).join(" · ");
    },
    keys: (k, num) => {
      const r = S.reward;
      if(k === "enter" || k === "s"){ send({type:"reward_done"}); return; }
      if(k === "r" && r.relic && !r.relic_taken){
        send({type:"reward", what:"relic"}); return; }
      if(k === "p" && r.potion && !r.potion_taken && !r.potions_full){
        send({type:"reward", what:"potion"}); return; }
      if(!r.card_taken && num >= 0 && num < r.cards.length)
        send({type:"reward", what:"card", idx:num});
    },
  },
  choose: {
    render: renderChoose,
    hint: "1–9 pick",
    keys: (k, num) => {
      if(num >= 0 && num < S.choose.cards.length) send({type:"choose", idx:num});
    },
  },
  rest: {
    render: renderRest,
    hint: "1 rest · 2 smith · 3 purge",
    keys: k => { if(k === "1" && S.player.hp < S.player.max_hp) send({type:"rest"});
                 if(k === "2") send({type:"smith"});
                 if(k === "3") send({type:"purge"}); },
  },
  shop: {
    render: renderShop,
    hint: "1–5 cards · r relic · q w e potions · x removal · esc leave",
    keys: (k, num) => {
      if(num >= 0 && num < S.shop.cards.length &&
         S.shop.cards[num].price <= S.player.gold){
        send({type:"shop_buy", what:"card", idx:num});
        return;
      }
      if(SHOP_KEYS[k]) send(SHOP_KEYS[k]);
    },
  },
  event: {
    render: renderEvent,
    hint: "1–3 choose · enter continue",
    keys: (k, num) => {
      if(S.event.result !== null){ if(k === "enter") send({type:"event_done"}); return; }
      if(num >= 0 && num < S.event.options.length) send({type:"event_choose", idx:num});
    },
  },
  treasure: {
    render: renderTreasure,
    hint: "enter continue",
    keys: k => { if(k === "enter") send({type:"treasure_done"}); },
  },
  gameover: {
    render: st => renderEnd(st, false),
    hint: "enter to climb again · c to change class",
    keys: k => { if(k === "enter") send({type:"new_run", cls:S.player.cls});
                 if(k === "c") abandon(); },
  },
  win: {
    render: st => renderEnd(st, true),
    hint: "enter to climb again · c to change class",
    keys: k => { if(k === "enter") send({type:"new_run", cls:S.player.cls});
                 if(k === "c") abandon(); },
  },
};

function combatKeys(k, num, ev){
  if(k === "e" || k === " "){ ev.preventDefault(); if(!sel) send({type:"end_turn"}); return; }
  const potIdx = POTION_KEYS.indexOf(k);
  if(potIdx >= 0 && potIdx < S.player.max_potions){ clickPotion(potIdx); return; }
  if(sel && sel.mode === "target"){
    const fi = LETTERS.indexOf(k);
    if(fi >= 0 && S.combat.enemies[fi] && S.combat.enemies[fi].alive){ clickFoe(fi); return; }
  }
  if(num >= 0 && num < S.combat.hand.length) clickCard(num);
}

/* ── main render ────────────────────────────────────────── */
function render(){
  hideTip();                 // whatever it was anchored to is about to be replaced
  renderTop();
  const st = $("#stage"); st.innerHTML = "";
  const changed = S.screen !== lastScreen;
  st.className = "screen-" + S.screen;
  if(changed){ void st.offsetWidth; st.classList.add("enter"); }  // fade only between screens
  if(S.screen !== "combat") lastTurn = -1;
  lastScreen = S.screen;
  if(S.banner){
    const b = el("div","result", `<b>${esc(S.banner[0])}</b><br>${esc(S.banner[1])}`);
    st.appendChild(b);
    announce(`${S.banner[0]}. ${S.banner[1]}`);
  }
  const screen = SCREENS[S.screen];
  if(screen) screen.render(st);
  else st.appendChild(el("div","center","…"));
  hint();
  floaters();
  announceCombat();
}

function hint(){
  const screen = SCREENS[S.screen];
  const h = screen ? (typeof screen.hint === "function" ? screen.hint() : screen.hint) : "";
  $("#hint").textContent = h;
}

/* ── screen-reader announcements ─────────────────────────
   The combat log and the floating damage numbers are purely visual; without
   this the game is silent to assistive tech. */
let lastAnnounced = "";
function announce(text){
  if(!text || text === lastAnnounced) return;
  lastAnnounced = text;
  $("#announcer").textContent = text;
}
function announceCombat(){
  if(!S.combat) return;
  const tail = S.combat.log.slice(-2).join(". ");
  const p = S.player;
  announce(`${tail}. You have ${p.hp} of ${p.max_hp} hit points` +
           (p.block ? `, ${p.block} block` : "") + ".");
}

/* ── keyboard ───────────────────────────────────────────── */
document.addEventListener("keydown", ev => {
  if(ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const k = ev.key.toLowerCase();
  if(overlayOpen()){
    // "1" confirms; Enter deliberately does not, so a stray keypress on the
    // continue-flavoured key cannot throw a run away.
    if(overlayConfirm && k === "1"){
      const go = overlayConfirm;
      closeOverlay();
      go();
      return;
    }
    if(k === "escape" || k === "i" || k === "?") closeOverlay();
    return;
  }
  if(offline) return;
  if(k === "i"){ if(S && S.screen !== "select") showDeck(); return; }
  if(k === "?" || (k === "/" && ev.shiftKey)){ showHelp(); return; }
  if(!S) return;
  if(k === "escape"){
    if(sel){ sel = null; render(); }
    else if(S.screen === "shop") send({type:"shop_leave"});
    else if(S.screen === "choose" && S.choose.kind === "remove") send({type:"choose", idx:null});
    return;
  }
  const screen = SCREENS[S.screen];
  if(screen && screen.keys) screen.keys(k, "1234567890".indexOf(ev.key), ev);
});

/* ── delegated clicks ────────────────────────────────────
   Handlers used to be interpolated into innerHTML strings, which forced every
   render function into global scope and ruled out a CSP. */
document.addEventListener("click", ev => {
  const target = ev.target.closest("[data-act]");
  if(!target) return;
  const i = Number(target.dataset.i);
  switch(target.dataset.act){
    case "deck":          if(S && S.screen !== "select") showDeck(); break;
    case "help":          showHelp(); break;
    case "close-overlay": closeOverlay(); break;
    case "quit":          confirmQuit(); break;
    case "relic":         showRelics(); break;
    case "potion":        clickPotion(i); break;
    case "pile":          showPile(target.dataset.pile,
                                   {draw_pile:"Draw pile", discard_pile:"Discard pile",
                                    exhaust_pile:"Exhausted"}[target.dataset.pile]); break;
    case "reconnect":     reconnect(); break;
  }
});

/* ── tooltip wiring ──────────────────────────────────────
   Delegated, so anything rendered with data-tip picks it up without knowing
   the tooltip exists. */
document.addEventListener("mouseover", ev => {
  const node = ev.target.closest("[data-tip]");
  if(node === tipFor) return;
  hideTip();
  if(node) showTip(node);
});
document.addEventListener("mouseout", ev => {
  if(tipFor && !tipFor.contains(ev.relatedTarget)) hideTip();
});
document.addEventListener("focusin", ev => {
  const node = ev.target.closest("[data-tip]");
  hideTip();
  if(node) showTip(node);
});
document.addEventListener("focusout", hideTip);
// Touch has no hover: tap a chip to pin its tooltip, tap elsewhere to drop it.
// Relics and potions are left out — they already open the overlay on tap. A tap
// on a chip already focused it, so re-showing here would only make it flicker.
// Capture phase, because an enemy's chips sit inside the enemy: tapping one to
// read it must not also pick that enemy as a target.
document.addEventListener("click", ev => {
  const node = ev.target.closest("[data-tip]:not([data-act])");
  if(!node){ hideTip(); return; }
  if(node !== tipFor) showTip(node);
  ev.stopPropagation();
}, true);
window.addEventListener("scroll", hideTip, true);
window.addEventListener("resize", hideTip);

async function reconnect(){
  setOffline(false);
  await boot();
}
// A machine coming back from sleep or a restarted server should recover itself.
window.addEventListener("online", () => { if(offline) reconnect(); });

boot();
