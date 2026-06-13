"use strict";
/* ArtDeck — фронтенд. Чистый vanilla, без сборки. Зовёт локальный JSON-API. */

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
  reqToken:0, keyOk:false,
};

const $  = s=>document.querySelector(s);
const el = (tag,cls,html)=>{const e=document.createElement(tag); if(cls)e.className=cls; if(html!=null)e.innerHTML=html; return e;};
async function jget(u){const r=await fetch(u); if(!r.ok) throw new Error((await r.json().catch(()=>({error:r.status}))).error||r.status); return r.json();}
async function jpost(u,b){const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}); return r.json();}
const enc = encodeURIComponent;
const IS_VIDEO = u => /\.(webm|mp4)(\?|$)/i.test(u || "");

/* ---------------- i18n статика ---------------- */
function applyStatic(){
  document.querySelectorAll("[data-i18n]").forEach(e=>{ e.textContent = t(e.dataset.i18n); });
  $("#filter").placeholder = t("filter_games");
  $("#search").placeholder = t("search_sgdb");
  $("#btn-lang").textContent = t("lang_name");
  document.documentElement.lang = LANG;
}

/* ---------------- init ---------------- */
window.addEventListener("DOMContentLoaded", init);

async function init(){
  applyStatic();
  buildTabs();
  $("#filter").addEventListener("input", renderGames);
  $("#search").addEventListener("keydown", e=>{ if(e.key==="Enter") doSearch(); });
  document.addEventListener("click", e=>{ const b=$("#candidates"); if(b && !b.contains(e.target)) candOpen(false); });
  document.addEventListener("keydown", e=>{ if(e.key==="Escape") candOpen(false); });
  $("#btn-autofill").addEventListener("click", autofill);
  $("#btn-clean").addEventListener("click", openClean);
  $("#btn-key").addEventListener("click", editKey);
  $("#btn-lang").addEventListener("click", toggleLang);
  $("#anim").addEventListener("change", e=>{ state.animated=e.target.checked; if(state.gameId) loadArts(); });

  // вкладки источника (Non-Steam / Установленные)
  document.querySelectorAll(".src-tab").forEach(tab=>{
    tab.addEventListener("click", ()=>{
      if(tab.classList.contains("active")) return;
      document.querySelectorAll(".src-tab").forEach(x=>x.classList.remove("active"));
      tab.classList.add("active");
      state.source = tab.dataset.src;
      $("#src-tabs").dataset.src = state.source;
      loadGames();
    });
  });

  // дропдаун аккаунта
  $("#acct-btn").addEventListener("click", toggleAcctMenu);
  document.addEventListener("click", e=>{ if(!$("#acct").contains(e.target)) closeAcctMenu(); });
  // лайтбокс
  $("#light-x").addEventListener("click", closeLight);
  $("#light").addEventListener("click", e=>{ if(e.target.id==="light") closeLight(); });
  document.addEventListener("keydown", e=>{ if(e.key==="Escape"){ closeLight(); closeModal(); } });

  try{
    const st = await jget("/api/state");
    setKey(st.key_ok);
    if(!st.steam_path){ toast(t("steam_not_found"),"bad"); return; }
    state.accounts = st.accounts || [];
    renderAcctMenu();
    if(state.accounts.length){ selectAccount(state.accounts[0].uid); }
    if(!st.key_ok) toast(t("no_key_hint"),"bad");
  }catch(e){ toast(t("error")+e.message,"bad"); }
}

function toggleLang(){
  setLang(nextLang());
  applyStatic();
  buildTabs();
  setKey(state.keyOk);
  renderAcctMenu();
  if(state.matchName) $("#match-sub").innerHTML = matchSubHtml();
  else if(state.selected) $("#match-sub").textContent = t("searching");
  if(!state.selected) $("#match-name").textContent = t("pick_game");
}

/* ---------------- аккаунты ---------------- */
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
function toggleAcctMenu(){ const m=$("#acct-menu"); const open=m.classList.toggle("hidden"); $("#acct-btn").setAttribute("aria-expanded", String(!open)); }
function closeAcctMenu(){ $("#acct-menu").classList.add("hidden"); $("#acct-btn").setAttribute("aria-expanded","false"); }

/* ---------------- список игр ---------------- */
async function loadGames(){
  if(!state.account) return;
  state.selected=null; state.gameId=null; state.matchName=null;
  $("#match-name").textContent=t("pick_game"); $("#match-sub").textContent="";
  $("#grid").innerHTML=""; $("#candidates").classList.add("hidden");
  try{
    const d = await jget(`/api/games?account=${enc(state.account)}&source=${state.source}`);
    state.games = d.games||[];
    renderGames();
    const first=document.querySelector("#games .game");
    if(first) first.click();
  }catch(e){ toast(t("games_err")+e.message,"bad"); }
}

