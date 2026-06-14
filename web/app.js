"use strict";
/* ArtDeck frontend. Plain vanilla, no build step. Calls the local JSON API. */

const SVG = (b)=>`<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${b}</svg>`;
const ICONS = {
  cover:  SVG(`<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="1.6"/><path d="m21 15-4-4-9 9"/>`),
  banner: SVG(`<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="8" cy="10" r="1.6"/><path d="m22 16-5-5L9 19"/>`),
  hero:   SVG(`<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20h14V9.5"/><path d="M9.5 20v-5h5v5"/>`),
  logo:   SVG(`<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>`),
  icon:   SVG(`<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.2" fill="currentColor"/>`),
};
const GAME_PH = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="3"/><path d="M7 12h3M8.5 10.5v3"/><circle cx="15.5" cy="11" r="1"/><circle cx="17.5" cy="13" r="1"/></svg>`;
const PEEK = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`;

const TYPES = [
  {id:"cover",  ar:"2/3",     w:170, fit:"cover"},
  {id:"banner", ar:"460/215", w:260, fit:"cover"},
  {id:"hero",   ar:"96/31",   w:340, fit:"cover"},
  {id:"logo",   ar:"3/2",     w:210, fit:"contain"},
  {id:"icon",   ar:"1/1",     w:108, fit:"contain"},
];
const TYPE = Object.fromEntries(TYPES.map(t=>[t.id,t]));
const STATUS_ORDER = ["cover","banner","hero","logo","icon"];

const state = {
  accounts:[], account:null, source:"shortcut",
  games:[], selected:null, gameId:null, matchName:null,
  type:"cover", animated:false, candidates:[], selectedArt:null,
  reqToken:0, keyOk:false, key:"",
  matchState:"", matchError:"", variants:null,
};

const $  = s=>document.querySelector(s);
const el = (tag,cls,html)=>{const e=document.createElement(tag); if(cls)e.className=cls; if(html!=null)e.innerHTML=html; return e;};
async function jget(u){const r=await fetch(u); if(!r.ok) throw new Error((await r.json().catch(()=>({error:r.status}))).error||r.status); return r.json();}
async function jpost(u,b){const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}); return r.json();}
const enc = encodeURIComponent;
const IS_VIDEO = u => /\.(webm|mp4)(\?|$)/i.test(u || "");

/* ---------------- i18n static ---------------- */
function applyStatic(){
  document.querySelectorAll("[data-i18n]").forEach(e=>{ e.textContent = t(e.dataset.i18n); });
  $("#filter").placeholder = t("filter_games");
  $("#search").placeholder = t("search_sgdb");
  $("#set-lang-cur").textContent = t("lang_name");
  $("#btn-autofill").dataset.tip = t("tip_autofill");
  $("#btn-clean").dataset.tip = t("tip_clean");
  document.documentElement.lang = LANG;
}

/* ---------------- init ---------------- */
window.addEventListener("DOMContentLoaded", init);

async function init(){
  applyStatic();
  buildTabs();
  $("#filter").addEventListener("input", filterGames);
  $("#search").addEventListener("keydown", e=>{ if(e.key==="Enter") doSearch(); });
  document.addEventListener("click", e=>{ const b=$("#candidates"); if(b && !b.contains(e.target)) candOpen(false); });
  document.addEventListener("keydown", e=>{ if(e.key==="Escape") candOpen(false); });
  $("#btn-autofill").addEventListener("click", autofill);
  $("#btn-clean").addEventListener("click", openClean);
  $("#btn-refresh").addEventListener("click", refreshGames);
  $("#btn-refresh").title = t("refresh");
  $("#btn-key").addEventListener("click", editKey);
  $("#btn-settings").addEventListener("click", e=>{ e.stopPropagation(); toggleSettings(); });
  $("#set-key").addEventListener("click", ()=>{ closeSettings(); editKey(); });
  $("#set-lang").addEventListener("click", ()=>{ closeSettings(); openLangPicker(); });
  document.addEventListener("click", e=>{ if(!$("#settings").contains(e.target)) closeSettings(); });
  $("#anim").addEventListener("change", e=>{ state.animated=e.target.checked; if(state.gameId) loadArts(); });

  // source tabs (Non-Steam / Installed)
  document.querySelectorAll(".src-tab").forEach(tab=>{
    tab.addEventListener("click", ()=>{
      if(tab.classList.contains("active")) return;
      document.querySelectorAll(".src-tab").forEach(x=>x.classList.remove("active"));
      tab.classList.add("active");
      state.source = tab.dataset.src;
      $("#src-tabs").dataset.src = state.source;
      $("#filter").value="";   // same start for both tabs: reset the filter
      // let the tab slider paint its transition before the heavy list re-render
      requestAnimationFrame(()=>requestAnimationFrame(()=>loadGames()));
    });
  });

  // account dropdown
  $("#acct-btn").addEventListener("click", toggleAcctMenu);
  document.addEventListener("click", e=>{ if(!$("#acct").contains(e.target)) closeAcctMenu(); });
  // lightbox
  $("#light-x").addEventListener("click", closeLight);
  $("#light").addEventListener("click", e=>{ if(e.target.id==="light") closeLight(); });
  document.addEventListener("keydown", e=>{ if(e.key==="Escape"){ closeLight(); closeModal(); } });

  try{
    const st = await jget("/api/state");
    state.key = st.key || "";
    setKey(st.key_ok);
    if(!st.steam_path){ toast(t("steam_not_found"),"bad"); return; }
    state.accounts = st.accounts || [];
    $("#acct").classList.toggle("solo", state.accounts.length<=1);  // single account -> no dropdown
    renderAcctMenu();
    if(state.accounts.length){ selectAccount(state.accounts[0].uid); }
    if(!st.key_ok) toast(t("no_key_hint"),"bad");
  }catch(e){ toast(t("error")+e.message,"bad"); }
}

