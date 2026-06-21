"""Self-contained modern trading dashboard (zero build) served at GET / by the API.

Vanilla HTML/CSS/JS — no Node, no bundler. It polls the same REST endpoints the backend
already exposes (/snapshot, /instruments, /accounts/...) and renders an order book, trade
tape, order ticket, positions and balance. Served same-origin, so fetch uses relative URLs.
"""

DASHBOARD_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Chronos Trade</title>
<style>
  :root{
    /* "Advanced Sense" palette */
    --bg:#1a2029; --panel:#252c38; --panel2:#2c3442; --line:#323a47; --txt:#e7eff6;
    --muted:#7e8ca1; --buy:#27b083; --sell:#e86349; --accent:#8fb9d1; --accent2:#213271;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);font:13px/1.45 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  header{display:flex;align-items:center;gap:16px;padding:10px 16px;background:var(--panel);border-bottom:1px solid var(--line)}
  header .brand{font-weight:700;letter-spacing:.5px}
  header .brand b{color:var(--accent)}
  header .last{font-size:20px;font-weight:700;margin-left:auto}
  header .spread{color:var(--muted);font-size:12px}
  select,input,button{background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:7px 9px;font:inherit;outline:none}
  button{cursor:pointer}
  button:hover{border-color:var(--accent)}
  .grid{display:grid;grid-template-columns:300px 1fr 360px;gap:12px;padding:12px;height:calc(100vh - 53px)}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;display:flex;flex-direction:column;overflow:hidden}
  .panel h3{margin:0;padding:10px 12px;font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);border-bottom:1px solid var(--line)}
  .panel .body{padding:12px;overflow:auto}
  .row{display:flex;gap:8px;margin-bottom:8px}
  .row > *{flex:1}
  label{display:block;color:var(--muted);font-size:11px;margin:6px 0 3px}
  .sidebtns{display:flex;gap:8px;margin-bottom:8px}
  .sidebtns button{flex:1;font-weight:700}
  .sidebtns .on.buy{background:var(--buy);border-color:var(--buy);color:#03130d}
  .sidebtns .on.sell{background:var(--sell);border-color:var(--sell);color:#160406}
  .place{width:100%;margin-top:10px;padding:11px;font-weight:700;border:none;color:#fff;background:var(--accent)}
  .place.buy{background:var(--buy);color:#03130d}.place.sell{background:var(--sell);color:#fff}
  table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
  th{color:var(--muted);font-weight:500;text-align:right;padding:4px 8px;font-size:11px}
  td{padding:3px 8px;text-align:right;position:relative;z-index:1}
  .book td.px{font-weight:600}
  .ask td.px{color:var(--sell)} .bid td.px{color:var(--buy)}
  .depth{position:absolute;top:0;bottom:0;right:0;z-index:-1;opacity:.16}
  .ask .depth{background:var(--sell)} .bid .depth{background:var(--buy)}
  .spreadrow td{color:var(--muted);text-align:center;background:var(--panel2);font-size:11px;padding:5px}
  .tape td.s-buy{color:var(--buy)} .tape td.s-sell{color:var(--sell)}
  .muted{color:var(--muted)}
  .kv{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--line)}
  .kv b{font-variant-numeric:tabular-nums}
  .pos-long{color:var(--buy)} .pos-short{color:var(--sell)}
  #toast{position:fixed;bottom:16px;right:16px;background:var(--panel2);border:1px solid var(--line);padding:10px 14px;border-radius:8px;opacity:0;transition:.3s;max-width:340px}
  #toast.show{opacity:1}
  .admin{display:flex;gap:6px;flex-wrap:wrap;align-items:flex-end}
  .admin > div{flex:1;min-width:90px}
  canvas{width:100%;height:120px;display:block}
  small.hint{color:var(--muted)}
</style>
</head>
<body>
<header>
  <div class="brand">CHRONOS<b> TRADE</b></div>
  <div><label>Symbol</label><select id="symbol"></select></div>
  <div><label>Account</label><input id="account" value="trader1" style="width:110px"/></div>
  <div class="last" id="last">--</div>
  <div class="spread" id="spread"></div>
</header>

<div class="grid">
  <!-- LEFT: ticket + admin -->
  <div class="panel">
    <h3>Order Ticket</h3>
    <div class="body">
      <div class="sidebtns">
        <button id="sideBuy" class="on buy" onclick="setSide('buy')">Buy</button>
        <button id="sideSell" class="sell" onclick="setSide('sell')">Sell</button>
      </div>
      <label>Order type</label>
      <select id="otype" onchange="syncTicket()">
        <option value="limit">Limit</option>
        <option value="market">Market</option>
        <option value="stop">Stop (market)</option>
        <option value="stop_limit">Stop limit</option>
      </select>
      <div class="row">
        <div><label>Quantity</label><input id="qty" type="number" value="10" step="any"/></div>
        <div id="priceWrap"><label>Limit price</label><input id="price" type="number" value="150.00" step="any"/></div>
      </div>
      <div class="row" id="stopWrap" style="display:none">
        <div><label>Stop price</label><input id="stop" type="number" value="150.00" step="any"/></div>
        <div><label>TIF</label><select id="tif"><option>gtc</option><option>ioc</option><option>fok</option></select></div>
      </div>
      <div id="tifWrap"><label>Time in force</label>
        <select id="tif2"><option>gtc</option><option>ioc</option><option>fok</option></select></div>
      <button id="place" class="place buy" onclick="placeOrder()">Place Buy Order</button>
      <div class="row" style="margin-top:10px">
        <div><label>Cancel order id</label><input id="cancelId" type="number" placeholder="id"/></div>
        <div style="flex:0 0 auto;align-self:flex-end"><button onclick="cancelOrder()">Cancel</button></div>
      </div>
      <h3 style="margin:14px -12px 8px;border-top:1px solid var(--line);border-bottom:none;padding-top:12px">Setup</h3>
      <div class="admin">
        <div><label>New equity</label><input id="newsym" placeholder="MSFT"/></div>
        <div style="flex:0 0 auto"><button onclick="addEquity()">Add</button></div>
      </div>
      <div class="admin" style="margin-top:8px">
        <div><label>Fund account ($)</label><input id="fundAmt" type="number" value="100000"/></div>
        <div style="flex:0 0 auto"><button onclick="fund()">Fund</button></div>
      </div>
      <small class="hint">Tip: add a symbol, fund your account, then place orders from two accounts to cross.</small>
    </div>
  </div>

  <!-- CENTER: book + chart -->
  <div class="panel">
    <h3>Order Book &middot; <span id="bookSym"></span></h3>
    <div class="body" style="flex:1">
      <table class="book"><thead><tr><th>Price</th><th>Qty</th><th>Total</th></tr></thead>
        <tbody id="asks"></tbody>
        <tbody id="spreadBody"></tbody>
        <tbody id="bids"></tbody>
      </table>
    </div>
    <h3>Price</h3>
    <div class="body" style="flex:0 0 auto"><canvas id="chart" width="600" height="120"></canvas></div>
  </div>

  <!-- RIGHT: tape + positions -->
  <div class="panel">
    <h3>Account</h3>
    <div class="body" style="flex:0 0 auto">
      <div class="kv"><span class="muted">Cash</span><b id="cash">--</b></div>
      <div class="kv"><span class="muted">Available</span><b id="avail">--</b></div>
      <div class="kv"><span class="muted">Reserved</span><b id="reserved">--</b></div>
    </div>
    <h3>Positions</h3>
    <div class="body" style="flex:1">
      <table><thead><tr><th style="text-align:left">Symbol</th><th>Qty</th><th>Cost</th><th>Realized</th></tr></thead>
        <tbody id="positions"></tbody></table>
    </div>
    <h3>Time &amp; Sales</h3>
    <div class="body" style="flex:1">
      <table class="tape"><thead><tr><th>#</th><th>Price</th><th>Qty</th></tr></thead>
        <tbody id="tape"></tbody></table>
    </div>
  </div>
</div>
<div id="toast"></div>

<script>
const $ = id => document.getElementById(id);
let side = 'buy';
let priceHist = [];

async function api(method, path, body){
  const opt = {method, headers:{}};
  if(body!==undefined){ opt.headers['Content-Type']='application/json'; opt.body=JSON.stringify(body); }
  const r = await fetch(path, opt);
  const data = await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(data.error || ('HTTP '+r.status));
  return data;
}
function toast(msg, ok=true){ const t=$('toast'); t.textContent=msg; t.style.borderColor= ok?'var(--buy)':'var(--sell)'; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2600); }
function fmt(n,d=2){ return (n==null)?'--':Number(n).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d}); }

