"""HTML timeline generator for AgentLens runs."""

from __future__ import annotations

import json
from typing import Any


def generate_html(run: dict[str, Any]) -> str:
    """Return a fully self-contained HTML timeline for the given run."""
    run_json = json.dumps(run, ensure_ascii=False, default=str)
    # Escape </script> so injected JSON cannot break out of the <script> block.
    run_json = run_json.replace("</script>", r"<\/script>")
    title = _esc(str(run.get("name") or run.get("run_id") or "AgentLens Run"))
    return _TEMPLATE.replace("/*__RUN_DATA__*/null", run_json).replace("__TITLE__", title)


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgentLens — __TITLE__</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0a0b;--surface:#121215;--surface2:#1a1a1f;--border:#26262c;
  --text:#e4e4e7;--muted:#71717a;
  --blue:#3b82f6;--amber:#f59e0b;--red:#ef4444;--green:#22c55e;--purple:#8b5cf6;
}
body{background:var(--bg);color:var(--text);font-family:'SF Mono','Fira Code','Cascadia Code',monospace;font-size:13px;line-height:1.6;padding:24px;min-height:100vh}
.container{max-width:1100px;margin:0 auto}

/* Header card */
.card{border:1px solid var(--border);border-radius:8px;background:var(--surface);margin-bottom:16px;overflow:hidden}
.card-header{padding:12px 20px;border-bottom:1px solid var(--border);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);display:flex;align-items:center;justify-content:space-between}

.run-header{padding:20px 24px 16px}
.run-name{font-size:17px;font-weight:600;letter-spacing:-0.3px;margin-bottom:6px;display:flex;align-items:center;gap:10px}
.status-badge{display:inline-flex;align-items:center;gap:5px;padding:2px 9px;border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;flex-shrink:0}
.badge-success{background:rgba(34,197,94,.15);color:var(--green)}
.badge-error{background:rgba(239,68,68,.15);color:var(--red)}
.badge-running{background:rgba(59,130,246,.15);color:var(--blue)}
.badge-unknown{background:var(--surface2);color:var(--muted)}
.run-meta{color:var(--muted);font-size:11px;margin-bottom:16px}
.stats-row{display:flex;gap:24px;flex-wrap:wrap}
.stat{display:flex;flex-direction:column;gap:2px}
.stat-val{font-size:15px;font-weight:600}
.stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}
.c-blue{color:var(--blue)}.c-amber{color:var(--amber)}.c-red{color:var(--red)}.c-green{color:var(--green)}

/* Timeline */
.span-row{border-bottom:1px solid var(--border);cursor:pointer;transition:background .12s}
.span-row:last-child{border-bottom:none}
.span-row:hover{background:var(--surface2)}
.span-row.open{background:var(--surface2)}
.span-main{display:grid;grid-template-columns:20px 1fr auto;gap:12px;align-items:start;padding:11px 20px}
.dot{width:9px;height:9px;border-radius:50%;margin-top:5px;flex-shrink:0}
.dot-llm{background:var(--blue);box-shadow:0 0 5px var(--blue)}
.dot-tool{background:var(--amber);box-shadow:0 0 5px var(--amber)}
.dot-error{background:var(--red);box-shadow:0 0 5px var(--red)}
.dot-memory{background:var(--purple);box-shadow:0 0 5px var(--purple)}
.dot-langgraph{background:var(--green);box-shadow:0 0 5px var(--green)}
.span-info{min-width:0}
.span-title{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.span-sub{color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}
.bar-wrap{height:3px;background:var(--border);border-radius:2px;margin-top:7px;max-width:220px}
.bar-fill{height:100%;border-radius:2px}
.bar-llm{background:var(--blue)}.bar-tool{background:var(--amber)}.bar-error{background:var(--red)}.bar-memory{background:var(--purple)}.bar-langgraph{background:var(--green)}
.span-right{text-align:right;flex-shrink:0}
.span-lat{font-size:12px;font-weight:600}
.chevron{display:inline-block;transition:transform .18s;color:var(--muted);font-size:10px;margin-right:5px}
.span-row.open .chevron{transform:rotate(90deg)}

/* Detail panel */
.span-detail{display:none;padding:0 20px 14px 52px;border-top:1px solid var(--border)}
.span-detail.open{display:block}
.dl{margin-top:10px}
.dl-lbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:4px}
.dl-val{background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:8px 10px;font-size:12px;white-space:pre-wrap;word-break:break-word;max-height:280px;overflow-y:auto}
.dl-val.err{border-color:var(--red);color:var(--red)}

