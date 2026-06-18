"use strict";
/* ArtDeck frontend. Plain vanilla, no build step. Calls the local JSON API. */

const SVG = (b)=>`<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${b}</svg>`;
const ICONS = {
  cover:  SVG(`<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="1.6"/><path d="m21 15-4-4-9 9"/>`),
  banner: SVG(`<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="8" cy="10" r="1.6"/><path d="m22 16-5-5L9 19"/>`),
  hero:   SVG(`<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20h14V9.5"/><path d="M9.5 20v-5h5v5"/>`),
  logo:   SVG(`<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>`),
};
const GAME_PH = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="3"/><path d="M7 12h3M8.5 10.5v3"/><circle cx="15.5" cy="11" r="1"/><circle cx="17.5" cy="13" r="1"/></svg>`;
const PEEK = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`;

const TYPES = [
  {id:"cover",  ar:"2/3",     w:170, fit:"cover"},
  {id:"banner", ar:"460/215", w:260, fit:"cover"},
  {id:"hero",   ar:"96/31",   w:340, fit:"cover"},
  {id:"logo",   ar:"3/2",     w:210, fit:"contain"},
];
const TYPE = Object.fromEntries(TYPES.map(t=>[t.id,t]));

const state = {
  accounts:[], account:null, source:"shortcut",
  games:[], selected:null, gameId:null,
  type:"cover", animated:false, candidates:[], selectedArt:null,
  reqToken:0, searchToken:0, keyOk:false,
  mode:"covers", launchers:[], activeLauncher:null,
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
  // import-add label includes count — update separately
  _updateImportAddLabel();
}

/* ---------------- init ---------------- */
window.addEventListener("DOMContentLoaded", init);

async function init(){
  applyStatic();
  buildTabs();
  $("#filter").addEventListener("input", filterGames);
  let _searchTimer=null;
  $("#search").addEventListener("input", ()=>{
    clearTimeout(_searchTimer);
    const q=$("#search").value.trim();
    if(!q){ state.candidates=[]; candOpen(false); return; }
    if(!state.keyOk){ candOpen(false); return; }
    _searchTimer=setTimeout(doSearch, 260);          // live typeahead — search as you type
  });
  $("#search").addEventListener("focus", ()=>{ if(state.candidates.length){ fillCandidates(); candOpen(true); } });
  $("#search").addEventListener("keydown", e=>{ if(e.key==="Enter"){ clearTimeout(_searchTimer); doSearch(); } });
  document.addEventListener("click", e=>{ if(!e.target.closest(".match-search")) candOpen(false); });
  document.addEventListener("keydown", e=>{ if(e.key==="Escape") candOpen(false); });
  $("#btn-autofill").addEventListener("click", autofill);
  $("#btn-clean").addEventListener("click", openClean);
  $("#btn-refresh").addEventListener("click", refreshGames);
  $("#btn-refresh").title = t("refresh");
  initSidebar();
  // mode switch
  $("#mode-seg").addEventListener("click", e=>{
    const b = e.target.closest(".mode-opt"); if(b) setMode(b.dataset.mode);
  });
  // import add
  $("#import-add").addEventListener("click", doImport);
  // import view toggle (grid / list)
  _initImportViewToggle();
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
  if(state.mode==="import") _updateImportAddLabel();
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
  state.launchers = [];
  state.activeLauncher = null;
  const a = state.accounts.find(x=>x.uid===uid) || {uid};
  const av=$("#acct-av"); av.style.cssText=avatarStyle(a); av.textContent = a.has_avatar ? "" : acctInitial(a);
  $("#acct-name").textContent = a.name || uid;
  renderAcctMenu();
  if(state.mode === "import"){
    loadLaunchers();
  } else {
    loadGames();
  }
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

async function loadGames(minMs=0, preselect=null){
  if(!state.account) return;
  state.selected=null; state.gameId=null;
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
    // Defer the auto-select one frame so the list paints first — otherwise
    // a heavy list (e.g. the Installed tab with many games) freezes while
    // the click handler runs search + ambient in the same task.
    requestAnimationFrame(()=>{
      if(preselect!=null){
        const g=state.games.find(x=>x.appid===preselect);
        if(g && g._row){ g._row.click(); return; }
      }
      const first=document.querySelector("#games .game");
      if(first) first.click();
    });
  }catch(e){ if(skelTimer) clearTimeout(skelTimer); $("#games").innerHTML=""; toast(t("games_err")+e.message,"bad"); }
}