const LANGS=[
  {code:"ru", name:"Русский", sub:"Russian"},
  {code:"en", name:"English", sub:"English"},
];
function applyLang(code){
  if(code===LANG) return;
  setLang(code);
  applyStatic();
  buildTabs();
  setKey(state.keyOk);
  renderAcctMenu();
  if(state.selected) renderMatchSub();
  else $("#match-name").textContent = t("pick_game");
}
function openLangPicker(){
  modal(t("lang_title"), `<div class="lang-list" id="lang-list"></div>`,
    [{x:t("cancel"),cls:"ghost",fn:closeModal}]);
  const box=$("#lang-list");
  LANGS.forEach(l=>{
    const row=el("button","lang-row"+(l.code===LANG?" sel":"")); row.type="button";
    row.innerHTML=`<span class="lang-code">${l.code.toUpperCase()}</span>`
      +`<span class="lang-meta"><b>${escapeHtml(l.name)}</b><small>${escapeHtml(l.sub)}</small></span>`
      +(l.code===LANG?`<span class="lang-check">✓</span>`:"");
    row.addEventListener("click", ()=>{ closeModal(); applyLang(l.code); });
    box.appendChild(row);
  });
}

/* ---------------- accounts ---------------- */
function acctInitial(a){ return (a.name||a.uid||"?").trim().charAt(0).toUpperCase(); }
function avatarStyle(a){ return a.has_avatar ? `background-image:url(/api/avatar?account=${enc(a.uid)})` : ""; }

function renderAcctMenu(){
  const menu=$("#acct-menu"); menu.innerHTML="";
  state.accounts.forEach(a=>{
    const row=el("div","acct-row"+(a.uid===state.account?" sel":""));
    const av=el("span","acct-av"); av.style.cssText=avatarStyle(a); if(!a.has_avatar) av.textContent=acctInitial(a);
    row.appendChild(av);
    row.appendChild(el("div",null,`<b>${escapeHtml(a.name||a.uid)}</b><small>${escapeHtml(a.uid)}</small>`));
    row.addEventListener("click", ()=>{ selectAccount(a.uid); closeAcctMenu(); });
    menu.appendChild(row);
  });
}
function selectAccount(uid){
  state.account = uid;
  const a = state.accounts.find(x=>x.uid===uid) || {uid};
  const av=$("#acct-av"); av.style.cssText=avatarStyle(a); av.textContent = a.has_avatar ? "" : acctInitial(a);
  $("#acct-name").textContent = a.name || uid;
  renderAcctMenu();
  loadGames();
}
function toggleAcctMenu(){ if($("#acct").classList.contains("solo")) return; const m=$("#acct-menu"); const open=m.classList.toggle("hidden"); $("#acct-btn").setAttribute("aria-expanded", String(!open)); }
function closeAcctMenu(){ $("#acct-menu").classList.add("hidden"); $("#acct-btn").setAttribute("aria-expanded","false"); }

/* ---------------- game list ---------------- */
async function refreshGames(){
  const b=$("#btn-refresh"); if(b) b.classList.add("spin");
  await loadGames(2000);                    // hold the skeleton at least 2s — otherwise the scan flickers
  if(b) b.classList.remove("spin");
  toast(t("refreshed"),"ok");
}