/* Message blocks */
.msg{margin-bottom:8px}
.msg-role{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px}
.role-system{color:var(--purple)}.role-user{color:var(--blue)}.role-assistant{color:var(--green)}.role-tool{color:var(--amber)}.role-unknown{color:var(--muted)}
.msg-body{background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:7px 10px;font-size:12px;white-space:pre-wrap;word-break:break-word;max-height:180px;overflow-y:auto}
.tool-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:4px}
.chip{background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.25);color:var(--amber);border-radius:4px;padding:1px 8px;font-size:11px}

/* Prompt viewer section */
.pv-step{padding:14px 20px;border-bottom:1px solid var(--border)}
.pv-step:last-child{border-bottom:none}
.pv-step-hdr{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:10px}
.toggle-section{cursor:pointer;user-select:none}
footer{text-align:center;color:var(--muted);font-size:11px;padding:20px 0}
</style>
</head>
<body>
<div class="container" id="root"></div>
<script>
const RUN = /*__RUN_DATA__*/null;

/* ── utils ─────────────────────────────────────────────────────────── */
function ms(v){if(!v||v<=0)return'';return v<1000?v.toFixed(0)+'ms':(v/1000).toFixed(2)+'s'}
function cost(v){if(!v||v<=0)return'';return v<0.0001?'<$0.0001':'$'+v.toFixed(6)}
function esc(s){if(s==null)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function cj(o,max){try{const s=JSON.stringify(o,null,2);return s.length>max?s.slice(0,max)+'…':s}catch{return String(o)}}
function usage(span){const u=span.usage||{};const i=(u.input_tokens||0)+(u.prompt_tokens||0);const o=(u.output_tokens||0)+(u.completion_tokens||0);return{i,o,tot:i+o}}
function dotCls(t){return t==='llm_call'?'llm':t==='tool_call'?'tool':t==='error'?'error':t==='memory_snapshot'?'memory':t==='langgraph_node'?'langgraph':'tool'}

/* ── render messages ───────────────────────────────────────────────── */
function renderMsgs(msgs){
  if(!Array.isArray(msgs)||!msgs.length)return'<em style="color:var(--muted)">none</em>';
  return msgs.map(m=>{
    const role=(m.role||'unknown').toLowerCase();
    let body='';
    if(typeof m.content==='string')body=esc(m.content);
    else if(Array.isArray(m.content))body=m.content.map(b=>{
      if(typeof b==='string')return esc(b);
      if(b.type==='text')return esc(b.text||'');
      if(b.type==='tool_result')return'[tool_result id='+esc(b.tool_use_id)+']';
      if(b.type==='tool_use')return'[tool_use: '+esc(b.name)+']';
      return esc(JSON.stringify(b));
    }).join('\n');
    else body=esc(JSON.stringify(m.content));
    return`<div class="msg"><div class="msg-role role-${role}">${role.toUpperCase()}</div><div class="msg-body">${body}</div></div>`;
  }).join('');
}

/* ── render span detail ────────────────────────────────────────────── */
function renderDetail(span){
  const t=span.type;let h='';
  if(t==='llm_call'){
    const msgs=span.input_messages||[];
    const sys=msgs.find(m=>m.role==='system');
    if(sys)h+=`<div class="dl"><div class="dl-lbl">System Prompt</div><div class="dl-val">${esc(typeof sys.content==='string'?sys.content:JSON.stringify(sys.content))}</div></div>`;
    const conv=msgs.filter(m=>m.role!=='system');
    if(conv.length)h+=`<div class="dl"><div class="dl-lbl">Conversation (${conv.length})</div>${renderMsgs(conv)}</div>`;
    const tools=span.tools||[];
    if(tools.length)h+=`<div class="dl"><div class="dl-lbl">Tools (${tools.length})</div><div class="tool-chips">${tools.map(t=>`<span class="chip">${esc(t.name||(t.function&&t.function.name)||'?')}</span>`).join('')}</div></div>`;
    if(span.response_content!=null)h+=`<div class="dl"><div class="dl-lbl">Response</div><div class="dl-val">${esc(cj(span.response_content,2000))}</div></div>`;
    const u=usage(span);if(u.tot>0){const rows=`input: ${u.i} tokens\noutput: ${u.o} tokens\ntotal: ${u.tot} tokens`+(span.cost_usd?`\ncost: ${cost(span.cost_usd)}`:'');h+=`<div class="dl"><div class="dl-lbl">Usage</div><div class="dl-val">${esc(rows)}</div></div>`;}
  }else if(t==='tool_call'){
    const isErr=span.output&&typeof span.output==='object'&&(span.output.status==='error'||span.output.error);
    if(span.input!=null)h+=`<div class="dl"><div class="dl-lbl">Input</div><div class="dl-val">${esc(cj(span.input,2000))}</div></div>`;
    if(span.output!=null)h+=`<div class="dl"><div class="dl-lbl">Output${isErr?' ⚠ error':''}</div><div class="dl-val${isErr?' err':''}">${esc(cj(span.output,2000))}</div></div>`;
    if(span.tool_use_id)h+=`<div class="dl"><div class="dl-lbl">Tool Use ID</div><div class="dl-val">${esc(span.tool_use_id)}</div></div>`;
  }else if(t==='error'){
    h+=`<div class="dl"><div class="dl-lbl">Error</div><div class="dl-val err">${esc(span.error||'unknown')}</div></div>`;
    if(span.context)h+=`<div class="dl"><div class="dl-lbl">Context</div><div class="dl-val">${esc(cj(span.context,2000))}</div></div>`;
  }else if(t==='memory_snapshot'){
    if(span.label)h+=`<div class="dl"><div class="dl-lbl">Label</div><div class="dl-val">${esc(span.label)}</div></div>`;
    h+=`<div class="dl"><div class="dl-lbl">Memory State</div><div class="dl-val">${esc(cj(span.state,3000))}</div></div>`;
  }else if(t==='langgraph_node'){
    h+=`<div class="dl"><div class="dl-lbl">Node</div><div class="dl-val">${esc(span.node_name||span.name||'?')}</div></div>`;
    if(span.input!=null)h+=`<div class="dl"><div class="dl-lbl">Input</div><div class="dl-val">${esc(cj(span.input,2000))}</div></div>`;
    if(span.output!=null)h+=`<div class="dl"><div class="dl-lbl">Output</div><div class="dl-val">${esc(cj(span.output,2000))}</div></div>`;
  }else{
    h+=`<div class="dl"><div class="dl-val">${esc(cj(span,3000))}</div></div>`;
  }
  return h;
}

/* ── render one timeline row ───────────────────────────────────────── */
function renderRow(span,i,maxLat){
  if(!span||typeof span!=='object')return'';
  const t=span.type||'unknown',cls=dotCls(t);
  let title=t,sub='';
  if(t==='llm_call'){title=span.model||'llm_call';sub=(span.provider||'')+(span.stop_reason?' · '+span.stop_reason:'');const u=usage(span);if(u.tot>0)sub+=' · '+u.tot.toLocaleString()+' tok';if(span.cost_usd>0)sub+=' · '+cost(span.cost_usd);}
  else if(t==='tool_call'){title=span.tool_name||'tool_call';const o=span.output;if(o&&typeof o==='object'&&(o.status==='error'||o.error))sub='⚠ error result';else if(o!=null)sub='returned result';}
  else if(t==='error'){title='error';sub=String(span.error||'').slice(0,80);}
  else if(t==='memory_snapshot'){title='memory snapshot';sub=span.label||'';}
  else if(t==='langgraph_node'){title=span.node_name||span.name||'langgraph node';sub=span.graph_id?'graph: '+span.graph_id:''}
  const lat=span.latency_ms||0;
  const pct=maxLat>0?Math.max(2,Math.round(lat/maxLat*100)):0;
  const barHtml=lat>0?`<div class="bar-wrap"><div class="bar-fill bar-${cls}" style="width:${pct}%"></div></div>`:'';
  return`<div class="span-row" onclick="toggle(this,${i})">
  <div class="span-main">
    <div class="dot dot-${cls}"></div>
    <div class="span-info">
      <div class="span-title"><span class="chevron">▶</span>${esc(title)}</div>
      ${sub?`<div class="span-sub">${esc(sub)}</div>`:''}
      ${barHtml}
    </div>
    <div class="span-right">${lat>0?`<div class="span-lat">${ms(lat)}</div>`:''}</div>
  </div>
  <div class="span-detail" id="d${i}">${renderDetail(span)}</div>
</div>`;
}

/* ── hallucination card ────────────────────────────────────────────── */
function renderHallucinations(run){
  const h=run.hallucinations||[];
  if(!h.length)return'';
  const sevColor={high:'var(--red)',medium:'var(--amber)',low:'var(--muted)'};
  const rows=h.map(ev=>{
    const sev=(ev.severity||'?').toLowerCase();
    const col=sevColor[sev]||'var(--muted)';
    return`<div class="pv-step" style="border-left:3px solid ${col}">
  <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:${col};margin-bottom:4px">${(ev.type||'').replace(/_/g,' ')} · step ${ev.step||'?'} · ${sev}</div>
  <div style="font-size:12px">${esc(ev.detail||'')}</div>
</div>`;
  }).join('');
  return`<div class="card">
  <div class="card-header toggle-section" onclick="toggleHall()"><span>⚠ Hallucinations Detected (${h.length})</span><span id="hall-chev" class="chevron" style="transform:rotate(90deg)">▶</span></div>
  <div id="hall-body">${rows}</div>
</div>`;
}

/* ── prompt viewer ─────────────────────────────────────────────────── */
function renderPromptViewer(spans){
  const llm=spans.filter(s=>s&&s.type==='llm_call');
  if(!llm.length)return'';
  const steps=llm.map((s,idx)=>{
    const msgs=s.input_messages||[];
    const tools=s.tools||[];
    return`<div class="pv-step">
  <div class="pv-step-hdr">Step ${idx+1} — ${esc(s.model||'llm_call')} (${esc(s.provider||'')})</div>
  ${renderMsgs(msgs)}
  ${tools.length?`<div style="margin-top:8px"><div class="dl-lbl">Tools available</div><div class="tool-chips">${tools.map(t=>`<span class="chip">${esc(t.name||(t.function&&t.function.name)||'?')}</span>`).join('')}</div></div>`:''}
</div>`;
  }).join('');
  return`<div class="card">
  <div class="card-header toggle-section" onclick="togglePV()"><span>LLM Prompt Viewer</span><span id="pv-chev" class="chevron" style="transform:rotate(90deg)">▶</span></div>
  <div id="pv-body">${steps}</div>
</div>`;
}

/* ── main render ───────────────────────────────────────────────────── */
function render(){
  const run=RUN;
  const spans=Array.isArray(run.spans)?run.spans:[];
  let llm=0,tool=0,errs=0,intok=0,outtok=0,costSum=0,latSum=0;
  let maxLat=0;
  for(const s of spans){
    if(!s||typeof s!=='object')continue;
    if(s.type==='llm_call'){llm++;const u=usage(s);intok+=u.i;outtok+=u.o;costSum+=(s.cost_usd||0);latSum+=(s.latency_ms||0);if((s.latency_ms||0)>maxLat)maxLat=s.latency_ms||0;}
    else if(s.type==='tool_call')tool++;
    else if(s.type==='error')errs++;
  }
  let dur=0;try{dur=Math.max(0,new Date(run.ended_at)-new Date(run.started_at));}catch{}
  const st=run.status||'unknown';
  const stCls={'success':'badge-success','error':'badge-error','running':'badge-running'}[st]||'badge-unknown';
  const stIcon={'success':'✓','error':'✗','running':'◌'}[st]||'?';
  const rows=spans.map((s,i)=>renderRow(s,i,maxLat)).join('');
  document.getElementById('root').innerHTML=`
<div class="card">
  <div class="run-header">
    <div class="run-name">${esc(run.name||'Unnamed Run')}<span class="status-badge ${stCls}">${stIcon} ${st}</span></div>
    <div class="run-meta">${esc(run.run_id||'')} · started ${esc((run.started_at||'').slice(0,19).replace('T',' '))} UTC${dur>0?' · '+ms(dur)+' duration':''}</div>
    <div class="stats-row">
      <div class="stat"><div class="stat-val c-blue">${llm}</div><div class="stat-lbl">LLM calls</div></div>
      <div class="stat"><div class="stat-val c-amber">${tool}</div><div class="stat-lbl">Tool calls</div></div>
      <div class="stat"><div class="stat-val${errs>0?' c-red':''}">${errs}</div><div class="stat-lbl">Errors</div></div>
      <div class="stat"><div class="stat-val">${intok.toLocaleString()}</div><div class="stat-lbl">Input tokens</div></div>
      <div class="stat"><div class="stat-val">${outtok.toLocaleString()}</div><div class="stat-lbl">Output tokens</div></div>
      ${costSum>0?`<div class="stat"><div class="stat-val c-green">${cost(costSum)}</div><div class="stat-lbl">Est. cost</div></div>`:''}
      ${latSum>0?`<div class="stat"><div class="stat-val">${ms(latSum)}</div><div class="stat-lbl">LLM latency</div></div>`:''}
    </div>
  </div>
</div>
<div class="card">
  <div class="card-header">Timeline — ${spans.length} span${spans.length!==1?'s':''}</div>
  ${rows||'<div style="padding:20px;color:var(--muted)">No spans captured.</div>'}
</div>
${renderHallucinations(run)}
${renderPromptViewer(spans)}
<footer>AgentLens · Generated ${new Date().toISOString().slice(0,19).replace('T',' ')} UTC</footer>`;
}

function toggle(row,i){
  row.classList.toggle('open');
  document.getElementById('d'+i).classList.toggle('open');
}

function toggleHall(){
  const body=document.getElementById('hall-body');
  const chev=document.getElementById('hall-chev');
  if(!body)return;
  const hidden=body.style.display==='none';
  body.style.display=hidden?'':'none';
  chev.style.transform=hidden?'rotate(90deg)':'';
}

function togglePV(){
  const body=document.getElementById('pv-body');
  const chev=document.getElementById('pv-chev');
  const hidden=body.style.display==='none';
  body.style.display=hidden?'':'none';
  chev.style.transform=hidden?'rotate(90deg)':'';
}

render();
</script>
</body>
</html>"""
