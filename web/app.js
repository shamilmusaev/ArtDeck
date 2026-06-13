"use strict";

const SVG = (b)=>`<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${b}</svg>`;
const ICONS = {
  cover:  SVG(`<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="1.6"/><path d="m21 15-4-4-9 9"/>`),
  banner: SVG(`<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="8" cy="10" r="1.6"/><path d="m22 16-5-5L9 19"/>`),
  hero:   SVG(`<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20h14V9.5"/><path d="M9.5 20v-5h5v5"/>`),
  logo:   SVG(`<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>`),
  icon:   SVG(`<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.2" fill="currentColor"/>`),
};
const KEY_ICON = SVG(`<path d="M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z"/><circle cx="16.5" cy="7.5" r=".5" fill="currentColor"/>`);

const TYPES = [
  {id:"cover",  title:"Обложка", ar:"2/3",    w:160, fit:"cover"},
  {id:"banner", title:"Баннер",  ar:"460/215", w:250, fit:"cover"},
  {id:"hero",   title:"Hero",    ar:"96/31",  w:320, fit:"cover"},
  {id:"logo",   title:"Logo",    ar:"3/2",    w:200, fit:"contain"},
  {id:"icon",   title:"Icon",    ar:"1/1",    w:104, fit:"contain"},
];
const TYPE = Object.fromEntries(TYPES.map(t=>[t.id,t]));

const state = {
  account:null, games:[], selected:null, gameId:null,
  matchName:null, type:"cover", candidates:[], reqToken:0,
};

const $ = s=>document.querySelector(s);
const el = (tag,cls,html)=>{const e=document.createElement(tag); if(cls)e.className=cls; if(html!=null)e.innerHTML=html; return e;};
async function jget(u){const r=await fetch(u); if(!r.ok) throw new Error((await r.json().catch(()=>({error:r.status}))).error||r.status); return r.json();}
async function jpost(u,b){const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}); return r.json();}

/* ---------- init ---------- */
window.addEventListener("DOMContentLoaded", init);

async function init(){
  buildTabs();
  $("#account").addEventListener("change", e=>{state.account=e.target.value; loadGames();});
  $("#filter").addEventListener("input", ()=>renderGames());
  $("#btn-autofill").addEventListener("click", autofill);
  $("#btn-clean").addEventListener("click", openClean);
  $("#btn-key").addEventListener("click", editKey);
  $("#search").addEventListener("keydown", e=>{if(e.key==="Enter") doSearch();});
  $("#candidates").addEventListener("change", onCandidate);

  try{
    const st = await jget("/api/state");
    setKey(st.key_ok);
    if(!st.steam_path){ toast("Steam не найден","bad"); return; }
    const sel=$("#account"); sel.innerHTML="";
    st.accounts.forEach(a=>sel.appendChild(el("option",null,a)));
    if(st.accounts.length){ state.account=st.accounts[0]; sel.value=state.account; loadGames(); }
    if(!st.key_ok) toast("Нет API-ключа — нажми «Ключ»","bad");
  }catch(e){ toast("Ошибка: "+e.message,"bad"); }
}

function setKey(ok){
  const p=$("#key-pill");
  p.innerHTML = KEY_ICON+"<span>"+(ok?"Ключ: OK":"Ключ: нет")+"</span>";
  p.className = "pill "+(ok?"ok":"bad");
}

/* ---------- games ---------- */
async function loadGames(){
  if(!state.account) return;
  try{
    const d = await jget("/api/games?account="+encodeURIComponent(state.account));
    state.games = d.games;
    renderGames();
    const first = document.querySelector("#games .game");
    if(first) first.click();   // авто-выбор первой игры
  }catch(e){ toast("Не загрузить игры: "+e.message,"bad"); }
}

