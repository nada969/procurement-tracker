import {createStore, downloadFile} from "./store.js";

const TECH=[["Pending","gr"],["In review","wa"],["Clarification","wa"],["Compliant","ok"],["Non-compliant","er"]];
const STAGE=[["Invited","gr"],["Submitted","in"],["Awarded","ok"],["Declined","gr"]];
const SUGG=["Earthing","Surge Arresters","Lighting","Transformers","Cables","Inverters","Trackers"];
let db,dl,P=[],K=[],S=[],N=[],noteDraft="",noteAbout="",route={v:"home"},tab="sup",fTech="",sortK="name",sortD=1,q="",cur=null;
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money=n=>n==null||n===""||isNaN(n)?"–":"$"+Math.round(n).toLocaleString("en-US");
const today=()=>new Date().toISOString().slice(0,10);
const sum=a=>a.reduce((x,y)=>x+(y||0),0);
const badge=(l,L)=>{const c=(L.find(x=>x[0]===l)||[0,"gr"])[1];return `<span class="badge s-${c}">${esc(l)}</span>`};
const col=n=>db.collection(n),newId=n=>col(n).doc().id;
const pkgs=p=>K.filter(k=>k.projectId===p.id),sups=k=>S.filter(s=>s.packageId===k.id);
const best=k=>sups(k).filter(s=>s.tech==="Compliant"&&s.total).sort((a,b)=>a.total-b.total)[0];
const od=s=>s.due&&s.due<today()&&["Invited","Submitted"].includes(s.stage)&&s.tech!=="Non-compliant";
const pstat=k=>{const s=sups(k);return s.some(x=>x.stage==="Awarded")?"Awarded":s.some(x=>x.tech==="Compliant")?"Evaluating":"Open"};
const vs=(t,b)=>t&&b?(t-b)/b:null,pct=r=>r==null?"–":(r>0?"+":"")+(r*100).toFixed(0)+"%";
const vc=r=>r==null?"":r>0?"od":"";