// Build every row once; filtering and per-row updates reuse these nodes so a
// keystroke or a single apply doesn't rebuild the list and re-fetch all icons.
function renderGames(){
  const box=$("#games"); box.innerHTML="";
  state.games.forEach(g=>{
    const row=el("div","game"); g._row=row;
    row.title=g.name;   // tooltip — the only label visible when the sidebar is collapsed
    if(state.selected && state.selected.appid===g.appid) row.classList.add("active");
    const ic=el("span","g-ic",GAME_PH);
    const img=el("img"); img.alt="";
    img.addEventListener("load",()=>{ ic.innerHTML=""; ic.appendChild(img); });
    img.src=`/api/gameicon?account=${enc(state.account)}&appid=${g.appid}`;
    row.appendChild(ic);
    row.appendChild(el("span","g-nm",escapeHtml(g.name)));
    row.addEventListener("click", ()=>selectGame(g,row));
    box.appendChild(row);
  });
  filterGames();
}

// Show/hide existing rows by the filter text — no rebuild, no icon re-fetch.
function filterGames(){
  const flt=$("#filter").value.trim().toLowerCase();
  let n=0;
  state.games.forEach(g=>{
    const hide = !!flt && !g.name.toLowerCase().includes(flt);
    if(g._row) g._row.classList.toggle("hidden", hide);
    if(!hide) n++;
  });
  const gc=$("#game-count"); if(gc) gc.textContent=String(n);
}

async function selectGame(g,row){
  state.selected=g; state.gameId=null;
  $("#search").value=g.name;            // search box reflects the loaded game; focus shows its SGDB matches
  document.querySelectorAll(".game.active").forEach(r=>r.classList.remove("active"));
  if(row) row.classList.add("active");
  ambientFromImage(`/api/gameicon?account=${enc(state.account)}&appid=${g.appid}`);
  $("#candidates").classList.add("hidden");
  $("#empty").classList.add("hidden");
  if(!state.keyOk){ showNeedKey(); return; }
  renderSkeletons();
  const tok=++state.searchToken;
  try{
    const d=await jget("/api/search?q="+enc(g.name));
    if(tok!==state.searchToken) return;   // a newer game pick / search superseded this
    state.candidates=d.results||[];
    fillCandidates();
    if(state.candidates.length){ const m=state.candidates[0]; setGame(m.id,m.name); }
  }catch(e){ if(tok===state.searchToken) toast(t("search_error")+e.message,"bad"); }
}

function setGame(id,name){
  state.gameId=id;
  updateCandLabel(); loadArts();
}