function renderGames(){
  const flt = $("#filter").value.trim().toLowerCase();
  const box = $("#games"); box.innerHTML="";
  state.games.filter(g=>!flt||g.name.toLowerCase().includes(flt)).forEach(g=>{
    const row = el("div","game");
    row.appendChild(el("span","nm",escapeHtml(g.name)));
    const dots = el("div","dots");
    ["cover","banner","hero","logo","icon"].forEach(t=>{
      const d=el("span","dot"+(g.status[t]?" on":"")); d.title=t; dots.appendChild(d);
    });
    row.appendChild(dots);
    row.addEventListener("click", ()=>selectGame(g,row));
    if(state.selected && state.selected.appid===g.appid) row.classList.add("active");
    box.appendChild(row);
  });
}

async function selectGame(g,row){
  state.selected=g;
  document.querySelectorAll(".game.active").forEach(r=>r.classList.remove("active"));
  if(row) row.classList.add("active");
  $("#match-name").textContent = g.name;
  $("#match-sub").textContent = "Поиск совпадения на SteamGridDB…";
  $("#candidates").classList.add("hidden");
  $("#empty").classList.add("hidden");
  renderSkeletons();   // сразу показываем загрузку, ещё до поиска
  try{
    const d = await jget("/api/search?q="+encodeURIComponent(g.name));
    state.candidates = d.results||[];
    fillCandidates();
    if(state.candidates.length){
      const m=state.candidates[0];
      setGame(m.id, m.name);
    }else{
      $("#match-sub").textContent="Не найдено — попробуй ручной поиск";
    }
  }catch(e){ $("#match-sub").textContent="Ошибка поиска: "+e.message; }
}

function setGame(id,name){
  state.gameId=id; state.matchName=name;
  $("#match-sub").innerHTML = `SteamGridDB: <b>${escapeHtml(name)}</b> · id ${id}`;
  loadArts();
}

/* ---------- manual search ---------- */
async function doSearch(){
  const q=$("#search").value.trim() || (state.selected?state.selected.name:"");
  if(!q) return;
  try{
    const d=await jget("/api/search?q="+encodeURIComponent(q));
    state.candidates=d.results||[];
    fillCandidates();
    if(state.candidates.length){toast("Найдено: "+state.candidates.length);}
    else toast("Ничего не найдено","bad");
  }catch(e){toast("Ошибка: "+e.message,"bad");}
}

function fillCandidates(){
  const sel=$("#candidates"); sel.innerHTML="";
  state.candidates.forEach(g=>sel.appendChild(el("option",null,`${escapeHtml(g.name)} (id ${g.id})`)));
  sel.classList.toggle("hidden", state.candidates.length===0);
}

function onCandidate(){
  const i=$("#candidates").selectedIndex;
  if(i>=0 && i<state.candidates.length){ const g=state.candidates[i]; setGame(g.id,g.name); }
}

/* ---------- tabs ---------- */
function buildTabs(){
  const box=$("#tabs"); box.innerHTML="";
  TYPES.forEach(t=>{
    const tab=el("div","tab"+(t.id===state.type?" active":""),t.title);
    tab.addEventListener("click", ()=>{
      state.type=t.id;
      document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
      tab.classList.add("active");
      if(state.gameId) loadArts();
    });
    box.appendChild(tab);
  });
}

/* ---------- arts ---------- */
function renderSkeletons(){
  const cfg=TYPE[state.type];
  const grid=$("#grid");
  grid.style.setProperty("--card-w", cfg.w+"px");
  grid.innerHTML="";
  if(state.selected) grid.appendChild(currentCard(cfg));
  for(let i=0;i<12;i++){ grid.appendChild(skeleton(cfg,i)); }
  grid.dataset.skel = state.type;
}

async function loadArts(){
  if(!state.gameId) return;
  const t=state.type, cfg=TYPE[t];
  const token=++state.reqToken;
  const grid=$("#grid");
  // не перерисовываем скелетоны, если они уже показаны для этого типа (без мигания)
  if(grid.dataset.skel!==t || !grid.querySelector(".skeleton")) renderSkeletons();
  try{
    const d=await jget(`/api/arts?game_id=${state.gameId}&type=${t}`);
    if(token!==state.reqToken) return;
    grid.querySelectorAll(".skeleton").forEach(s=>s.remove());
    const arts=d.arts||[];
    if(!arts.length){ grid.appendChild(el("div","empty","Нет вариантов в базе для этого типа")); }
    arts.forEach((a,i)=>grid.appendChild(artCard(a,cfg,i)));
  }catch(e){
    if(token!==state.reqToken) return;
    grid.querySelectorAll(".skeleton").forEach(s=>s.remove());
    toast("Не загрузить варианты: "+e.message,"bad");
  }
}