function renderGameSkeletons(){
  const box=$("#games"); box.innerHTML="";
  const banner=el("div","scan-banner");
  banner.innerHTML=`<span class="scan-spin"></span><span>${escapeHtml(t("scanning"))}</span>`;
  box.appendChild(banner);
  for(let i=0;i<8;i++){
    const row=el("div","game gskel"); row.style.animationDelay=(i*45)+"ms";
    row.innerHTML=`<span class="sk sk-ic"></span><span class="sk sk-nm"></span><span class="sk sk-cov"></span>`;
    box.appendChild(row);
  }
}

async function loadGames(minMs=0){
  if(!state.account) return;
  state.selected=null; state.gameId=null; state.matchName=null;
  $("#match-name").textContent=t("pick_game"); $("#match-sub").textContent="";
  $("#grid").innerHTML=""; $("#candidates").classList.add("hidden");
  // refresh — show the skeleton immediately; a quick switch only if loading takes >160ms
  // (otherwise the skeleton flashes for an instant when local files read instantly).
  let shown=false;
  const showSkel=()=>{ shown=true; renderGameSkeletons(); };
  const skelTimer = minMs>0 ? (showSkel(),null) : setTimeout(showSkel,160);
  const t0=Date.now();
  try{
    const d = await jget(`/api/games?account=${enc(state.account)}&source=${state.source}`);
    state.games = d.games||[];
    if(skelTimer) clearTimeout(skelTimer);
    const wait=minMs-(Date.now()-t0);         // for refresh, hold the skeleton no shorter than minMs (2s)
    if(wait>0){ if(!shown) showSkel(); await new Promise(r=>setTimeout(r,wait)); }
    renderGames();
    const first=document.querySelector("#games .game");
    if(first) first.click();
  }catch(e){ if(skelTimer) clearTimeout(skelTimer); $("#games").innerHTML=""; toast(t("games_err")+e.message,"bad"); }
}

// Render the coverage meter for one game (reused for in-place row updates).
function renderCov(cov, g){
  cov.innerHTML=""; let have=0;
  const has=tp=>!!((g.status && g.status[tp]) || (g.official && g.official[tp]));
  STATUS_ORDER.forEach(tp=>{
    const custom=!!(g.status && g.status[tp]);
    const present=has(tp); if(present) have++;
    // on = our custom art (mint); off = Steam's own art (dim)
    const seg=el("span","seg"+(tp==="cover"?" cover":"")+(custom?" on":present?" off":""));
    seg.title=t("t_"+tp)+(present?" ✓":" ✗");
    cov.appendChild(seg);
  });
  const missing=STATUS_ORDER.filter(tp=>!has(tp)).map(tp=>t("t_"+tp));
  cov.classList.toggle("need", !has("cover"));
  cov.title = have===5 ? t("cov_full")
    : t("cov_count",have)+" · "+t("cov_missing")+": "+missing.join(", ");
}

// Build every row once; filtering and per-row updates reuse these nodes so a
// keystroke or a single apply doesn't rebuild the list and re-fetch all icons.
function renderGames(){
  const box=$("#games"); box.innerHTML="";
  state.games.forEach(g=>{
    const row=el("div","game"); g._row=row;
    if(state.selected && state.selected.appid===g.appid) row.classList.add("active");
    const ic=el("span","g-ic",GAME_PH);
    const img=el("img"); img.alt="";
    img.addEventListener("load",()=>{ ic.innerHTML=""; ic.appendChild(img); });
    img.src=`/api/gameicon?account=${enc(state.account)}&appid=${g.appid}`;
    row.appendChild(ic);
    row.appendChild(el("span","g-nm",escapeHtml(g.name)));
    const cov=el("div","cov"); g._cov=cov; renderCov(cov,g);
    row.appendChild(cov);
    row.addEventListener("click", ()=>selectGame(g,row));
    box.appendChild(row);
  });
  filterGames();
}

// Show/hide existing rows by the filter text — no rebuild, no icon re-fetch.
function filterGames(){
  const flt=$("#filter").value.trim().toLowerCase();
  state.games.forEach(g=>{
    if(g._row) g._row.classList.toggle("hidden", !!flt && !g.name.toLowerCase().includes(flt));
  });
}

// Refresh just one game's coverage meter after apply/revert.
function updateGameRow(g){
  if(g && g._cov) renderCov(g._cov, g);
}

async function selectGame(g,row){
  state.selected=g; state.gameId=null; state.matchName=null; state.variants=null;
  document.querySelectorAll(".game.active").forEach(r=>r.classList.remove("active"));
  if(row) row.classList.add("active");
  ambientFromImage(`/api/gameicon?account=${enc(state.account)}&appid=${g.appid}`);
  $("#match-name").textContent=g.name;
  $("#candidates").classList.add("hidden");
  $("#empty").classList.add("hidden");
  if(!state.keyOk){ state.matchState="nokey"; renderMatchSub(); showNeedKey(); return; }
  state.matchState="searching"; renderMatchSub();
  renderSkeletons();
  try{
    const d=await jget("/api/search?q="+enc(g.name));
    state.candidates=d.results||[];
    fillCandidates();
    if(state.candidates.length){ const m=state.candidates[0]; setGame(m.id,m.name); }
    else { state.matchState="notfound"; renderMatchSub(); }
  }catch(e){ state.matchState="error"; state.matchError=e.message; renderMatchSub(); }
}