function renderGames(){
  const flt=$("#filter").value.trim().toLowerCase();
  const box=$("#games"); box.innerHTML="";
  state.games.filter(g=>!flt||g.name.toLowerCase().includes(flt)).forEach(g=>{
    const row=el("div","game");
    if(state.selected && state.selected.appid===g.appid) row.classList.add("active");
    const ic=el("span","g-ic",GAME_PH);
    const img=el("img"); img.alt="";
    img.addEventListener("load",()=>{ ic.innerHTML=""; ic.appendChild(img); });
    img.src=`/api/gameicon?account=${enc(state.account)}&appid=${g.appid}`;
    row.appendChild(ic);
    row.appendChild(el("span","g-nm",escapeHtml(g.name)));
    const cov=el("div","cov"); let have=0;
    STATUS_ORDER.forEach(tp=>{
      const on=!!(g.status && g.status[tp]); if(on) have++;
      const seg=el("span","seg"+(tp==="cover"?" cover":"")+(on?" on":""));
      seg.title=t("t_"+tp)+(on?" ✓":" ✗");
      cov.appendChild(seg);
    });
    const missing=STATUS_ORDER.filter(tp=>!(g.status && g.status[tp])).map(tp=>t("t_"+tp));
    cov.classList.toggle("need", !(g.status && g.status.cover));
    cov.title = have===5 ? t("cov_full")
      : t("cov_count",have)+" · "+t("cov_missing")+": "+missing.join(", ");
    row.appendChild(cov);
    row.addEventListener("click", ()=>selectGame(g,row));
    box.appendChild(row);
  });
}

async function selectGame(g,row){
  state.selected=g; state.gameId=null; state.matchName=null;
  document.querySelectorAll(".game.active").forEach(r=>r.classList.remove("active"));
  if(row) row.classList.add("active");
  $("#match-name").textContent=g.name;
  $("#match-sub").textContent=t("searching");
  $("#candidates").classList.add("hidden");
  $("#empty").classList.add("hidden");
  renderSkeletons();
  try{
    const d=await jget("/api/search?q="+enc(g.name));
    state.candidates=d.results||[];
    fillCandidates();
    if(state.candidates.length){ const m=state.candidates[0]; setGame(m.id,m.name); }
    else $("#match-sub").textContent=t("not_found_manual");
  }catch(e){ $("#match-sub").textContent=t("search_error")+e.message; }
}

function matchSubHtml(){ return `SteamGridDB: <b>${escapeHtml(state.matchName)}</b> · id ${state.gameId}`; }
function setGame(id,name){ state.gameId=id; state.matchName=name; $("#match-sub").innerHTML=matchSubHtml(); updateCandLabel(); loadArts(); }

/* ---------------- ручной поиск ---------------- */
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

/* ---------------- вкладки типов ---------------- */
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

/* ---------------- арты ---------------- */
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
  c.appendChild(el("span","badge",t("current")));
  const img=el("img"); img.style.objectFit=cfg.fit;
  img.onerror=()=>{ w.innerHTML=""; w.appendChild(el("div","none",t("none_short"))); };
  img.src=`/img?account=${enc(state.account)}&appid=${state.selected.appid}&type=${state.type}&t=${Date.now()}`;
  w.appendChild(img); return c;
}

function artCard(a,cfg,i){
  const{c,w}=cardShell(cfg,i); c.classList.add("loading");
  if(a.animated) c.appendChild(el("span","badge anim",t("animated_badge")));
  const done=()=>c.classList.remove("loading");
  const fail=()=>{ c.classList.remove("loading"); w.innerHTML=""; w.appendChild(el("div","none","⚠")); };
  if(IS_VIDEO(a.thumb)){
    // лёгкое .webm-превью анимации (десятки КБ), полный url не грузим в сетке
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

/* ---------------- лайтбокс предпросмотра ---------------- */
function openLight(a){
  state.selectedArt=a;
  const stage=$("#light-stage"); stage.innerHTML="";
  if(IS_VIDEO(a.thumb)){
    // анимацию показываем лёгким .webm-превью, тяжёлый url качаем только при установке
    const v=el("video"); v.src=a.thumb; v.muted=true; v.loop=true; v.autoplay=true; v.controls=false;
    v.setAttribute("playsinline",""); stage.appendChild(v);
  } else {
    const img=el("img"); img.src=a.url||a.thumb; stage.appendChild(img);
  }
  const dims=(a.width&&a.height)?`${a.width}×${a.height}`:"";
  $("#light-meta").innerHTML = dims + (a.style?` · <b>${escapeHtml(a.style)}</b>`:"") + (a.animated?` · ${t("animated_badge")}`:"");
  const ap=$("#light-apply"); ap.textContent=t("apply"); ap.onclick=()=>{ applyArt(a,null); closeLight(); };
  $("#light").classList.remove("hidden");
}
function closeLight(){ $("#light").classList.add("hidden"); $("#light-stage").innerHTML=""; }

/* ---------------- применение ---------------- */
async function applyArt(a,card){
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
      if(g){ g.status[state.type]=true; renderGames(); }
    }else toast(t("error")+(r.error||"?"),"bad");
  }catch(e){ toast(t("apply_err")+e.message,"bad"); }
}

/* ---------------- авто-дозаливка ---------------- */
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

/* ---------------- очистка ---------------- */
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

/* ---------------- ключ ---------------- */
function setKey(ok){
  state.keyOk=ok;
  const b=$("#btn-key");
  b.classList.remove("ok","bad"); b.classList.add(ok?"ok":"bad");
  $("#key-label").textContent = ok ? t("key_ok") : t("key_need");
}
function editKey(){
  modal(t("key_title"),
    `<p style="margin:0 0 4px">${t("key_hint")}</p><input type="text" id="m-key" placeholder="${t("key_placeholder")}">`,
    [{x:t("cancel"),cls:"ghost",fn:closeModal},
     {x:t("save"),cls:"primary",fn:async()=>{
        const v=$("#m-key").value.trim(); closeModal();
        const r=await jpost("/api/key",{key:v});
        setKey(r.key_ok); toast(r.key_ok?t("key_saved"):t("key_cleared"), r.key_ok?"ok":"bad");
        if(r.key_ok && state.selected) selectGame(state.selected, document.querySelector(".game.active"));
     }}]);
}

/* ---------------- ui-хелперы ---------------- */
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
