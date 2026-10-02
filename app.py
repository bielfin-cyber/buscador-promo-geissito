from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from core import OfferIndex, SourceError, brl

INDEX = OfferIndex(ttl_seconds=900)

HTML = r'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Buscador Promo do Geissito</title>
<style>
:root{--blue:#0797d5;--green:#22b967;--red:#e53945;--ink:#14213d;--muted:#5c7082;--line:#dceaf1}*{box-sizing:border-box}body{margin:0;background:#f7fbfd;color:var(--ink);font-family:Segoe UI,Arial,sans-serif}header{background:linear-gradient(135deg,#067fb7,#11a8dd 55%,#20b96b);color:#fff;padding:42px 20px 70px;text-align:center}header h1{font-size:clamp(2rem,6vw,4rem);margin:0 0 10px;letter-spacing:-.04em}header p{margin:0;font-size:1.08rem}main{max-width:1180px;margin:-38px auto 40px;padding:0 20px}.searchbox{display:flex;gap:12px;background:#fff;border:1px solid var(--line);padding:14px;border-radius:18px;box-shadow:0 14px 40px #08334b1c}input{flex:1;border:0;outline:0;font-size:1.08rem;padding:14px;min-width:0}button{border:0;border-radius:12px;background:var(--ink);color:#fff;font-weight:800;padding:0 26px;cursor:pointer;font-size:1rem}button:disabled{opacity:.6;cursor:wait}.examples{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:18px 0 8px}.chip{border:1px solid #b9dce9;background:#fff;color:#25627c;padding:8px 13px;border-radius:999px;cursor:pointer}#status{text-align:center;color:var(--muted);min-height:28px;margin:18px 0;font-weight:600}.loading{display:inline-flex;align-items:center;gap:10px}.spinner{width:20px;height:20px;border:3px solid #cde6ef;border-top-color:var(--blue);border-radius:50%;animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px}article{background:#fff;border:1px solid var(--line);border-radius:18px;overflow:hidden;box-shadow:0 8px 28px #15384b12;display:flex;flex-direction:column;min-height:430px}.photo{height:220px;display:grid;place-items:center;position:relative;padding:14px}.photo img{max-width:100%;max-height:100%;object-fit:contain}.discount{position:absolute;right:12px;top:12px;background:var(--red);color:#fff;padding:7px 10px;border-radius:999px;font-weight:900}.content{padding:17px;display:flex;flex:1;flex-direction:column}.store{color:var(--blue);font-size:.78rem;text-transform:uppercase;font-weight:900;letter-spacing:.05em}h2{font-size:1rem;line-height:1.4;margin:8px 0 16px}.prices{margin-top:auto}.old{text-decoration:line-through;color:#83919c;font-size:.9rem}.price{display:block;color:var(--red);font-size:1.55rem;font-weight:900;margin-top:3px}.coupon{background:#fff1c8;padding:7px 9px;border-radius:8px;font-weight:800;font-size:.84rem;margin-top:8px}.cta{display:block;text-align:center;color:#fff;background:linear-gradient(135deg,var(--blue),var(--green));font-weight:900;text-decoration:none;border-radius:11px;padding:13px;margin-top:14px}.empty,.error{background:#fff;border:1px solid var(--line);padding:30px;border-radius:16px;text-align:center}.error{color:#a11d2a;border-color:#f1b9be;background:#fff5f6}footer{text-align:center;color:var(--muted);padding:30px 15px 45px}footer b{color:var(--ink)}@media(max-width:600px){header{padding-top:30px}.searchbox{flex-direction:column}button{height:50px}.grid{grid-template-columns:1fr}main{padding:0 12px}}
</style></head><body><header><h1>🔎 Promo do Geissito</h1><p>Encontre as melhores ofertas publicadas no seu site</p></header><main><form class="searchbox" id="form"><input id="query" autofocus placeholder="O que você procura? Ex.: air fryer" autocomplete="off"><button id="search">Buscar ofertas</button></form><div class="examples"><span class="chip" data-q="air fryer">Air fryer</span><span class="chip" data-q="TV 50">TV 50</span><span class="chip" data-q="tênis masculino">Tênis masculino</span></div><div id="status">Digite um produto ou escolha um exemplo acima.</div><section id="results"></section></main><footer>Preços e disponibilidade podem mudar a qualquer momento.<br><br><b>Promo do Geissito: achou promoção, achou economia!</b></footer>
<script>
const form=document.querySelector('#form'),input=document.querySelector('#query'),button=document.querySelector('#search'),status=document.querySelector('#status'),results=document.querySelector('#results');const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));async function search(q){q=(q||'').trim();if(q.length<2){status.textContent='Digite pelo menos 2 caracteres.';return}input.value=q;button.disabled=true;results.innerHTML='';status.innerHTML='<span class="loading"><span class="spinner"></span>Consultando as ofertas. Na primeira busca, aguarde alguns segundos…</span>';try{const r=await fetch('/api/search?q='+encodeURIComponent(q));const d=await r.json();if(!r.ok)throw new Error(d.error||'Falha na busca');status.textContent=`${d.count} resultado(s) encontrado(s) em ${d.indexed} ofertas válidas.`;if(!d.offers.length){results.innerHTML='<div class="empty">Nenhuma oferta correspondente foi encontrada agora.</div>';return}results.innerHTML='<div class="grid">'+d.offers.map(o=>`<article><div class="photo">${o.image?`<img src="${esc(o.image)}" alt="">`:''}${o.discount?`<span class="discount">-${o.discount}%</span>`:''}</div><div class="content"><span class="store">${esc(o.store)}</span><h2>${esc(o.title)}</h2><div class="prices">${o.old_price?`<span class="old">De ${esc(o.old_price)}</span>`:''}<span class="price">${esc(o.price)}</span>${o.coupon?`<div class="coupon">Cupom: ${esc(o.coupon)}</div>`:''}</div><a class="cta" href="${esc(o.url)}" target="_blank" rel="noopener sponsored nofollow">Ver promoção</a></div></article>`).join('')+'</div>'}catch(e){status.textContent='';results.innerHTML=`<div class="error"><b>Não foi possível carregar as ofertas.</b><br>${esc(e.message)}<br><br>Tente novamente.</div>`}finally{button.disabled=false}}form.addEventListener('submit',e=>{e.preventDefault();search(input.value)});document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>search(c.dataset.q)));
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/": self.send_bytes(HTML.encode(), "text/html; charset=utf-8"); return
        if parsed.path == "/api/search":
            query = (parse_qs(parsed.query).get("q") or [""])[0].strip()
            try:
                offers, stats = INDEX.search(query, limit=24)
                data = {"count": len(offers), "indexed": stats.get("accepted", 0), "offers": [{"title": o.title, "store": o.store, "price": brl(o.price), "old_price": brl(o.old_price) if o.old_price else None, "discount": o.discount, "coupon": o.coupon, "image": o.image, "url": o.affiliate_url} for o in offers]}
                self.send_bytes(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            except SourceError as exc: self.send_bytes(json.dumps({"error": str(exc)}, ensure_ascii=False).encode(), "application/json; charset=utf-8", 502)
            return
        self.send_bytes(b"Not found", "text/plain", 404)

    def log_message(self, format: str, *args) -> None: return


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__)); pid_path = os.path.join(root, ".promo.pid")
    with open(pid_path, "w", encoding="ascii") as f: f.write(str(os.getpid()))
    server = ThreadingHTTPServer((os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", "7860"))), Handler)
    threading.Thread(target=lambda: INDEX.refresh(), daemon=True).start()
    try: server.serve_forever()
    finally:
        server.server_close()
        try: os.remove(pid_path)
        except OSError: pass