function cardShell(cfg,i){
  const c=el("div","card");
  c.style.animationDelay=(i*25)+"ms";
  const w=el("div","imgwrap");
  w.style.setProperty("--ar",cfg.ar);
  c.appendChild(w);
  return {c,w};
}

function skeleton(cfg,i){ const {c}=cardShell(cfg,i); c.classList.add("skeleton"); return c; }

function currentCard(cfg){
  const {c,w}=cardShell(cfg,0);
  c.classList.add("current");
  c.appendChild(el("span","badge","Текущая"));
  const img=el("img");
  img.style.objectFit=cfg.fit;
  img.onerror=()=>{ w.innerHTML=""; w.appendChild(el("div","none","нет")); };
  img.src=`/img?account=${encodeURIComponent(state.account)}&appid=${state.selected.appid}&type=${state.type}&t=${Date.now()}`;
  w.appendChild(img);
  return c;
}

function artCard(a,cfg,i){
  const {c,w}=cardShell(cfg,i);
  c.classList.add("loading");
  const img=el("img");
  img.style.objectFit=cfg.fit;
  img.addEventListener("load",()=>c.classList.remove("loading"));
  img.addEventListener("error",()=>{
    if(!img.dataset.fb && a.url && a.url!==a.thumb){ img.dataset.fb="1"; img.src=a.url; }
    else { c.classList.remove("loading"); w.innerHTML=""; w.appendChild(el("div","none","⚠")); }
  });
  img.src=a.thumb;
  if(img.complete && img.naturalWidth>0) c.classList.remove("loading");
  w.appendChild(img);
  c.appendChild(meta(a));
  const btn=el("button","apply","✓ Установить");
  btn.addEventListener("click",ev=>{ev.stopPropagation(); applyArt(a,c);});
  c.appendChild(btn);
  c.addEventListener("click",()=>{
    document.querySelectorAll(".card.sel").forEach(x=>x.classList.remove("sel"));
    c.classList.add("sel"); state.selectedArt=a;
  });
  return c;
}

function meta(a){
  const m=el("div","meta");
  m.appendChild(el("span",null,(a.width&&a.height)?`${a.width}×${a.height}`:""));
  if(a.style) m.appendChild(el("span",null,a.style));
  return m;
}

async function applyArt(a,card){
  card.classList.add("sel");
  try{
    const r=await jpost("/api/apply",{account:state.account,appid:state.selected.appid,type:state.type,url:a.url});
    if(r.ok){
      toast("Установлено: "+r.dest+" · перезапусти Steam","ok");
      document.querySelectorAll(".card.current img").forEach(img=>{
        img.src=`/img?account=${encodeURIComponent(state.account)}&appid=${state.selected.appid}&type=${state.type}&t=${Date.now()}`;
      });
      // обновить точку в списке
      const g=state.games.find(x=>x.appid===state.selected.appid);
      if(g){ g.status[state.type]=true; renderGames(); }
    }else{ toast("Ошибка: "+(r.error||"?"),"bad"); }
  }catch(e){ toast("Ошибка применения: "+e.message,"bad"); }
}

/* ---------- autofill ---------- */
function autofill(){
  modal("Авто-дозаливка недостающего",
    `<p>Скачать все недостающие арты и заполнить пробелы? Существующее не трогается.</p>
     <label style="display:flex;gap:8px;align-items:center;margin-top:10px">
       <input type="checkbox" id="m-all"> Все аккаунты (иначе только текущий)</label>`,
    [{t:"Отмена",cls:"ghost",fn:closeModal},
     {t:"Запустить",fn:()=>{const all=$("#m-all").checked; closeModal(); runAutofill(all?"all":state.account);}}]);
}