function setSide(s){ side=s; $('sideBuy').className=(s==='buy'?'on buy':'buy'); $('sideSell').className=(s==='sell'?'on sell':'sell');
  const b=$('place'); b.className='place '+s; b.textContent='Place '+(s==='buy'?'Buy':'Sell')+' Order'; }
function syncTicket(){ const t=$('otype').value;
  $('priceWrap').style.display=(t==='market'||t==='stop')?'none':'block';
  $('stopWrap').style.display=(t==='stop'||t==='stop_limit')?'flex':'none';
  $('tifWrap').style.display=(t==='limit')?'block':'none';
}

async function loadInstruments(){
  const {instruments} = await api('GET','/instruments');
  const sel=$('symbol'); const cur=sel.value;
  sel.innerHTML = instruments.map(i=>`<option value="${i.symbol}">${i.symbol}${i.kind==='option'?' (opt)':''}</option>`).join('');
  if(cur) sel.value=cur;
  if(!sel.value && instruments[0]) sel.value=instruments[0].symbol;
}
async function addEquity(){ const s=$('newsym').value.trim().toUpperCase(); if(!s) return;
  try{ await api('POST','/instruments/equity',{symbol:s}); $('newsym').value=''; await loadInstruments(); $('symbol').value=s; toast('Added '+s);}catch(e){toast(e.message,false);} }