/* match-bar subline: useful status chips from the game's own data (cover status
   + coverage) — filled instantly, without waiting on SteamGridDB; plus the
   search state / variant count and a compact GridDB match. */
function mchip(cls, text, title){
  return `<span class="mbadge${cls?" "+cls:""}"${title?` title="${escapeHtml(title)}"`:""}>${escapeHtml(text)}</span>`;
}
function renderMatchSub(){
  const g=state.selected, sub=$("#match-sub");
  if(!g){ sub.textContent=""; return; }
  const has=ty=>!!((g.status&&g.status[ty])||(g.official&&g.official[ty]));
  // 1) cover status — the headline fact (custom / Steam / none)
  let html;
  if(g.status&&g.status.cover) html=mchip("ms ok", t("ms_cover_custom"));
  else if(has("cover")) html=mchip("ms", t("ms_cover_steam"));
  else html=mchip("ms warn", t("ms_cover_none"));
  // 2) coverage N/5
  const have=STATUS_ORDER.filter(has).length;
  html+=mchip(have===5?"ok":"", t("cov_count", have));
  // 3) SteamGridDB state / variant count for the active type
  if(state.matchState==="nokey")        html+=mchip("warn", t("need_key_sub"));
  else if(state.matchState==="searching") html+=mchip("", "SteamGridDB · "+t("ms_searching"));
  else if(state.matchState==="notfound")  html+=mchip("warn", t("not_found_manual"));
  else if(state.matchState==="error")     html+=mchip("warn", t("search_error")+(state.matchError||""));
  else if(state.matchState==="matched"){
    html+=(state.variants==null) ? mchip("", "…") : mchip("", t("ms_variants", state.variants));
    html+=mchip("name", "SteamGridDB · "+state.matchName, state.matchName+" · id "+state.gameId);
  }
  sub.innerHTML=html;
}
function setGame(id,name){
  state.gameId=id; state.matchName=name; state.matchState="matched"; state.variants=null;
  renderMatchSub(); updateCandLabel(); loadArts();
}

/* ---------------- manual search ---------------- */
async function doSearch(){
  const q=$("#search").value.trim() || (state.selected?state.selected.name:"");
  if(!q) return;
  try{
    const d=await jget("/api/search?q="+enc(q));
    state.candidates=d.results||[];
    fillCandidates();
    if(state.candidates.length) toast(t("found_n",state.candidates.length));
    else toast(t("nothing_found"),"bad");
  }catch(e){ toast(t("error")+e.message,"bad"); }
}
const CHEV='<svg class="cand-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';
function fillCandidates(){
  const box=$("#candidates"); box.innerHTML="";
  if(!state.candidates.length){ box.classList.add("hidden"); box.classList.remove("open"); return; }
  const trig=el("button","cand-trigger"); trig.type="button"; trig.title=t("found_n",state.candidates.length);
  trig.innerHTML=`<span class="cand-count">${state.candidates.length}</span>${CHEV}`;
  trig.addEventListener("click", e=>{ e.stopPropagation(); candOpen(!box.classList.contains("open")); });
  const menu=el("div","cand-menu");
  state.candidates.forEach(g=>{
    const o=el("button","cand-opt"); o.type="button";
    o.innerHTML=`<span class="cand-opt-name">${escapeHtml(g.name)}</span><span class="cand-opt-id">id ${escapeHtml(String(g.id))}</span>`;
    o.addEventListener("click", ()=>{ setGame(g.id,g.name); candOpen(false); });
    menu.appendChild(o);
  });
  box.appendChild(trig); box.appendChild(menu);
  box.classList.remove("hidden"); box.classList.remove("open");
  updateCandLabel();
}
function updateCandLabel(){
  const box=$("#candidates"); if(!box || box.classList.contains("hidden")) return;
  box.querySelectorAll(".cand-opt").forEach((o,i)=>{
    const g=state.candidates[i];
    o.classList.toggle("sel", !!g && String(g.id)===String(state.gameId));
  });
}
function candOpen(open){
  const box=$("#candidates"); if(!box || box.classList.contains("hidden")) return;
  box.classList.toggle("open", open);
  if(open){ const s=box.querySelector(".cand-opt.sel"); if(s) s.scrollIntoView({block:"nearest"}); }
}