async function init(){
  db=createStore();dl={save:async({filename,data})=>downloadFile(filename,data)};
  if(!db){$("main").innerHTML='<div class="empty">Storage is unavailable in this browser.</div>';return}
  [["projects",v=>P=v],["packages",v=>K=v],["suppliers",v=>S=v],["notes",v=>N=v]].forEach(([n,set])=>col(n).onSnapshot(s=>{set(s.docs.map(d=>({id:d.id,...d.data()})));if(ready<4)ready++;if(ready===4)draw()},e=>{$("main").innerHTML='<div class="empty">Cannot reach the server: '+esc(e.message)+'</div>'}));
  fromHash();
}
let ready=0;
const hashOf=()=>route.v==="home"?"#/":route.v==="project"?"#/p/"+route.p:"#/p/"+route.p+"/k/"+route.k;
function fromHash(){const m=(location.hash||"").match(/^#\/p\/([^/]+)(?:\/k\/([^/]+))?/);const r=m?(m[2]?{v:"package",p:m[1],k:m[2]}:{v:"project",p:m[1]}):{v:"home"};if(JSON.stringify(r)!==JSON.stringify(route)){route=r;draw()}}
window.addEventListener("hashchange",fromHash);

function draw(){
  if(ready<4)return;
  let p=P.find(x=>x.id===route.p),k=K.find(x=>x.id===route.k&&x.projectId===route.p);
  if(route.v==="package"&&!k)route=p?{v:"project",p:p.id}:{v:"home"};
  if(route.v==="project"&&!p)route={v:"home"};
  const cr=['<a data-nav="home">Projects</a>'];let sw="";
  const opts=(a,id)=>a.map(x=>`<option value="${x.id}"${x.id===id?" selected":""}>${esc(x.name)}</option>`).join("");
  if(p){cr.push(route.v==="project"?`<b>${esc(p.name)}</b>`:`<a data-nav="project" data-p="${p.id}">${esc(p.name)}</a>`);
    if(route.v==="project")sw=`<select data-sw="p" title="Switch project">${opts(P,p.id)}</select>`}
  if(route.v==="package"){cr.push(`<b>${esc(k.name)}</b>`);sw=`<select data-sw="k" title="Switch package">${opts(pkgs(p),k.id)}</select>`}
  $("crumb").innerHTML=cr.join(" › ")+" "+sw;
  $("main").innerHTML=route.v==="home"?home():route.v==="project"?project(p):pack(p,k);
  try{if(location.hash!==hashOf())location.hash=hashOf()}catch(e){}
}
const head=(t,s,b)=>`<div class="top" style="margin:12px 0 14px"><div><h2 class="h">${esc(t)}</h2><div class="sub">${s}</div></div><div class="bar" style="margin:0">${b}</div></div>`;

function home(){
  const cards=P.map(p=>{const ks=pkgs(p),bu=sum(ks.map(k=>k.budget)),bs=ks.map(best).filter(Boolean),sp=ks.flatMap(sups);
    const r=bs.length&&bs.length===ks.length?vs(sum(bs.map(x=>x.total)),bu):null;
    return `<div class="card pcard" data-nav="project" data-p="${p.id}"><h3>${esc(p.name)}</h3><div class="sub">${esc(p.client||"")}${p.status==="Archived"?" · Archived":""}</div>
    <div class="st"><div><div class="l">Packages</div><div class="v">${ks.length}</div></div><div><div class="l">Budget</div><div class="v">${bu?money(bu):"–"}</div></div>
    <div><div class="l">Compliant bids</div><div class="v">${bs.length} of ${ks.length} packages</div></div><div><div class="l">Best vs budget</div><div class="v ${vc(r)}">${pct(r)}</div></div>
    <div><div class="l">Overdue actions</div><div class="v ${sp.some(od)?"od":""}">${sp.filter(od).length}</div></div><div><div class="l">Awarded</div><div class="v">${ks.filter(k=>pstat(k)==="Awarded").length}</div></div></div></div>`}).join("");
  return head("Projects",P.length+" project"+(P.length===1?"":"s"),'<button data-act="backup">Download backup</button><button data-act="restore">Restore backup</button><button class="p" data-act="addProject">+ New project</button>')+
    (P.length?`<div class="pc">${cards}</div>`:'<div class="card empty">No projects yet. Create your first one.</div>');
}
function project(p){
  const ks=pkgs(p).sort((a,b)=>a.name.localeCompare(b.name));
  const free=SUGG.filter(n=>!ks.some(k=>k.name===n));
  const rows=ks.map(k=>{const b=best(k),s=sups(k);return `<tr class="go" style="cursor:pointer" data-nav="package" data-p="${p.id}" data-k="${k.id}"><td><b>${esc(k.name)}</b></td><td>${badge(pstat(k),[["Awarded","ok"],["Evaluating","wa"],["Open","gr"]])}</td><td class="num">${money(k.budget)}</td><td class="num">${b?money(b.total):"–"}${b?`<div class="mu">${esc(b.name)}</div>`:""}</td><td class="num ${vc(vs(b&&b.total,k.budget))}">${pct(vs(b&&b.total,k.budget))}</td><td class="num">${s.filter(x=>x.tech==="Compliant").length} / ${s.length}</td><td>${esc(k.ros||"–")}</td></tr>`}).join("");
  return head(p.name,esc(p.client||"")+" · "+ks.length+" packages",'<button data-act="editProject">Edit project</button><button data-act="xlsProj">Export Excel</button><button class="p" data-act="addPackage">+ Add package</button>')+
    `<div class="tw"><table><thead><tr><th>Package</th><th>Status</th><th class="num">Budget</th><th class="num">Lowest compliant</th><th class="num">vs budget</th><th class="num">Compliant / total</th><th>Required on site</th></tr></thead><tbody>${rows||'<tr><td colspan="7" class="empty">No packages yet.</td></tr>'}</tbody></table></div>`+
    (free.length?`<div class="chips" style="margin-top:12px"><span class="mu" style="align-self:center">Quick add:</span>${free.map(n=>`<button class="chip" data-act="suggest" data-name="${n}">+ ${n}</button>`).join("")}</div>`:"");
}
function pack(p,k){
  const ss=sups(k),b=best(k),B=k.budget||0;
  return head(k.name,esc(p.name)+(B?" · Budget "+money(B):"")+(k.ros?" · Required on site "+esc(k.ros):""),'<button data-act="editPackage">Edit package</button><button data-act="xlsPkg">Export Excel</button>'+(dl?'<button data-act="exp">Export CSV</button>':"")+'<button class="p" data-act="addSupplier">+ Add supplier</button>')+
  `<div class="cards"><div class="card"><div class="l">Suppliers</div><div class="v">${ss.length}</div></div><div class="card"><div class="l">Overdue actions</div><div class="v ${ss.some(od)?"od":""}">${ss.filter(od).length}</div></div>
  <div class="card"><div class="l">Lowest compliant bid</div><div class="v">${b?money(b.total):"–"}</div><div class="mu">${b?esc(b.name):"none yet"}</div></div>
  <div class="card"><div class="l">Best vs budget</div><div class="v ${vc(vs(b&&b.total,B))}">${pct(vs(b&&b.total,B))}</div></div></div>
  <div class="tabs"><button class="tab ${tab==="sup"?"on":""}" data-act="tab" data-tab="sup">Suppliers</button><button class="tab ${tab==="cmp"?"on":""}" data-act="tab" data-tab="cmp">Compare</button><button class="tab ${tab==="notes"?"on":""}" data-act="tab" data-tab="notes">Notes (${N.filter(n=>n.packageId===k.id).length})</button></div>`+
  (tab==="cmp"?compare(k):tab==="notes"?notesTab(k):supTab(k));
}
function supTab(k){
  const ss=sups(k),cnt={};ss.forEach(s=>cnt[s.tech]=(cnt[s.tech]||0)+1);
  const th=[["name","Supplier"],["tech","Technical"],["stage","Stage"],["total","Bid (USD)"],["vs","vs budget"],["leadWeeks","Lead (wk)"],["nextAction","Next action"],["due","Due"]];
  return `<input id="q" type="search" placeholder="Search suppliers…" value="${esc(q)}" style="width:100%;margin-bottom:10px">
  <div class="chips"><button class="chip ${fTech?"":"on"}" data-act="tech" data-t="">All ${ss.length}</button>${TECH.filter(t=>cnt[t[0]]).map(t=>`<button class="chip ${fTech===t[0]?"on":""}" data-act="tech" data-t="${t[0]}">${t[0]} ${cnt[t[0]]}</button>`).join("")}</div>
  <div class="tw"><table><thead><tr>${th.map(h=>`<th data-act="sort" data-k="${h[0]}" class="${["total","vs","leadWeeks"].includes(h[0])?"num":""}">${h[1]}${sortK===h[0]?(sortD>0?" ▲":" ▼"):""}</th>`).join("")}</tr></thead><tbody id="rows">${supRows(k)}</tbody></table></div>`;
}
function supRows(k){
  const B=k.budget||0,v=s=>vs(s.total,B),key=s=>sortK==="vs"?v(s):s[sortK];
  const r=sups(k).filter(s=>(!fTech||s.tech===fTech)&&(!q||[s.name,s.nextAction,s.reason].join(" ").toLowerCase().includes(q.toLowerCase())));
  r.sort((a,b)=>{const x=key(a),y=key(b);if(x==null||x==="")return 1;if(y==null||y==="")return -1;return(x>y?1:x<y?-1:0)*sortD});
  return r.length?r.map(s=>`<tr style="cursor:pointer" data-act="editSupplier" data-id="${s.id}"><td><b>${esc(s.name)}</b>${nc(s)}${s.reason?`<div class="mu">${esc(s.reason)}</div>`:""}</td><td>${badge(s.tech,TECH)}</td><td>${badge(s.stage,STAGE)}</td><td class="num">${money(s.total)}</td><td class="num ${vc(v(s))}">${pct(v(s))}</td><td class="num">${s.leadWeeks??"–"}</td><td>${esc(s.nextAction)}</td><td class="${od(s)?"od":""}">${esc(s.due)}${od(s)?" ⚠":""}</td></tr>`).join(""):'<tr><td colspan="8" class="empty">No suppliers match. Use “+ Add supplier”.</td></tr>';
}
const nc=s=>{const n=N.filter(x=>x.supplierId===s.id).length;return n?` <span class="mu">· ${n} note${n>1?"s":""}</span>`:""};
function notesTab(k){
  const ss=sups(k),ns=N.filter(n=>n.packageId===k.id).sort((a,b)=>(b.createdAt||"").localeCompare(a.createdAt||""));
  const who=n=>{const s=n.supplierId&&S.find(x=>x.id===n.supplierId);return s?esc(s.name):"Whole package"};
  const fmt=t=>t?new Date(t).toLocaleString([],{dateStyle:"medium",timeStyle:"short"}):"";
  return `<div class="card" style="margin-bottom:12px"><label for="nbody">Add a note</label>
  <textarea id="nbody" rows="3" style="width:100%" placeholder="What did you do or decide? e.g. Called Alpha, they confirmed 8 weeks.">${esc(noteDraft)}</textarea>
  <div class="bar" style="margin:8px 0 0"><select id="nabout"><option value="">About: whole package</option>${ss.map(s=>`<option value="${s.id}"${s.id===noteAbout?" selected":""}>About: ${esc(s.name)}</option>`).join("")}</select><span style="flex:1"></span><button class="p" data-act="addNote">Add note</button></div></div>`+
  (ns.length?ns.map(n=>`<div class="card nt"><div class="mu">${fmt(n.createdAt)} · <b>${who(n)}</b><button class="d" data-act="delNote" data-id="${n.id}" style="float:right;padding:1px 8px">Delete</button></div><div style="white-space:pre-wrap;margin-top:4px">${esc(n.body)}</div></div>`).join(""):'<div class="card empty">No notes yet. Write what you did and decided.</div>');
}
function compare(k){
  const ss=sups(k).slice().sort((a,b)=>(a.total??1e18)-(b.total??1e18));
  if(!ss.length)return '<div class="card empty">Add suppliers to compare their offers side by side.</div>';
  const ok=ss.filter(s=>s.tech==="Compliant"),minT=Math.min(...ok.filter(s=>s.total).map(s=>s.total)),minL=Math.min(...ok.filter(s=>s.leadWeeks!=null).map(s=>s.leadWeeks)),B=k.budget||0;
  const dim=s=>s.tech!=="Compliant"?"dim ":"";
  const row=(l,f,c)=>`<tr><th>${l}</th>${ss.map(s=>`<td class="${dim(s)}${c?c(s):""}">${f(s)}</td>`).join("")}</tr>`;
  return `<div class="tw"><table class="cmp"><thead><tr><th></th>${ss.map(s=>`<th class="${dim(s)}">${esc(s.name)}</th>`).join("")}</tr></thead><tbody>`+
   row("Technical",s=>badge(s.tech,TECH))+row("Stage",s=>badge(s.stage,STAGE))+
   row("Bid (USD)",s=>money(s.total),s=>s.tech==="Compliant"&&s.total===minT?"best":"")+
   row("vs budget",s=>pct(vs(s.total,B)))+
   row("Lead time (wk)",s=>s.leadWeeks??"–",s=>s.tech==="Compliant"&&s.leadWeeks===minL?"best":"")+
   row("Incoterm",s=>esc(s.incoterm||"–"))+row("Payment",s=>esc(s.payment||"–"))+row("Technical note",s=>esc(s.reason||"–"))+
   `</tbody></table></div><p class="mu">Greyed columns are not technically compliant. Green marks the best compliant value.</p>`;
}

function form(title,fields,v,onSave,onDel){
  $("mt").textContent=title;
  $("fg").innerHTML=fields.map(f=>`<div class="${f.full?"f":""}"><label>${f.l}</label>`+(f.o?`<select data-k="${f.k}">${f.o.map(o=>`<option${o===v[f.k]?" selected":""}>${o}</option>`).join("")}</select>`:f.t==="ta"?`<textarea data-k="${f.k}" rows="2">${esc(v[f.k]||"")}</textarea>`:`<input data-k="${f.k}" type="${f.t||"text"}"${f.t==="number"?' step="any" min="0"':""} value="${esc(v[f.k]==null?"":v[f.k])}">`)+"</div>").join("");
  $("del").style.display=onDel?"":"none";cur={fields,onSave,onDel};$("ov").classList.add("show");
  const f=$("fg").querySelector("input");f&&f.focus();
}
const close=()=>$("ov").classList.remove("show");
$("cancel").onclick=close;$("ov").onclick=e=>{if(e.target===$("ov"))close()};
document.addEventListener("keydown",e=>{if(e.key==="Escape")close()});
$("save").onclick=async()=>{const o={};
  document.querySelectorAll("#fg [data-k]").forEach(el=>{const f=cur.fields.find(x=>x.k===el.dataset.k);o[f.k]=f.t==="number"?(el.value===""?null:parseFloat(el.value)):el.value.trim()});
  if(!o[cur.fields[0].k]){return}close();try{await cur.onSave(o)}catch(e){alert("Save failed: "+(e.message||e.code))}};
$("del").onclick=async()=>{if(!cur.onDel)return;close();try{await cur.onDel()}catch(e){alert("Delete failed")}};

const F={
 project:[{k:"name",l:"Project name",full:1},{k:"client",l:"Client / owner"},{k:"status",l:"Status",o:["Active","Archived"]}],
 package:[{k:"name",l:"Package name",full:1},{k:"budget",l:"Budget (USD)",t:"number"},{k:"ros",l:"Required on site",t:"date"}],
 supplier:[{k:"name",l:"Supplier"},{k:"total",l:"Bid total (USD)",t:"number"},{k:"tech",l:"Technical status",o:TECH.map(t=>t[0])},{k:"stage",l:"Commercial stage",o:STAGE.map(t=>t[0])},{k:"incoterm",l:"Incoterm / delivery"},{k:"payment",l:"Payment terms"},{k:"leadWeeks",l:"Lead time (weeks)",t:"number"},{k:"due",l:"Next action due",t:"date"},{k:"nextAction",l:"Next action",full:1},{k:"reason",l:"Technical note",t:"ta",full:1}]
};
const del=async(name,ids)=>{await Promise.all(ids.map(([c,id])=>col(c).doc(id).delete()))};
const acts={
 addProject(){form("New project",F.project,{status:"Active"},async o=>{const id=newId("projects");await col("projects").doc(id).set(o);route={v:"project",p:id};draw()})},
 editProject(){const p=P.find(x=>x.id===route.p);form("Edit project",F.project,p,o=>col("projects").doc(p.id).set(o),async()=>{if(!confirm("Delete this project with all its packages and suppliers?"))return;const ks=pkgs(p);await del("",[...ks.flatMap(k=>sups(k).map(s=>["suppliers",s.id])),...ks.map(k=>["packages",k.id]),["projects",p.id]]);route={v:"home"};draw()})},
 addPackage(){form("Add package",F.package,{},o=>col("packages").doc(newId("packages")).set({...o,projectId:route.p}))},
 suggest(d){return col("packages").doc(newId("packages")).set({name:d.name,projectId:route.p,budget:null,ros:""})},
 editPackage(){const k=K.find(x=>x.id===route.k);form("Edit package",F.package,k,o=>col("packages").doc(k.id).set({...o,projectId:k.projectId}),async()=>{if(!confirm("Delete this package and its suppliers?"))return;await del("",[...sups(k).map(s=>["suppliers",s.id]),["packages",k.id]]);route={v:"project",p:k.projectId};draw()})},
 addSupplier(){supForm(null)},
 editSupplier(d){supForm(S.find(x=>x.id===d.id))},
 tab(d){tab=d.tab;draw()},tech(d){fTech=d.t;draw()},
 sort(d){sortD=sortK===d.k?-sortD:1;sortK=d.k;draw()},
 async addNote(){const b=$("nbody").value.trim();if(!b){$("nbody").focus();return}
  const k=K.find(x=>x.id===route.k),sid=$("nabout").value;noteDraft="";noteAbout="";
  try{await col("notes").doc(newId("notes")).set({packageId:k.id,supplierId:sid||null,body:b})}catch(e){alert("Save failed: "+(e.message||e))}},
 async delNote(d){if(!confirm("Delete this note?"))return;try{await col("notes").doc(d.id).delete()}catch(e){alert("Delete failed")}},
 xlsPkg(){location.href="/api/export/package/"+route.k+".xlsx"},
 xlsProj(){location.href="/api/export/project/"+route.p+".xlsx"},
 backup(){location.href="/api/backup"},
 restore(){const i=document.createElement("input");i.type="file";i.accept="application/json";
  i.onchange=async()=>{const f=i.files[0];if(!f)return;if(!confirm("Restore from "+f.name+"? Records with the same id are overwritten; all others are kept."))return;
   try{const r=await fetch("/api/restore",{method:"POST",headers:{"Content-Type":"application/json"},body:await f.text()});if(!r.ok)throw new Error(await r.text());await db.refresh();alert("Restore complete.")}catch(e){alert("Restore failed: "+e.message)}};i.click()},
 async exp(){const k=K.find(x=>x.id===route.k),c=s=>'"'+String(s==null?"":s).replace(/"/g,'""')+'"';
  const csv=[["Supplier","Technical","Stage","Bid USD","Incoterm","Payment","Lead weeks","Next action","Due","Note"].map(c).join(",")].concat(sups(k).map(s=>[s.name,s.tech,s.stage,s.total,s.incoterm,s.payment,s.leadWeeks,s.nextAction,s.due,s.reason].map(c).join(","))).join("\n");
  try{await dl.save({filename:k.name.replace(/\W+/g,"-")+"-suppliers.csv",data:csv})}catch(e){}}
};
function supForm(s){
  const k=K.find(x=>x.id===route.k);
  form(s?"Edit supplier":"Add supplier",F.supplier,s||{tech:"Pending",stage:"Invited"},async o=>{
    const h=(s&&s.history||[]).slice();if(!s||s.tech!==o.tech||s.stage!==o.stage)h.push({t:today(),s:o.tech+" / "+o.stage});
    await col("suppliers").doc(s?s.id:newId("suppliers")).set({...o,packageId:k.id,history:h.slice(-30)})},
    s&&(()=>{if(confirm("Delete "+s.name+"?"))return col("suppliers").doc(s.id).delete()}));
}
document.addEventListener("click",e=>{const t=e.target.closest("[data-nav],[data-act]");if(!t)return;const d=t.dataset;
  if(d.nav){route=d.nav==="home"?{v:"home"}:d.nav==="project"?{v:"project",p:d.p}:{v:"package",p:d.p,k:d.k};tab="sup";fTech="";q="";draw();return}
  acts[d.act]&&acts[d.act](d)});
document.addEventListener("change",e=>{if(e.target.id==="nabout"){noteAbout=e.target.value;return}const s=e.target.dataset&&e.target.dataset.sw;if(!s)return;
  route=s==="p"?{v:"project",p:e.target.value}:{v:"package",p:route.p,k:e.target.value};tab="sup";draw()});
document.addEventListener("input",e=>{if(e.target.id==="nbody")noteDraft=e.target.value;if(e.target.id==="q"){q=e.target.value;const k=K.find(x=>x.id===route.k);if(k)$("rows").innerHTML=supRows(k)}});
init();