async function fund(){ try{ const a=$('account').value; await api('POST',`/accounts/${a}/fund`,{amount:Number($('fundAmt').value)}); toast('Funded '+a);}catch(e){toast(e.message,false);} }

async function placeOrder(){
  try{
    const t=$('otype').value;
    const body={account:$('account').value, symbol:$('symbol').value, side, quantity:Number($('qty').value), order_type:t};
    if(t==='limit'||t==='stop_limit') body.price=Number($('price').value);
    if(t==='stop'||t==='stop_limit') body.stop_price=Number($('stop').value);
    body.tif = (t==='limit')? $('tif2').value : (t==='stop_limit'? $('tif').value : 'gtc');
    const o=await api('POST','/orders',body);
    toast(`#${o.id} ${o.side} ${o.symbol} → ${o.status}`+(o.reject_reason?(': '+o.reject_reason):''), o.status!=='rejected');
    refresh();
  }catch(e){ toast(e.message,false); }
}
async function cancelOrder(){ const id=$('cancelId').value; if(!id) return;
  try{ const o=await api('DELETE','/orders/'+id); toast(`#${o.id} → ${o.status}`); refresh(); }catch(e){toast(e.message,false);} }

function renderBook(snap){
  const rows = (arr, cls)=>{ let cum=0; const max=arr.reduce((a,l)=>a+l.quantity,0)||1;
    return arr.map(l=>{ cum+=l.quantity; const w=(cum/max*100).toFixed(1);
      return `<tr class="${cls}"><td class="px">${fmt(l.price)}</td><td>${fmt(l.quantity,3)}</td><td class="muted">${fmt(cum,3)}<span class="depth" style="width:${w}%"></span></td></tr>`;
    }).join(''); };
  // asks shown high->low so best ask sits just above the spread
  const asks=[...snap.asks].slice(0,12).reverse();
  $('asks').innerHTML = rows(asks,'ask');
  $('bids').innerHTML = rows(snap.bids.slice(0,12),'bid');
  const sp = (snap.best_bid!=null&&snap.best_ask!=null)? (snap.best_ask-snap.best_bid):null;
  $('spreadBody').innerHTML = `<tr class="spreadrow"><td colspan="3">spread ${sp==null?'--':fmt(sp)} &middot; last ${fmt(snap.last)}</td></tr>`;
}
function renderTape(snap){
  $('tape').innerHTML = [...snap.trades].reverse().map(t=>`<tr><td class="muted">${t.seq}</td><td>${fmt(t.price)}</td><td>${fmt(t.quantity,3)}</td></tr>`).join('');
}
function drawChart(){
  const c=$('chart'), ctx=c.getContext('2d'); const W=c.width,H=c.height; ctx.clearRect(0,0,W,H);
  if(priceHist.length<2) return;
  const min=Math.min(...priceHist), max=Math.max(...priceHist), rng=(max-min)||1;
  ctx.strokeStyle='#8fb9d1'; ctx.lineWidth=2; ctx.beginPath();
  priceHist.forEach((p,i)=>{ const x=i/(priceHist.length-1)*W; const y=H-((p-min)/rng)*(H-12)-6; i?ctx.lineTo(x,y):ctx.moveTo(x,y); });
  ctx.stroke();
}