/* ---------------- type tabs ---------------- */
function buildTabs(){
  const box=$("#tabs"); box.innerHTML="";
  TYPES.forEach(tp=>{
    const tab=el("div","tab"+(tp.id===state.type?" active":""),"<span>"+t("t_"+tp.id)+"</span>");
    tab.addEventListener("click", ()=>{
      state.type=tp.id;
      document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
      tab.classList.add("active");
      if(state.gameId) loadArts();
    });
    box.appendChild(tab);
  });
  $("#anim-wrap").style.display = state.type==="icon" ? "none" : "";
}

/* ---------------- art ---------------- */
function cardShell(cfg,i){
  const c=el("div","card"); c.style.animationDelay=(i*22)+"ms";
  const w=el("div","imgwrap"); w.style.setProperty("--ar",cfg.ar);
  c.appendChild(w); return {c,w};
}
function skeleton(cfg,i){ const{c}=cardShell(cfg,i); c.classList.add("skeleton"); return c; }

function renderSkeletons(){
  const cfg=TYPE[state.type], grid=$("#grid");
  grid.style.setProperty("--card-w",cfg.w+"px");
  grid.innerHTML="";
  if(state.selected) grid.appendChild(currentCard(cfg));
  for(let i=0;i<10;i++) grid.appendChild(skeleton(cfg,i));
  grid.dataset.skel=state.type+"|"+state.animated;
}

async function loadArts(){
  if(!state.gameId) return;
  const tp=state.type, cfg=TYPE[tp], token=++state.reqToken, grid=$("#grid");
  const sig=tp+"|"+state.animated;
  if(grid.dataset.skel!==sig || !grid.querySelector(".skeleton")) renderSkeletons();
  $("#anim-wrap").style.display = tp==="icon" ? "none" : "";
  state.variants=null; renderMatchSub();   // "..." in the variants chip while loading
  try{
    const d=await jget(`/api/arts?game_id=${state.gameId}&type=${tp}&animated=${state.animated?1:0}`);
    if(token!==state.reqToken) return;
    grid.querySelectorAll(".skeleton").forEach(s=>s.remove());
    const arts=d.arts||[];
    state.variants=arts.length; renderMatchSub();
    if(!arts.length){ grid.appendChild(el("div","empty",t("no_variants"))); return; }
    arts.forEach((a,i)=>grid.appendChild(artCard(a,cfg,i)));
  }catch(e){
    if(token!==state.reqToken) return;
    grid.querySelectorAll(".skeleton").forEach(s=>s.remove());
    toast(t("load_variants_err")+e.message,"bad");
  }
}