/* ---------------- manual search ---------------- */
async function doSearch(){
  const q=$("#search").value.trim() || (state.selected?state.selected.name:"");
  if(!q) return;
  if(!state.keyOk){ showNeedKey(); return; }
  const tok=++state.searchToken;
  try{
    const d=await jget("/api/search?q="+enc(q));
    if(tok!==state.searchToken) return;              // a newer search superseded this one
    state.candidates=d.results||[];
    fillCandidates();
    candOpen(true);                                  // drop the live list (results or "nothing found")
  }catch(e){ if(tok===state.searchToken) toast(t("search_error")+e.message,"bad"); }
}
function fillCandidates(){
  const box=$("#candidates"); box.innerHTML="";
  const menu=el("div","cand-menu");
  if(!state.candidates.length){
    menu.appendChild(el("div","cand-empty",t("nothing_found")));
  }else{
    state.candidates.forEach(g=>{
      const o=el("button","cand-opt"); o.type="button";
      o.innerHTML=`<span class="cand-opt-name">${escapeHtml(g.name)}</span><span class="cand-opt-id">id ${escapeHtml(String(g.id))}</span>`;
      o.addEventListener("click", ()=>{ $("#search").value=g.name; setGame(g.id,g.name); candOpen(false); });
      menu.appendChild(o);
    });
  }
  box.appendChild(menu);
  box.classList.remove("hidden");
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
  const box=$("#candidates"); if(!box) return;
  if(open) box.classList.remove("hidden");   // un-hide so focus can reopen a prior list
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
  $("#anim-wrap").style.display = "";
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
  $("#anim-wrap").style.display = "";
  try{
    const d=await jget(`/api/arts?game_id=${state.gameId}&type=${tp}&animated=${state.animated?1:0}`);
    if(token!==state.reqToken) return;
    grid.querySelectorAll(".skeleton").forEach(s=>s.remove());
    const arts=d.arts||[];
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
  const src=`/img?account=${enc(state.account)}&appid=${state.selected.appid}&type=${state.type}&t=${Date.now()}`;
  const img=el("img"); img.style.objectFit=cfg.fit;
  let hasArt=true;
  img.onerror=()=>{ hasArt=false; w.innerHTML=""; w.appendChild(el("div","none",t("none_short"))); c.classList.add("nopic"); };
  img.src=src; w.appendChild(img);
  c.appendChild(el("div","cur-cap",t("current")));
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
      g.status[state.type]=false;
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
      if(g){ g.status[state.type]=true; }
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

/* ---------------- sidebar collapse ---------------- */
function initSidebar(){
  if (localStorage.getItem("artdeck.sidebar") === "1") document.body.classList.add("sidebar-collapsed");
  const b = $("#btn-sidebar");
  if (!b) return;
  const updateTip = ()=>{ b.title = document.body.classList.contains("sidebar-collapsed") ? t("tip_sidebar_show") : t("tip_sidebar_hide"); };
  updateTip();
  b.addEventListener("click", ()=>{
    const collapsed = document.body.classList.toggle("sidebar-collapsed");
    localStorage.setItem("artdeck.sidebar", collapsed ? "1" : "0");
    updateTip();
  });
}
/* ---------------- mode switch (Covers / Import) ---------------- */
function setMode(mode){
  state.mode = mode;
  document.querySelectorAll(".mode-opt").forEach(b=>b.classList.toggle("active", b.dataset.mode===mode));
  document.body.classList.toggle("is-import", mode==="import");
  const searchRow = $("#search-row");
  const coversToolbar = $("#covers-toolbar");
  if(searchRow) searchRow.classList.toggle("hidden", mode==="import");
  if(coversToolbar) coversToolbar.classList.toggle("hidden", mode==="import");
  if(mode==="import"){
    $("#grid").classList.add("hidden");
    $("#empty").classList.add("hidden");
    $("#import-view").classList.remove("hidden");
    // swap sidebar: show launcher list instead of game list
    loadLaunchers();
  } else {
    $("#grid").classList.remove("hidden");
    $("#import-view").classList.add("hidden");
    // restore sidebar: show game list
    _showCoversSidebar();
  }
}

function _showCoversSidebar(){
  const lb = $("#launcher-list");
  if(lb) lb.remove();
  const sc = $(".side-cap"); if(sc) sc.style.display = "";
  const gl = $("#games"); if(gl) gl.style.display = "";
  const fi = $(".filter"); if(fi) fi.style.display = "";
  const st = $(".src-tabs"); if(st) st.style.display = "";
}

async function loadLaunchers(){
  if(!state.account) return;
  // hide covers-mode sidebar elements; show launcher list instead
  const sc = $(".side-cap"); if(sc) sc.style.display = "none";
  const gl = $("#games"); if(gl) gl.style.display = "none";
  const fi = $(".filter"); if(fi) fi.style.display = "none";
  const st = $(".src-tabs"); if(st) st.style.display = "none";

  let lb = $("#launcher-list");
  if(!lb){
    lb = el("div","launcher-list"); lb.id = "launcher-list";
    const sidebar = $(".sidebar");
    // insert after brand
    const brand = $(".sidebar .brand");
    if(brand && brand.nextSibling) sidebar.insertBefore(lb, brand.nextSibling);
    else sidebar.appendChild(lb);
  }
  lb.innerHTML = `<div class="scan-banner"><span class="scan-spin"></span><span>${escapeHtml(t("scanning"))}</span></div>`;

  try{
    const d = await jget("/api/launchers?account="+enc(state.account));
    state.launchers = d.launchers || [];
    renderLaunchers();
  }catch(e){ lb.innerHTML = ""; toast(t("error")+e.message,"bad"); }
}

function renderLaunchers(){
  const lb = $("#launcher-list"); if(!lb) return;
  lb.innerHTML = "";
  if(!state.launchers.length){
    lb.appendChild(el("div","launcher-empty",t("import_no_launchers")));
    return;
  }
  const cap = el("div","side-cap launcher-cap");
  cap.appendChild(el("span","side-cap-t",t("import_launchers_section")));
  // scan/refresh button mirroring #btn-refresh in Covers
  const rb = el("button","refresh-btn"); rb.id = "btn-launcher-refresh"; rb.title = t("import_refresh");
  rb.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 4v5h-5"/></svg>`;
  rb.addEventListener("click", refreshLaunchers);
  cap.appendChild(rb);
  lb.appendChild(cap);
  state.launchers.forEach(lau=>{
    const row = el("div","launcher-row"+(state.activeLauncher===lau.key?" active":""));
    row.title = lau.label;
    const ic = el("span","launcher-ic"); ic.innerHTML = _launcherIcon(lau.key);
    const nm = el("span","launcher-nm",escapeHtml(lau.label));
    const cnt = el("span","launcher-cnt",String((lau.games||[]).length));
    row.appendChild(ic); row.appendChild(nm); row.appendChild(cnt);
    row.addEventListener("click", ()=>selectLauncher(lau));
    lb.appendChild(row);
  });
  // auto-select first launcher
  if(state.launchers.length && !state.activeLauncher){
    selectLauncher(state.launchers[0]);
  }
}

async function refreshLaunchers(){
  const b = $("#btn-launcher-refresh"); if(b) b.classList.add("spin");
  state.activeLauncher = null;
  await loadLaunchers();
  const b2 = $("#btn-launcher-refresh"); if(b2) b2.classList.remove("spin");
  toast(t("import_refreshed"), "ok");
}

function _launcherIcon(key){
  // Brand logos from Simple Icons (CC0). viewBox 0 0 24 24, fill="currentColor".
  if(key === "epic") return `<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M3.537 0C2.165 0 1.66.506 1.66 1.879V18.44a4.262 4.262 0 00.02.433c.031.3.037.59.316.92.027.033.311.245.311.245.153.075.258.13.43.2l8.335 3.491c.433.199.614.276.928.27h.002c.314.006.495-.071.928-.27l8.335-3.492c.172-.07.277-.124.43-.2 0 0 .284-.211.311-.243.28-.33.285-.621.316-.92a4.261 4.261 0 00.02-.434V1.879c0-1.373-.506-1.88-1.878-1.88zm13.366 3.11h.68c1.138 0 1.688.553 1.688 1.696v1.88h-1.374v-1.8c0-.369-.17-.54-.523-.54h-.235c-.367 0-.537.17-.537.539v5.81c0 .369.17.54.537.54h.262c.353 0 .523-.171.523-.54V8.619h1.373v2.143c0 1.144-.562 1.71-1.7 1.71h-.694c-1.138 0-1.7-.566-1.7-1.71V4.82c0-1.144.562-1.709 1.7-1.709zm-12.186.08h3.114v1.274H6.117v2.603h1.648v1.275H6.117v2.774h1.74v1.275h-3.14zm3.816 0h2.198c1.138 0 1.7.564 1.7 1.708v2.445c0 1.144-.562 1.71-1.7 1.71h-.799v3.338h-1.4zm4.53 0h1.4v9.201h-1.4zm-3.13 1.235v3.392h.575c.354 0 .523-.171.523-.54V4.965c0-.368-.17-.54-.523-.54zm-3.74 10.147a1.708 1.708 0 01.591.108 1.745 1.745 0 01.49.299l-.452.546a1.247 1.247 0 00-.308-.195.91.91 0 00-.363-.068.658.658 0 00-.28.06.703.703 0 00-.224.163.783.783 0 00-.151.243.799.799 0 00-.056.299v.008a.852.852 0 00.056.31.7.7 0 00.157.245.736.736 0 00.238.16.774.774 0 00.303.058.79.79 0 00.445-.116v-.339h-.548v-.565H7.37v1.255a2.019 2.019 0 01-.524.307 1.789 1.789 0 01-.683.123 1.642 1.642 0 01-.602-.107 1.46 1.46 0 01-.478-.3 1.371 1.371 0 01-.318-.455 1.438 1.438 0 01-.115-.58v-.008a1.426 1.426 0 01.113-.57 1.449 1.449 0 01.312-.46 1.418 1.418 0 01.474-.309 1.58 1.58 0 01.598-.111 1.708 1.708 0 01.045 0zm11.963.008a2.006 2.006 0 01.612.094 1.61 1.61 0 01.507.277l-.386.546a1.562 1.562 0 00-.39-.205 1.178 1.178 0 00-.388-.07.347.347 0 00-.208.052.154.154 0 00-.07.127v.008a.158.158 0 00.022.084.198.198 0 00.076.066.831.831 0 00.147.06c.062.02.14.04.236.061a3.389 3.389 0 01.43.122 1.292 1.292 0 01.328.17.678.678 0 01.207.24.739.739 0 01.071.337v.008a.865.865 0 01-.081.382.82.82 0 01-.229.285 1.032 1.032 0 01-.353.18 1.606 1.606 0 01-.46.061 2.16 2.16 0 01-.71-.116 1.718 1.718 0 01-.593-.346l.43-.514c.277.223.578.335.9.335a.457.457 0 00.236-.05.157.157 0 00.082-.142v-.008a.15.15 0 00-.02-.077.204.204 0 00-.073-.066.753.753 0 00-.143-.062 2.45 2.45 0 00-.233-.062 5.036 5.036 0 01-.413-.113 1.26 1.26 0 01-.331-.16.72.72 0 01-.222-.243.73.73 0 01-.082-.36v-.008a.863.863 0 01.074-.359.794.794 0 01.214-.283 1.007 1.007 0 01.34-.185 1.423 1.423 0 01.448-.066 2.006 2.006 0 01.025 0zm-9.358.025h.742l1.183 2.81h-.825l-.203-.499H8.623l-.198.498h-.81zm2.197.02h.814l.663 1.08.663-1.08h.814v2.79h-.766v-1.602l-.711 1.091h-.016l-.707-1.083v1.593h-.754zm3.469 0h2.235v.658h-1.473v.422h1.334v.61h-1.334v.442h1.493v.658h-2.255zm-5.3.897l-.315.793h.624zm-1.145 5.19h8.014l-4.09 1.348z"/></svg>`;
  if(key === "gog")  return `<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M7.15 15.24H4.36a.4.4 0 0 0-.4.4v2c0 .21.18.4.4.4h2.8v1.32h-3.5c-.56 0-1.02-.46-1.02-1.03v-3.39c0-.56.46-1.02 1.03-1.02h3.48v1.32zM8.16 11.54c0 .58-.47 1.05-1.05 1.05H2.63v-1.35h3.78a.4.4 0 0 0 .4-.4V6.39a.4.4 0 0 0-.4-.4H4.39a.4.4 0 0 0-.41.4v2.02c0 .23.18.4.4.4H6v1.35H3.68c-.58 0-1.05-.46-1.05-1.04V5.68c0-.57.47-1.04 1.05-1.04H7.1c.58 0 1.05.47 1.05 1.04v5.86zM21.36 19.36h-1.32v-4.12h-.93a.4.4 0 0 0-.4.4v3.72h-1.33v-4.12h-.93a.4.4 0 0 0-.4.4v3.72h-1.33v-4.42c0-.56.46-1.02 1.03-1.02h5.61v5.44zM21.37 11.54c0 .58-.47 1.05-1.05 1.05h-4.48v-1.35h3.78a.4.4 0 0 0 .4-.4V6.39a.4.4 0 0 0-.4-.4h-2.03a.4.4 0 0 0-.4.4v2.02c0 .23.18.4.4.4h1.62v1.35H16.9c-.58 0-1.05-.46-1.05-1.04V5.68c0-.57.47-1.04 1.05-1.04h3.43c.58 0 1.05.47 1.05 1.04v5.86zM13.72 4.64h-3.44c-.58 0-1.04.47-1.04 1.04v3.44c0 .58.46 1.04 1.04 1.04h3.44c.57 0 1.04-.46 1.04-1.04V5.68c0-.57-.47-1.04-1.04-1.04m-.3 1.75v2.02a.4.4 0 0 1-.4.4h-2.03a.4.4 0 0 1-.4-.4V6.4c0-.22.17-.4.4-.4H13c.23 0 .4.18.4.4zM12.63 13.92H9.24c-.57 0-1.03.46-1.03 1.02v3.39c0 .57.46 1.03 1.03 1.03h3.39c.57 0 1.03-.46 1.03-1.03v-3.39c0-.56-.46-1.02-1.03-1.02m-.3 1.72v2a.4.4 0 0 1-.4.4v-.01H9.94a.4.4 0 0 1-.4-.4v-1.99c0-.22.18-.4.4-.4h2c.22 0 .4.18.4.4zM23.49 1.1a1.74 1.74 0 0 0-1.24-.52H1.75A1.74 1.74 0 0 0 0 2.33v19.34a1.74 1.74 0 0 0 1.75 1.75h20.5A1.74 1.74 0 0 0 24 21.67V2.33c0-.48-.2-.92-.51-1.24m0 20.58a1.23 1.23 0 0 1-1.24 1.24H1.75A1.23 1.23 0 0 1 .5 21.67V2.33a1.23 1.23 0 0 1 1.24-1.24h20.5a1.24 1.24 0 0 1 1.24 1.24v19.34z"/></svg>`;
  // neutral fallback
  const s = (body)=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
  return s(`<rect x="4" y="4" width="16" height="16" rx="3"/>`);
}

function selectLauncher(lau){
  state.activeLauncher = lau.key;
  document.querySelectorAll(".launcher-row").forEach(r=>r.classList.remove("active"));
  const rows = document.querySelectorAll(".launcher-row");
  const idx = state.launchers.findIndex(l=>l.key===lau.key);
  if(rows[idx]) rows[idx].classList.add("active");
  renderImportCards(lau.games || []);
}

function renderImportCards(games){
  _importGames = games;
  // respect the persisted view preference
  if(_currentImportView() === "list"){ renderImportList(games); return; }
  const box = $("#import-cards"); box.innerHTML = "";
  box.classList.remove("list");
  box.style.setProperty("--card-w", "170px");
  if(!games.length){
    box.appendChild(el("div","import-empty",t("import_no_games")));
    _updateImportAddLabel();
    return;
  }
  games.forEach((g,i)=>{
    const cfg = {ar:"2/3", fit:"cover"};
    const {c,w} = cardShell(cfg, i);
    c.classList.add("imp-cover-card");
    if(!g.imported) c.classList.add("imp-grayscale");
    // cover image — src from /api/launcher-cover?name=...
    const img = el("img"); img.alt = ""; img.style.objectFit = "cover";
    const coverFail = ()=>{ c.classList.remove("loading"); w.innerHTML=""; w.appendChild(el("div","none",GAME_PH)); };
    img.addEventListener("load", ()=>c.classList.remove("loading"));
    img.addEventListener("error", coverFail);
    c.classList.add("loading");
    w.appendChild(img);
    // the endpoint returns JSON {thumb}; fetch it, then load that image URL
    jget("/api/launcher-cover?name="+enc(g.name)).then(d=>{ if(d && d.thumb){ img.src = d.thumb; } else { coverFail(); } }).catch(coverFail);
    // game name label
    c.appendChild(el("div","imp-cover-nm",escapeHtml(g.name)));
    if(g.imported){
      // already in Steam: badge + explicit Customize button
      c.appendChild(el("span","imp-badge",t("imported_badge")));
      // quick-customize: prev/next arrows that flip covers without leaving Import
      _attachQcArrows(c, w, img, g);
      const custBtn = el("button","imp-customize",t("customize"));
      custBtn.addEventListener("click", ev=>{ ev.stopPropagation(); openInArtwork(g); });
      c.appendChild(custBtn);
    } else {
      // not yet imported: checkbox overlay; clicking card toggles it
      const cb = el("input"); cb.type = "checkbox"; cb.className = "imp-cb";
      cb.checked = true; cb.dataset.appid = String(g.appid);
      cb.addEventListener("change", _updateImportAddLabel);
      cb.addEventListener("click", e=>e.stopPropagation());
      const cbWrap = el("label","imp-cb-wrap"); cbWrap.appendChild(cb);
      c.appendChild(cbWrap);
      c.addEventListener("click", ()=>{ cb.checked = !cb.checked; _updateImportAddLabel(); });
    }
    box.appendChild(c);
  });
  _updateImportAddLabel();
}

// --- quick-customize: arrow buttons on imported cover cards ---
function _attachQcArrows(card, wrap, img, g){
  // per-card lazy state — covers fetched once on first arrow press
  let covers = null;    // null = not yet fetched; [] = fetched, none found
  let idx = 0;
  let applyTimer = null;

  const prev = el("button", "qc-arrow qc-prev", "&#8249;");
  const next = el("button", "qc-arrow qc-next", "&#8250;");
  prev.title = t("qc_hint");
  next.title = t("qc_hint");

  function _showCover(){
    if(!covers || !covers.length) return;
    idx = ((idx % covers.length) + covers.length) % covers.length;
    img.src = covers[idx].thumb;
  }

  function _scheduleApply(){
    clearTimeout(applyTimer);
    applyTimer = setTimeout(async ()=>{
      if(!covers || !covers.length) return;
      const entry = covers[idx];
      try{
        const r = await jpost("/api/apply", {
          account: state.account,
          appid: g.steam_appid,
          type: "cover",
          url: entry.url,
        });
        if(r.ok){
          card.classList.remove("qc-saved-pulse");
          // force reflow to restart the animation
          void card.offsetWidth;
          card.classList.add("qc-saved-pulse");
          toast(t("qc_saved"), "ok");
        } else {
          toast(t("error") + (r.error || "?"), "bad");
        }
      }catch(e){ toast(t("error") + e.message, "bad"); }
    }, 500);
  }

  async function _arrowClick(delta, e){
    e.stopPropagation();
    if(covers === null){
      // first press — fetch the cover list
      prev.disabled = true;
      next.disabled = true;
      try{
        const d = await jget("/api/launcher-covers?name=" + enc(g.name));
        covers = (d && d.covers) || [];
      }catch(_){ covers = []; }
      prev.disabled = false;
      next.disabled = false;
      if(!covers.length){ toast(t("qc_none"), "bad"); return; }
    }
    if(!covers.length) return;
    idx += delta;
    _showCover();
    _scheduleApply();
  }

  prev.addEventListener("click", e=>_arrowClick(-1, e));
  next.addEventListener("click", e=>_arrowClick(+1, e));

  wrap.appendChild(prev);
  wrap.appendChild(next);
}

// --- import view: grid / list toggle (F6) ---
let _importGames = [];  // last rendered set; re-rendered on view switch

function _initImportViewToggle(){
  const saved = localStorage.getItem("artdeck.importview") || "grid";
  _setImportView(saved, false);
  const gb = $("#ivt-grid"), lb = $("#ivt-list"); if(!gb || !lb) return;
  gb.title = t("import_view_grid");
  lb.title = t("import_view_list");
  gb.addEventListener("click", ()=>_setImportView("grid", true));
  lb.addEventListener("click", ()=>_setImportView("list", true));
}

function _setImportView(view, persist){
  if(persist) localStorage.setItem("artdeck.importview", view);
  const gb = $("#ivt-grid"), lb = $("#ivt-list"); if(!gb || !lb) return;
  gb.classList.toggle("active", view === "grid");
  gb.setAttribute("aria-pressed", String(view === "grid"));
  lb.classList.toggle("active", view === "list");
  lb.setAttribute("aria-pressed", String(view === "list"));
  if(_importGames.length) {
    if(view === "grid") renderImportCards(_importGames);
    else renderImportList(_importGames);
  }
}

function _currentImportView(){
  return localStorage.getItem("artdeck.importview") || "grid";
}

function renderImportList(games){
  _importGames = games;
  const box = $("#import-cards"); box.innerHTML = "";
  box.classList.add("list");
  if(!games.length){
    box.appendChild(el("div","import-empty",t("import_no_games")));
    _updateImportAddLabel();
    return;
  }
  games.forEach(g=>{
    const row = el("div","imp-list-row"+(g.imported?" imp-list-row--imported":""));
    // thumbnail
    const thumb = el("div","imp-list-thumb"+(g.imported?"":" imp-grayscale")); thumb.innerHTML = GAME_PH;
    const img = el("img"); img.alt = "";
    img.addEventListener("load", ()=>{ thumb.innerHTML = ""; thumb.appendChild(img); });
    // the endpoint returns JSON {thumb}; fetch it, then load that image URL
    jget("/api/launcher-cover?name="+enc(g.name)).then(d=>{ if(d && d.thumb){ img.src = d.thumb; } }).catch(()=>{});
    // name
    const nm = el("span","imp-list-nm",escapeHtml(g.name));
    row.appendChild(thumb); row.appendChild(nm);
    if(g.imported){
      // already in Steam: badge + explicit Customize button
      const badge = el("span","imp-badge imp-badge--list",t("imported_badge"));
      row.appendChild(badge);
      const custBtn = el("button","imp-customize",t("customize"));
      custBtn.addEventListener("click", ev=>{ ev.stopPropagation(); openInArtwork(g); });
      row.appendChild(custBtn);
    } else {
      // not yet imported: checkbox; clicking row toggles it
      const cb = el("input"); cb.type = "checkbox"; cb.className = "imp-cb imp-list-cb";
      cb.checked = true; cb.dataset.appid = String(g.appid);
      cb.addEventListener("change", _updateImportAddLabel);
      cb.addEventListener("click", e=>e.stopPropagation());
      row.appendChild(cb);
      row.addEventListener("click", ()=>{ cb.checked = !cb.checked; _updateImportAddLabel(); });
    }
    box.appendChild(row);
  });
  _updateImportAddLabel();
}

async function openInArtwork(g){
  setMode("covers");
  // activate the Non-Steam source tab — mirror the existing .src-tab click handler
  state.source = "shortcut";
  document.querySelectorAll(".src-tab").forEach(x=>x.classList.remove("active"));
  const shortcutTab = document.querySelector(".src-tab[data-src='shortcut']");
  if(shortcutTab) shortcutTab.classList.add("active");
  const srcTabs = $("#src-tabs");
  if(srcTabs) srcTabs.dataset.src = "shortcut";
  $("#filter").value = "";
  // prefer the real Steam shortcut appid when available; loadGames auto-selects it
  const want = g.steam_appid != null ? g.steam_appid : g.appid;
  await loadGames(0, want);
}

function _checkedImportAppids(){
  return [...document.querySelectorAll(".imp-cb:checked")].map(cb=>cb.dataset.appid);
}

function _updateImportAddLabel(){
  const btn = $("#import-add"); if(!btn) return;
  const n = _checkedImportAppids().length;
  btn.textContent = t("import_add_btn").replace("%d", String(n));
}

async function doImport(){
  const appids = _checkedImportAppids();
  if(!appids.length) return;
  let close_steam = false;
  try{
    const sr = await jget("/api/steam-running");
    if(sr.running){
      const confirmed = await _confirmDialog(t("import_close_steam"));
      if(!confirmed) return;
      close_steam = true;
    }
  }catch(e){ /* if endpoint missing, proceed without check */ }
  const download_art = $("#import-art").checked;
  try{
    const res = await jpost("/api/import", {account:state.account, appids, close_steam, download_art});
    if(res.ok){
      toast(t("import_done").replace("%d", String(res.added)), "ok");
      if(download_art){ runAutofill(state.account); }
      state.activeLauncher = null; loadLaunchers();
    } else if(res.steam_running){
      // server says Steam is open; ask to close it
      const confirmed = await _confirmDialog(t("import_close_steam"));
      if(!confirmed) return;
      const res2 = await jpost("/api/import", {account:state.account, appids, close_steam:true, download_art});
      if(res2.ok){
        toast(t("import_done").replace("%d", String(res2.added)), "ok");
        if(download_art){ runAutofill(state.account); }
        state.activeLauncher = null; loadLaunchers();
      } else {
        toast(t("error")+(res2.error||"?"), "bad");
      }
    } else {
      toast(t("error")+(res.error||"?"), "bad");
    }
  }catch(e){ toast(t("error")+e.message, "bad"); }
}

// minimal confirm dialog using the existing modal/closeModal helpers
function _confirmDialog(msg){
  return new Promise(resolve=>{
    modal(msg, "",
      [{x:t("cancel"),              cls:"ghost",   fn:()=>{ closeModal(); resolve(false); }},
       {x:t("import_close_confirm"), cls:"primary", fn:()=>{ closeModal(); resolve(true); }}]);
  });
}

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
     <input type="text" id="m-key" placeholder="${t("key_placeholder")}" autocomplete="off">`,
    [{x:t("cancel"),cls:"ghost",fn:closeModal},
     {x:t("save"),cls:"primary",fn:async()=>{
        const v=$("#m-key").value.trim(); closeModal();
        const r=await jpost("/api/key",{key:v});
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