async function refresh(){
  const sym=$('symbol').value, acct=$('account').value; if(!sym) return;
  $('bookSym').textContent=sym;
  try{
    const snap=await api('GET','/snapshot/'+sym);
    $('last').textContent=fmt(snap.last); $('last').style.color = snap.last!=null?'#fff':'var(--muted)';
    $('spread').textContent = (snap.best_bid!=null?('bid '+fmt(snap.best_bid)):'') + (snap.best_ask!=null?(' / ask '+fmt(snap.best_ask)):'');
    renderBook(snap); renderTape(snap);
    if(snap.last!=null){ priceHist.push(snap.last); if(priceHist.length>120) priceHist.shift(); drawChart(); }
    const bal=await api('GET',`/accounts/${acct}/balance`);
    $('cash').textContent='$'+fmt(bal.cash); $('avail').textContent='$'+fmt(bal.available); $('reserved').textContent='$'+fmt(bal.reserved);
    const {positions}=await api('GET',`/accounts/${acct}/positions`);
    $('positions').innerHTML = positions.length? positions.map(p=>{ const cls=p.quantity>0?'pos-long':(p.quantity<0?'pos-short':'');
      return `<tr><td style="text-align:left">${p.symbol}</td><td class="${cls}">${fmt(p.quantity,3)}</td><td class="muted">$${fmt(p.cost_basis)}</td><td>$${fmt(p.realized_pnl)}</td></tr>`;}).join('')
      : '<tr><td colspan="4" class="muted" style="text-align:left">No positions</td></tr>';
  }catch(e){ /* symbol may not exist yet */ }
}

$('symbol').addEventListener('change',()=>{priceHist=[];refresh();});
$('account').addEventListener('change',refresh);
syncTicket(); loadInstruments().then(refresh);
setInterval(refresh, 1000);
setInterval(loadInstruments, 5000);
// Instant updates via Server-Sent Events (polling above remains a fallback).
try{ const es=new EventSource('/stream'); es.onmessage=(e)=>{ try{ const ev=JSON.parse(e.data); if(!ev.symbol||ev.symbol===$('symbol').value) refresh(); }catch(_){} }; }catch(_){}
</script>
</body>
</html>
'''