function runAutofill(scope){
  $("#overlay").classList.remove("hidden");
  $("#ov-game").textContent="Подготовка…";
  $("#bar-fill").style.width="0%";
  $("#ov-count").textContent="";
  const es=new EventSource("/api/autofill?accounts="+encodeURIComponent(scope));
  es.onmessage=ev=>{
    const d=JSON.parse(ev.data);
    if(d.type==="start"){ $("#ov-count").textContent="Игр к обработке: "+d.total; }
    else if(d.type==="progress"){
      $("#ov-game").textContent=d.game;
      $("#bar-fill").style.width=Math.round(d.i/Math.max(1,d.total)*100)+"%";
      $("#ov-count").textContent=`${d.i} / ${d.total}`;
    }else if(d.type==="error"){ es.close(); $("#overlay").classList.add("hidden"); toast(d.message,"bad"); }
    else if(d.type==="done"){
      es.close(); $("#overlay").classList.add("hidden");
      toast(`Дозаливка: +${d.ok}, пропущено ${d.skip}, ошибок ${d.fail} · перезапусти Steam`, d.fail?"bad":"ok");
      loadGames();
    }
  };
  es.onerror=()=>{ es.close(); $("#overlay").classList.add("hidden"); toast("Соединение прервано","bad"); };
}

/* ---------- cleanup ---------- */
async function openClean(){
  let d;
  try{ d=await jget("/api/orphans"); }catch(e){ toast("Ошибка: "+e.message,"bad"); return; }
  const items=d.items||[];
  if(!items.length){ toast("Осиротевших артов нет","ok"); return; }
  const body=el("div");
  items.forEach((it,i)=>{
    const row=el("div","orphan");
    const cb=el("input"); cb.type="checkbox"; cb.checked=true; cb.dataset.i=i;
    row.appendChild(cb);
    const info=el("div");
    info.appendChild(el("div","of",escapeHtml(it.file)));
    info.appendChild(el("div","oa","аккаунт "+it.account));
    row.appendChild(info);
    body.appendChild(row);
  });
  modal(`Очистка осиротевших (${items.length})`, body.outerHTML,
    [{t:"Отмена",cls:"ghost",fn:closeModal},
     {t:"Удалить выбранное",fn:async()=>{
        const chosen=[...document.querySelectorAll(".orphan input:checked")].map(cb=>items[+cb.dataset.i]);
        closeModal();
        const r=await jpost("/api/clean",{items:chosen});
        toast("Удалено файлов: "+(r.removed||0),"ok");
        loadGames();
     }}]);
}

/* ---------- key ---------- */
function editKey(){
  modal("API-ключ SteamGridDB",
    `<p style="color:#8b97ad;margin:0 0 10px">steamgriddb.com → Preferences → API</p>
     <input type="text" id="m-key" placeholder="Вставь ключ…">`,
    [{t:"Отмена",cls:"ghost",fn:closeModal},
     {t:"Сохранить",fn:async()=>{
        const v=$("#m-key").value.trim(); closeModal();
        const r=await jpost("/api/key",{key:v});
        setKey(r.key_ok); toast(r.key_ok?"Ключ сохранён":"Ключ очищен", r.key_ok?"ok":"bad");
        if(r.key_ok && state.selected) selectGame(state.selected);
     }}]);
}

/* ---------- ui helpers ---------- */
function toast(msg,kind){
  const t=el("div","toast"+(kind?" "+kind:""),escapeHtml(msg));
  $("#toasts").appendChild(t);
  setTimeout(()=>{t.classList.add("out"); setTimeout(()=>t.remove(),300);}, 3800);
}

function modal(title,bodyHtml,actions){
  $("#modal-title").textContent=title;
  $("#modal-body").innerHTML=bodyHtml;
  const a=$("#modal-actions"); a.innerHTML="";
  actions.forEach(act=>{
    const b=el("button","btn"+(act.cls?" "+act.cls:""),act.t);
    b.addEventListener("click",act.fn);
    a.appendChild(b);
  });
  $("#modal").classList.remove("hidden");
}
function closeModal(){ $("#modal").classList.add("hidden"); }

function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}