function currentCard(cfg){
  const{c,w}=cardShell(cfg,0); c.classList.add("current");
  c.appendChild(el("span","badge",t("current")));
  const src=`/img?account=${enc(state.account)}&appid=${state.selected.appid}&type=${state.type}&t=${Date.now()}`;
  const img=el("img"); img.style.objectFit=cfg.fit;
  let hasArt=true;
  img.onerror=()=>{ hasArt=false; w.innerHTML=""; w.appendChild(el("div","none",t("none_short"))); c.classList.add("nopic"); };
  img.src=src; w.appendChild(img);
  c.appendChild(el("div","cur-cap",t("current_cap")));
  // revert-to-Steam-original button — only if we have our own custom art for this type
  const hasCustom = !!(state.selected && state.selected.status && state.selected.status[state.type]);
  if(hasCustom){
    const rv=el("button","revert",
      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg><span>${escapeHtml(t("revert"))}</span>`);
    rv.title=t("revert_hint");
    rv.addEventListener("click",ev=>{ ev.stopPropagation(); revertArt(); });
    c.appendChild(rv);
  }
  c.title=t("current_hint");
  c.addEventListener("click",()=>{ if(hasArt) openLight({url:src,thumb:src}); });
  return c;
}

async function revertArt(){
  const g=state.selected; if(!g) return;
  try{
    const r=await jpost("/api/revert",{account:state.account,appid:g.appid,type:state.type});
    if(r.ok){
      toast((r.removed&&r.removed.length)?t("reverted"):t("nothing_to_revert"),"ok");
      g.status[state.type]=false; updateGameRow(g);
      loadArts();   // re-renders the "Current" card: Steam's original or "none"
    }else toast(t("error")+(r.error||"?"),"bad");
  }catch(e){ toast(t("error")+e.message,"bad"); }
}

function artCard(a,cfg,i){
  const{c,w}=cardShell(cfg,i); c.classList.add("loading");
  if(a.animated) c.appendChild(el("span","badge anim",t("animated_badge")));
  const done=()=>c.classList.remove("loading");
  const fail=()=>{ c.classList.remove("loading"); w.innerHTML=""; w.appendChild(el("div","none","⚠")); };
  if(IS_VIDEO(a.thumb)){
    // light .webm animation preview (tens of KB); we don't load the full url in the grid
    const v=el("video"); v.muted=true; v.loop=true; v.autoplay=true;
    v.setAttribute("playsinline",""); v.style.objectFit=cfg.fit;
    v.addEventListener("loadeddata",done); v.addEventListener("error",fail);
    v.src=a.thumb; w.appendChild(v);
  } else {
    const img=el("img"); img.style.objectFit=cfg.fit;
    img.addEventListener("load",done);
    img.addEventListener("error",()=>{
      if(!img.dataset.fb && a.url && a.url!==a.thumb){ img.dataset.fb="1"; img.src=a.url; }
      else fail();
    });
    img.src=a.thumb;
    if(img.complete && img.naturalWidth>0) done();
    w.appendChild(img);
  }
  c.appendChild(meta(a));
  const acts=el("div","card-actions");
  const peek=el("button","peek",PEEK); peek.title=t("preview");
  peek.addEventListener("click",ev=>{ ev.stopPropagation(); openLight(a); });
  const ap=el("button","apply",t("apply"));
  ap.addEventListener("click",ev=>{ ev.stopPropagation(); applyArt(a,c); });
  acts.appendChild(peek); acts.appendChild(ap);
  c.appendChild(acts);
  c.addEventListener("click",()=>openLight(a));
  return c;
}
function meta(a){
  const m=el("div","meta");
  m.appendChild(el("span",null,(a.width&&a.height)?`${a.width}×${a.height}`:""));
  if(a.style) m.appendChild(el("span",null,a.style));
  return m;
}

/* ---------------- preview lightbox ---------------- */
function openLight(a){
  state.selectedArt=a;
  const stage=$("#light-stage"); stage.innerHTML="";
  // reserve the media frame at the art's final aspect ratio up front — the skeleton (shimmer)
  // takes the same size as the future cover, with no jump when it loads.
  let w=a.width, h=a.height;
  if(!(w&&h)){ const p=((TYPE[state.type]&&TYPE[state.type].ar)||"2/3").split("/").map(Number); w=p[0]; h=p[1]; }
  const frame=el("div","light-frame loading");
  frame.style.setProperty("--ar", `${w}/${h}`);
  frame.style.setProperty("--arn", String(w/h));
  const ready=()=>frame.classList.remove("loading");
  if(IS_VIDEO(a.thumb)){
    // show animation via the light .webm preview; the heavy url is fetched only on apply
    const v=el("video"); v.muted=true; v.loop=true; v.autoplay=true; v.controls=false;
    v.setAttribute("playsinline","");
    v.addEventListener("loadeddata",ready); v.addEventListener("error",ready);
    v.src=a.thumb; frame.appendChild(v);
  } else {
    const img=el("img");
    img.addEventListener("load",ready); img.addEventListener("error",ready);
    img.src=a.url||a.thumb;
    if(img.complete && img.naturalWidth>0) ready();
    frame.appendChild(img);
  }
  stage.appendChild(frame);
  const dims=(a.width&&a.height)?`${a.width}×${a.height}`:"";
  $("#light-meta").innerHTML = dims + (a.style?` · <b>${escapeHtml(a.style)}</b>`:"") + (a.animated?` · ${t("animated_badge")}`:"");
  const ap=$("#light-apply"); ap.textContent=t("apply"); ap.onclick=()=>{ applyArt(a,null); closeLight(); };
  $("#light").classList.remove("hidden");
}
function closeLight(){ $("#light").classList.add("hidden"); $("#light-stage").innerHTML=""; }

/* ---------------- applying ---------------- */
async function applyArt(a,card){
  // only one variant is marked applied: clear the highlight from the rest
  document.querySelectorAll("#grid .card.sel").forEach(c=>c.classList.remove("sel"));
  if(card) card.classList.add("sel");
  try{
    const r=await jpost("/api/apply",{account:state.account,appid:state.selected.appid,type:state.type,url:a.url});
    if(r.ok){
      if(r.warn) toast(t("warn_"+r.warn),"bad");
      else toast(t("applied",r.dest),"ok");
      document.querySelectorAll(".card.current img").forEach(img=>{
        img.src=`/img?account=${enc(state.account)}&appid=${state.selected.appid}&type=${state.type}&t=${Date.now()}`;
      });
      const g=state.games.find(x=>x.appid===state.selected.appid);
      if(g){ g.status[state.type]=true; updateGameRow(g); }
    }else{ if(card) card.classList.remove("sel"); toast(t("error")+(r.error||"?"),"bad"); }
  }catch(e){ if(card) card.classList.remove("sel"); toast(t("apply_err")+e.message,"bad"); }
}

/* ---------------- auto-fill ---------------- */
function autofill(){
  modal(t("autofill_title"),
    `<p>${t("autofill_body")}</p>
     <label style="display:flex;gap:9px;align-items:center;margin-top:12px;color:var(--txt)">
       <input type="checkbox" id="m-all" style="width:16px;height:16px;accent-color:var(--coral)"> ${t("autofill_all")}</label>`,
    [{x:t("cancel"),cls:"ghost",fn:closeModal},
     {x:t("run"),cls:"primary",fn:()=>{ const all=$("#m-all").checked; closeModal(); runAutofill(all?"all":state.account); }}]);
}
function runAutofill(scope){
  $("#overlay").classList.remove("hidden");
  $("#ov-game").textContent=t("prepare"); $("#bar-fill").style.width="0%"; $("#ov-count").textContent="";
  const es=new EventSource("/api/autofill?accounts="+enc(scope));
  es.onmessage=ev=>{
    const d=JSON.parse(ev.data);
    if(d.type==="start"){ $("#ov-count").textContent=t("to_process",d.total); }
    else if(d.type==="progress"){
      $("#ov-game").textContent=d.game;
      $("#bar-fill").style.width=Math.round(d.i/Math.max(1,d.total)*100)+"%";
      $("#ov-count").textContent=`${d.i} / ${d.total}`;
    }else if(d.type==="error"){ es.close(); $("#overlay").classList.add("hidden"); toast(d.message,"bad"); }
    else if(d.type==="done"){
      es.close(); $("#overlay").classList.add("hidden");
      toast(t("autofill_done",d.ok,d.skip,d.fail), d.fail?"bad":"ok");
      loadGames();
    }
  };
  es.onerror=()=>{ es.close(); $("#overlay").classList.add("hidden"); toast(t("conn_lost"),"bad"); };
}

/* ---------------- cleanup ---------------- */
async function openClean(){
  let d;
  try{ d=await jget("/api/orphans"); }catch(e){ toast(t("error")+e.message,"bad"); return; }
  const items=d.items||[];
  if(!items.length){ toast(t("no_orphans"),"ok"); return; }
  const body=el("div");
  items.forEach((it,i)=>{
    const row=el("div","orphan");
    const cb=el("input"); cb.type="checkbox"; cb.checked=true; cb.dataset.i=i;
    row.appendChild(cb);
    const info=el("div");
    info.appendChild(el("div","of",escapeHtml(it.file)));
    info.appendChild(el("div","oa",t("account_label")+it.account));
    row.appendChild(info); body.appendChild(row);
  });
  modal(t("clean_title",items.length), body.outerHTML,
    [{x:t("cancel"),cls:"ghost",fn:closeModal},
     {x:t("delete_chosen"),cls:"primary",fn:async()=>{
        const chosen=[...document.querySelectorAll(".orphan input:checked")].map(cb=>items[+cb.dataset.i]);
        closeModal();
        const r=await jpost("/api/clean",{items:chosen});
        toast(t("removed_n",r.removed||0),"ok"); loadGames();
     }}]);
}

/* ---------------- key ---------------- */
function setKey(ok){
  state.keyOk=ok;
  // settings menu (the key status is always present)
  const st=$("#set-key-status"); if(st) st.textContent = ok ? "OK" : t("key_need");
  const sk=$("#set-key"); if(sk) sk.classList.toggle("bad", !ok);
  const dot=$("#set-key-dot"); if(dot){ dot.classList.toggle("ok",ok); dot.classList.toggle("bad",!ok); }
  // explicit CTA button in the bar (old spot) — only when there's no key; otherwise the key lives in the gear menu
  const b=$("#btn-key");
  if(b){ b.classList.toggle("hidden", ok); const lbl=$("#key-label"); if(lbl) lbl.textContent = t("key_need"); }
  // don't also show the gear dot while the explicit button is up
  const gd=$("#gear-dot"); if(gd) gd.classList.toggle("on", false);
}
function toggleSettings(){ const m=$("#settings-menu"); const open=m.classList.toggle("hidden"); $("#btn-settings").setAttribute("aria-expanded", String(!open)); }
function closeSettings(){ const m=$("#settings-menu"); if(m) m.classList.add("hidden"); $("#btn-settings").setAttribute("aria-expanded","false"); }
const SGDB_KEY_URL = "https://www.steamgriddb.com/profile/preferences/api";
function openExternal(url){ fetch("/api/open?url="+enc(url)).catch(()=>{}); }

function showNeedKey(){
  const grid=$("#grid"); grid.dataset.skel=""; grid.innerHTML="";
  const box=el("div","needkey");
  box.appendChild(el("div","needkey-ic","🔑"));
  box.appendChild(el("div","needkey-t",t("need_key_title")));
  box.appendChild(el("div","needkey-s",t("need_key_body")));
  const b=el("button","btn primary",t("key_need"));
  b.addEventListener("click",editKey);
  box.appendChild(b);
  grid.appendChild(box);
}

function editKey(){
  modal(t("key_title"),
    `<div class="key-steps">${t("key_steps")}</div>
     <button type="button" class="btn ghost keyget" id="m-getkey">${escapeHtml(t("key_get"))} ↗</button>
     <input type="text" id="m-key" placeholder="${t("key_placeholder")}" autocomplete="off" value="${escapeHtml(state.key||"")}">`,
    [{x:t("cancel"),cls:"ghost",fn:closeModal},
     {x:t("save"),cls:"primary",fn:async()=>{
        const v=$("#m-key").value.trim(); closeModal();
        const r=await jpost("/api/key",{key:v});
        state.key = r.key || "";
        setKey(r.key_ok); toast(r.key_ok?t("key_saved"):t("key_cleared"), r.key_ok?"ok":"bad");
        if(r.key_ok && state.selected) selectGame(state.selected, document.querySelector(".game.active"));
     }}]);
  const gb=$("#m-getkey"); if(gb) gb.addEventListener("click",()=>openExternal(SGDB_KEY_URL));
  const inp=$("#m-key"); if(inp) setTimeout(()=>{inp.focus(); inp.select();},60);
}

/* ---------------- ui helpers ---------------- */
function toast(msg,kind){
  const e=el("div","toast"+(kind?" "+kind:""),escapeHtml(msg));
  $("#toasts").appendChild(e);
  setTimeout(()=>{ e.classList.add("out"); setTimeout(()=>e.remove(),300); }, 4000);
}
function modal(title,bodyHtml,actions){
  $("#modal-title").textContent=title;
  $("#modal-body").innerHTML=bodyHtml;
  const a=$("#modal-actions"); a.innerHTML="";
  actions.forEach(act=>{ const b=el("button","btn "+(act.cls||"ghost"),act.x); b.addEventListener("click",act.fn); a.appendChild(b); });
  $("#modal").classList.remove("hidden");
}
function closeModal(){ $("#modal").classList.add("hidden"); }
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}

/* ---------------- ambient background from the selected game's icon ---------------- */
function vivid(c){                          // boost a dim color's brightness while keeping its hue
  const mx = Math.max(c[0], c[1], c[2], 1);
  const k = Math.min(225 / mx, 2.6);
  return [Math.min(255, Math.round(c[0]*k)),
          Math.min(255, Math.round(c[1]*k)),
          Math.min(255, Math.round(c[2]*k))];
}
function setAmbient(c1, c2){
  const a = vivid(c1), b = vivid(c2);
  const r = document.documentElement.style;
  r.setProperty("--amb-1", `rgba(${a[0]},${a[1]},${a[2]},.55)`);
  r.setProperty("--amb-2", `rgba(${b[0]},${b[1]},${b[2]},.42)`);
}
function resetAmbient(){
  const r = document.documentElement.style;
  r.removeProperty("--amb-1"); r.removeProperty("--amb-2");  // restore the default coral/mint
}
let _ambToken = 0;
function ambientFromImage(src){
  const token = ++_ambToken;
  const img = new Image();
  img.onload = ()=>{
    if(token !== _ambToken) return;            // a different game was selected — cancel
    try{
      const n = 24, cv = document.createElement("canvas"); cv.width = cv.height = n;
      const ctx = cv.getContext("2d", {willReadFrequently:true});
      ctx.drawImage(img, 0, 0, n, n);
      const d = ctx.getImageData(0, 0, n, n).data;
      let r=0, g=0, b=0, cnt=0, best=null, bestScore=-1;
      for(let i=0;i<d.length;i+=4){
        if(d[i+3] < 128) continue;             // skip transparent pixels
        const R=d[i], G=d[i+1], B=d[i+2];
        r+=R; g+=G; b+=B; cnt++;
        const mx=Math.max(R,G,B), mn=Math.min(R,G,B);
        const score=(mx-mn)*0.75 + mx*0.25;    // the most vivid pixel becomes the accent
        if(score>bestScore){ bestScore=score; best=[R,G,B]; }
      }
      if(!cnt) return;
      const avg=[Math.round(r/cnt), Math.round(g/cnt), Math.round(b/cnt)];
      setAmbient(best||avg, avg);
    }catch(_){ /* canvas tainted/error — leave as is */ }
  };
  img.onerror = ()=>{ if(token===_ambToken) resetAmbient(); };  // no icon — default
  img.src = src;
}
