from __future__ import annotations

import hashlib
import hmac
import html
import json
import re
import secrets
import select
import shutil
import subprocess
import threading
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse, urlsplit

import httpx

from app import captcha, env_manager, storage
from app.handlers import resolve_cached_file, resolve_redirect
from app.settings import settings

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
_REFERER = "https://www.teraboxdl.site/"
_UPSTREAM_HEADERS = {"user-agent": _UA, "referer": _REFERER}
_TIMEOUT = httpx.Timeout(None, connect=20.0)

def _headers_for(url: str) -> tuple[str, str]:
    """Returns (user_agent, referer) tuned to the upstream host."""
    host = (urlparse(url).hostname or "").lower()
    if "fzcdn.cloud" in host or "flezen" in host:
        return _UA, "https://flezen-downloader.pages.dev/"
    if "diskwala" in host:
        return _UA, "https://miniapp.diskwala.net/"
    if "vidbunker" in host:
        return _UA, "https://vidbunker-ma.pages.dev/"
    if "upfiles" in host:
        return _UA, "https://upfiles.com/"
    if any(
        part in host
        for part in (
            "terabox",
            "teraboxpage",
            "4funbox",
            "nephobox",
            "momerybox",
            "gibibox",
            "workers.dev",
        )
    ):
        return _UA, "https://www.terabox.com/"
    return _UA, _REFERER


def _request_headers(
    url: str,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    ua, ref = _headers_for(url)
    headers = {"user-agent": ua, "referer": ref}
    for key, value in (extra or {}).items():
        if value:
            headers[key.lower()] = str(value)
    return headers

_CAPTCHA_PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Verifying…</title><style>  * { box-sizing: border-box; margin: 0; padding: 0; }  body { background: #0b0d12; color: #eaeaea;         font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;         display: flex; flex-direction: column; align-items: center; justify-content: center;         min-height: 100vh; padding: 24px; }  .card { background: #151821; border: 1px solid #23262f; border-radius: 16px;          padding: 32px 28px; max-width: 420px; width: 100%; text-align: center;          box-shadow: 0 8px 32px rgba(0,0,0,.4); }  h1 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }  p { color: #8a8f98; font-size: 14px; line-height: 1.5; margin-bottom: 20px; }  .spinner { width: 40px; height: 40px; border: 3px solid #23262f;             border-top-color: #5b8cff; border-radius: 50%;             animation: spin .8s linear infinite; margin: 0 auto 20px; }  @keyframes spin { to { transform: rotate(360deg); } }  .progress { background: #23262f; border-radius: 8px; height: 6px; overflow: hidden; margin-top: 12px; }  .bar { background: linear-gradient(90deg, #5b8cff, #8b5cf6); height: 100%; width: 0%; transition: width .2s; }  .status { color: #6b7280; font-size: 12px; margin-top: 12px; min-height: 16px; }  .err { color: #ff6b6b; font-size: 13px; margin-top: 12px; display: none; }  button { margin-top: 20px; padding: 12px 28px; border-radius: 10px; border: none;           background: #5b8cff; color: #fff; font-weight: 600; font-size: 15px;           cursor: pointer; display: none; }</style><script src="https://cdnjs.cloudflare.com/ajax/libs/js-sha256/0.9.0/sha256.min.js"></script></head><body><div class="card">  <div class="spinner" id="spin"></div>  <h1>Verifying your browser…</h1>  <p>Solving a quick proof-of-work challenge to keep this service safe.</p>  <div class="progress"><div class="bar" id="bar"></div></div>  <div class="status" id="status">Starting…</div>  <div class="err" id="err"></div>  <button id="go" style="display:none">Continue</button></div><script>const NEXT_URL = "__NEXT_URL__";const statusEl = document.getElementById('status');const barEl = document.getElementById('bar');const errEl = document.getElementById('err');const goBtn = document.getElementById('go');function fail(msg) {  errEl.textContent = msg;  errEl.style.display = 'block';  document.getElementById('spin').style.display = 'none';}async function sha256Hex(bytes){return sha256(bytes)}async function solveOne(salt, difficulty) {  const target = '0'.repeat(difficulty);  const enc = new TextEncoder();  for (let n = 0; n < 5_000_000; n++) {    const hex = await sha256Hex(enc.encode(salt + n));    if (hex.startsWith(target)) return n;  }  throw new Error('no solution found');}async function run() {    let data;  try {    const res = await fetch('/_cap/challenge', { cache: 'no-store' });    if (!res.ok) throw new Error('HTTP ' + res.status);    data = await res.json();    if (!data || !Array.isArray(data.challenges) || data.challenges.length === 0) {      throw new Error('invalid challenge response');    }  } catch (e) {    fail('Could not start verification: ' + e.message);    return;  }  const total = data.challenges.length;  const solutions = [];  for (let i = 0; i < total; i++) {    const ch = data.challenges[i];    statusEl.textContent = `Solving ${i+1} / ${total}…`;    try {      const sol = await solveOne(ch.salt, ch.difficulty);      solutions.push(sol);    } catch (e) {      fail('Challenge solving failed: ' + e.message);      return;    }    barEl.style.width = ((i+1) / total * 100).toFixed(0) + '%';  }  statusEl.textContent = 'Verifying with server…';  let vtoken = null;  try {    const verify = await fetch('/_cap/redeem', {      method: 'POST',      headers: { 'content-type': 'application/json' },      body: JSON.stringify({ token: data.token, solutions }),    });    const out = await verify.json();    vtoken = out && out.token;  } catch (e) {    fail('Verification request failed: ' + e.message);    return;  }  if (!vtoken) {    fail('Server rejected the proof-of-work. Please reload.');    return;  }  document.cookie = 'cap_token=' + vtoken + '; path=/; max-age=300; SameSite=Lax';  statusEl.textContent = 'Verified. Redirecting…';  document.getElementById('spin').style.display = 'none';  barEl.style.width = '100%';  // Auto-redirect after a short delay so the user sees "Verified".  setTimeout(() => { window.location.href = NEXT_URL; }, 250);  goBtn.style.display = 'inline-block';  goBtn.onclick = () => { window.location.href = NEXT_URL; };}run();</script></body></html>"""

_CAPTCHA_PAGE_V2 = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Verifying…</title><style>*{box-sizing:border-box}body{background:#0b0d12;color:#eaeaea;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}.card{background:#151821;border:1px solid #2b3040;border-radius:16px;padding:32px 28px;max-width:420px;width:100%;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,.4)}h1{font-size:18px;font-weight:600;margin:0 0 8px}.copy{color:#8a8f98;font-size:14px;line-height:1.5;margin:0 0 20px}.spinner{width:40px;height:40px;border:3px solid #23262f;border-top-color:#5b8cff;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 20px}@keyframes spin{to{transform:rotate(360deg)}}.progress{background:#23262f;border-radius:8px;height:6px;overflow:hidden;margin-top:12px}.bar{background:linear-gradient(90deg,#5b8cff,#8b5cf6);height:100%;width:0;transition:width .2s}.status{color:#9aa1ad;font-size:12px;margin-top:12px;min-height:16px}.err{color:#ff8b8b;font-size:13px;line-height:1.45;margin-top:12px;display:none}button{margin-top:20px;padding:12px 28px;border-radius:10px;border:0;background:#5b8cff;color:#fff;font-weight:600;font-size:15px;cursor:pointer;display:none}</style><script src="https://cdnjs.cloudflare.com/ajax/libs/js-sha256/0.9.0/sha256.min.js"></script></head><body><div class="card"><div class="spinner" id="spin"></div><h1>Verifying your browser…</h1><p class="copy">Solving a quick proof-of-work challenge to keep this service safe.</p><div class="progress"><div class="bar" id="bar"></div></div><div class="status" id="status">Starting…</div><div class="err" id="err"></div><button id="go">Continue</button></div><script>const NEXT_URL="__NEXT_URL__";const CHALLENGE_URL="__CHALLENGE_URL__";const REDEEM_URL="__REDEEM_URL__";const statusEl=document.getElementById("status"),barEl=document.getElementById("bar"),errEl=document.getElementById("err"),goBtn=document.getElementById("go");function fail(msg){document.getElementById("spin").style.display="none";errEl.textContent=msg;errEl.style.display="block";goBtn.style.display="inline-block";goBtn.onclick=()=>{window.location.href=NEXT_URL}}async function fetchJson(url,options){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);try{const res=await fetch(url,{...options,cache:"no-store",credentials:"same-origin",signal:controller.signal});if(!res.ok)throw new Error("HTTP "+res.status);return await res.json()}finally{clearTimeout(timer)}}async function sha256Hex(bytes){return sha256(bytes)}async function solveOne(salt,difficulty){const target="0".repeat(difficulty),enc=new TextEncoder();for(let n=0;n<5000000;n++){if((await sha256Hex(enc.encode(salt+n))).startsWith(target))return n}throw new Error("no solution found")}async function run(){try{const data=await fetchJson(CHALLENGE_URL),solutions=[];if(!data||!Array.isArray(data.challenges)||!data.challenges.length)throw new Error("invalid challenge response");for(let i=0;i<data.challenges.length;i++){statusEl.textContent="Solving "+(i+1)+" / "+data.challenges.length+"…";solutions.push(await solveOne(data.challenges[i].salt,data.challenges[i].difficulty));barEl.style.width=((i+1)/data.challenges.length*100).toFixed(0)+"%"}statusEl.textContent="Verifying with server…";const out=await fetchJson(REDEEM_URL,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({token:data.token,solutions})});if(!out||!out.token)throw new Error("server rejected the proof-of-work");document.cookie="cap_token="+encodeURIComponent(out.token)+"; path=/; max-age=300; SameSite=Lax";statusEl.textContent="Verified. Redirecting…";barEl.style.width="100%";document.getElementById("spin").style.display="none";setTimeout(()=>{window.location.href=NEXT_URL},250)}catch(err){fail(err&&err.name==="AbortError"?"The verification server did not respond in time. Please reload.":"Verification failed: "+(err.message||"unknown error"))}}run();</script></body></html>"""

_STREAM_BODY = '<section class="player-shell">\n  <div class="player-top"><span class="live-dot"></span><span>secure stream</span><span class="quality" id="qtag">browser playback</span></div>\n  <div class="player-wrap">\n    <video id="player" controls playsinline webkit-playsinline preload="auto" poster="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'1200\' height=\'675\' viewBox=\'0 0 1200 675\'%3E%3Cdefs%3E%3ClinearGradient id=\'g\' x1=\'0\' y1=\'0\' x2=\'1\' y2=\'1\'%3E%3Cstop stop-color=\'%23121c38\'/%3E%3Cstop offset=\'1\' stop-color=\'%233b176d\'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width=\'1200\' height=\'675\' fill=\'url(%23g)\'/%3E%3Ccircle cx=\'600\' cy=\'337\' r=\'72\' fill=\'%23ffffff\' fill-opacity=\'.12\'/%3E%3Cpath d=\'M580 292l70 45-70 45z\' fill=\'%23fff\'/%3E%3C/svg%3E"></video>\n    <div class="player-loading" id="load"><div class="spin"></div><span>starting playback…</span></div>\n    <div class="player-error" id="err">\n      <div class="error-icon">!</div><strong>this stream could not start</strong>\n      <span data-msg>the source may be temporarily busy. retry, use remux, or download directly.</span>\n      <div class="err-actions">\n        <button class="button secondary" id="retry" type="button">retry playback</button>\n        <button class="button secondary" id="remuxbtn" type="button">try remux</button>\n        <a class="button secondary" href="__DIRECT__">open direct download</a>\n      </div>\n    </div>\n  </div>\n</section>\n<div class="hint">hls, mp4, mkv and ts sources play in this page. seeking works on native files; live remux starts as soon as the first fragment arrives.</div>\n<script src="https://cdnjs.cloudflare.com/ajax/libs/hls.js/1.5.17/hls.min.js" crossorigin="anonymous"></script>\n<script>\n(function(){\n  const SRC="__SRC__";\n  const REMUX="__REMUX__";\n  const KIND="__KIND__";\n  const video=document.getElementById("player");\n  const err=document.getElementById("err");\n  const load=document.getElementById("load");\n  const qtag=document.getElementById("qtag");\n  let hlsObj=null, triedRemux=false;\n\n  function hideLoad(){ if(load) load.style.display="none"; }\n  function showLoad(text){\n    if(!load) return;\n    load.style.display="flex";\n    const span=load.querySelector("span");\n    if(span && text) span.textContent=text;\n    err.classList.remove("visible");\n    video.style.display="block";\n  }\n  function showErr(msg){\n    hideLoad();\n    const s=err.querySelector("[data-msg]");\n    if(s && msg) s.textContent=msg;\n    err.classList.add("visible");\n    video.style.display="none";\n  }\n  function setTag(t){ if(qtag) qtag.textContent=t; }\n  function destroyHls(){\n    if(!hlsObj) return;\n    try{ hlsObj.destroy(); }catch(e){}\n    hlsObj=null;\n  }\n  function playNative(url){\n    destroyHls();\n    try{ video.pause(); }catch(e){}\n    video.removeAttribute("src");\n    video.src=url;\n    video.load();\n    const p=video.play();\n    if(p && p.catch) p.catch(function(){});\n  }\n  function playHls(url){\n    destroyHls();\n    if(window.Hls && Hls.isSupported()){\n      setTag("hls.js");\n      hlsObj=new Hls({\n        enableWorker:true,\n        lowLatencyMode:false,\n        backBufferLength:30,\n        maxBufferLength:45,\n        maxMaxBufferLength:90,\n        maxBufferHole:1.5,\n        capLevelToPlayerSize:true,\n        fragLoadingTimeOut:30000,\n        manifestLoadingTimeOut:30000,\n        levelLoadingTimeOut:20000,\n        fragLoadingMaxRetry:8,\n        manifestLoadingMaxRetry:6,\n        startPosition:-1\n      });\n      hlsObj.loadSource(url);\n      hlsObj.attachMedia(video);\n      hlsObj.on(Hls.Events.MANIFEST_PARSED, function(){\n        hideLoad();\n        video.play().catch(function(){});\n      });\n      hlsObj.on(Hls.Events.ERROR, function(_, data){\n        if(!data || !data.fatal) return;\n        if(data.type===Hls.ErrorTypes.NETWORK_ERROR){\n          try{ hlsObj.startLoad(); return; }catch(e){}\n        }\n        if(data.type===Hls.ErrorTypes.MEDIA_ERROR){\n          try{ hlsObj.recoverMediaError(); return; }catch(e){}\n        }\n        fallbackRemux("hls decode failed, switching to remux…");\n      });\n      return;\n    }\n    if(video.canPlayType("application/vnd.apple.mpegurl") || video.canPlayType("application/x-mpegURL")){\n      setTag("native hls");\n      playNative(url);\n      return;\n    }\n    fallbackRemux("this browser needs remux for hls…");\n  }\n  function fallbackRemux(msg){\n    if(triedRemux){ showErr(msg || "this stream could not start"); return; }\n    triedRemux=true;\n    showLoad("remuxing for this browser…");\n    setTag("ffmpeg remux");\n    playNative(REMUX);\n  }\n  function detectAndPlay(){\n    showLoad("starting playback…");\n    if(KIND==="hls"){ playHls(SRC); return; }\n    if(KIND==="mp4" || KIND==="webm" || KIND==="audio"){ setTag(KIND+" native"); playNative(SRC); return; }\n    if(KIND==="mkv" || KIND==="ts" || KIND==="avi"){ fallbackRemux(); return; }\n    const ctrl=new AbortController();\n    const timer=setTimeout(function(){ ctrl.abort(); }, 8000);\n    fetch(SRC, {method:"GET", headers:{Range:"bytes=0-80"}, cache:"no-store", signal:ctrl.signal})\n      .then(function(r){\n        clearTimeout(timer);\n        const ct=(r.headers.get("content-type")||"").toLowerCase();\n        return r.arrayBuffer().then(function(buf){\n          const head=new TextDecoder("utf-8",{fatal:false}).decode(buf).trim();\n          if(ct.indexOf("mpegurl")>=0 || head.indexOf("#EXTM3U")===0) playHls(SRC);\n          else { setTag("native"); playNative(SRC); }\n        });\n      })\n      .catch(function(){\n        clearTimeout(timer);\n        if(window.Hls && Hls.isSupported()) playHls(SRC);\n        else playNative(SRC);\n      });\n  }\n  video.addEventListener("playing", hideLoad);\n  video.addEventListener("canplay", hideLoad);\n  video.addEventListener("error", function(){\n    if(triedRemux){ showErr("the source is not playable in this browser"); return; }\n    fallbackRemux("native playback failed, trying remux…");\n  });\n  document.getElementById("retry").onclick=function(){\n    triedRemux=false;\n    detectAndPlay();\n  };\n  document.getElementById("remuxbtn").onclick=function(){\n    triedRemux=false;\n    fallbackRemux();\n  };\n  function boot(){\n    if(KIND==="hls" && !(window.Hls || (video.canPlayType && video.canPlayType("application/vnd.apple.mpegurl")))){\n      var n=0, t=setInterval(function(){\n        n++;\n        if(window.Hls || n>50){ clearInterval(t); detectAndPlay(); }\n      }, 100);\n      return;\n    }\n    detectAndPlay();\n  }\n  boot();\n})();\n</script>\n'

_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme:dark; --bg:#070a14; --card:#10162a; --line:#24304d;
          --muted:#8c98b3; --text:#f8fbff; --blue:#62a8ff; --violet:#a879ff; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { min-height:100vh; padding:28px 16px 44px; color:var(--text);
         background:radial-gradient(circle at 15% 0%,#162951 0,#070a14 43%,#05060c 100%);
         font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
         display:flex; flex-direction:column; align-items:center; }
  .wrap { width:min(960px,100%); }
  .brand { display:flex; align-items:center; gap:10px; color:var(--muted); font-size:12px;
           letter-spacing:.14em; text-transform:uppercase; margin-bottom:22px; }
  .brand-mark { display:grid; place-items:center; width:30px; height:30px; border-radius:10px;
                background:linear-gradient(135deg,var(--blue),var(--violet)); color:#fff; font-weight:900; }
  .card { background:linear-gradient(180deg,rgba(20,29,53,.94),rgba(11,16,31,.96));
          border:1px solid rgba(137,163,218,.2); border-radius:24px; padding:clamp(18px,4vw,34px);
          box-shadow:0 24px 70px rgba(0,0,0,.35); }
  .eyebrow { color:var(--blue); font-size:11px; letter-spacing:.16em; text-transform:uppercase;
             font-weight:800; margin-bottom:10px; }
  h1 { font-size:clamp(18px,3vw,27px); line-height:1.18; font-weight:760;
       word-break:break-word; margin-bottom:8px; }
  .sub { color:var(--muted); font-size:13px; line-height:1.55; }
  .player-shell { margin-top:24px; overflow:hidden; border:1px solid var(--line);
                  border-radius:18px; background:#03050a; }
  .player-top { display:flex; gap:8px; align-items:center; padding:11px 14px; color:#b8c5e1;
                font-size:11px; letter-spacing:.1em; text-transform:uppercase; background:#0c1222; }
  .live-dot { width:7px; height:7px; border-radius:50%; background:#55e4a4; box-shadow:0 0 12px #55e4a4; }
  .quality { margin-left:auto; color:#71809f; }
  video { width:100%; aspect-ratio:16/9; display:block; background:#000; }
  .player-wrap { position:relative; background:#000; }
  .player-loading { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
                    flex-direction:column; gap:10px; background:rgba(3,5,10,.72); color:#8c98b3; font-size:13px; }
  .player-loading .spin { width:36px; height:36px; border:3px solid #23262f; border-top-color:#62a8ff;
                          border-radius:50%; animation:tdspin .8s linear infinite; }
  @keyframes tdspin { to { transform:rotate(360deg); } }
  .player-error { display:none; min-height:300px; padding:42px 24px; align-items:center; justify-content:center;
                  flex-direction:column; gap:10px; color:#ffb4bb; text-align:center; }
  .player-error.visible { display:flex; }
  .player-error span { max-width:360px; color:var(--muted); font-size:13px; line-height:1.5; }
  .error-icon { display:grid; place-items:center; width:42px; height:42px; border-radius:50%;
                background:#4c1f35; color:#ff9eaa; font-size:23px; font-weight:800; }
  .err-actions { display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin-top:6px; }
  a.button, button.button { margin-top:22px; display:inline-flex; align-items:center; justify-content:center; min-height:48px;
             padding:13px 22px; border-radius:13px; background:linear-gradient(135deg,var(--blue),var(--violet));
             color:#06101f; text-decoration:none; font-weight:900; font-size:14px; border:0; cursor:pointer;
             font-variant-caps:small-caps; text-transform:lowercase; letter-spacing:.05em;
             box-shadow:0 10px 24px rgba(98,168,255,.2); }
  .err-actions a.button, .err-actions button.button { margin-top:0; }
  a.button.secondary, button.button.secondary { color:#eff6ff; background:#1b2949; border:1px solid #38517f; box-shadow:none; }
  .download-card { display:flex; flex-direction:column; align-items:center; text-align:center; padding:30px 18px;
                   border:1px solid var(--line); border-radius:18px; margin-top:24px; background:#0a1020; }
  .download-icon { display:grid; place-items:center; width:58px; height:58px; border-radius:18px;
                   background:linear-gradient(135deg,#203b70,#4b2a82); font-size:27px; margin-bottom:15px; }
  .hint { color:var(--muted); font-size:13px; line-height:1.55; margin-top:15px; text-align:center; }
  .footer { color:#52617f; font-size:11px; text-align:center; margin-top:18px; }
  @media (max-width:520px) { body { padding:18px 11px 30px; } .card { border-radius:19px; padding:18px 14px; }
    .player-top { font-size:10px; } .quality { display:none; } .player-error { min-height:240px; } }
</style>
</head>
<body>
<main class="wrap"><div class="brand"><span class="brand-mark">↗</span><span>teradrop secure delivery</span></div>
<section class="card"><div class="eyebrow">__MODE__</div><h1>__TITLE__</h1>
<p class="sub">fast, protected delivery from your telegram request.</p>
__BODY__
</section><div class="footer">link expires automatically for your security</div></main>
</body>
</html>"""


_ADMIN_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>teradrop control panel</title>
<style>
:root{color-scheme:dark;--bg:#070a12;--panel:#101728;--panel2:#151f34;--line:#273653;--text:#f4f7ff;--muted:#8d9ab5;--blue:#6ea8ff;--green:#58dfae;--red:#ff7685}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 90% 0,#172a52 0,#070a12 44%);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,sans-serif}
button,input,select,textarea{font:inherit}button{cursor:pointer;border:0}.shell{max-width:1180px;margin:auto;padding:24px 16px 50px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:20px}.brand{display:flex;align-items:center;gap:10px}.mark{display:grid;place-items:center;width:38px;height:38px;border-radius:13px;background:linear-gradient(135deg,#60a7ff,#a66cff);font-weight:900;font-size:20px}.brand strong{display:block;font-size:18px}.brand span{display:block;color:var(--muted);font-size:11px;letter-spacing:.12em;text-transform:uppercase}.pill{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}.stat,.card{border:1px solid var(--line);border-radius:18px;background:rgba(16,23,40,.88);box-shadow:0 18px 45px #0002}.stat{padding:17px}.stat b{display:block;font-size:25px}.stat span,.muted{color:var(--muted);font-size:12px}.layout{display:grid;grid-template-columns:1.15fr .85fr;gap:16px}.card{padding:18px;margin-bottom:16px}.card h2{font-size:16px;margin:0 0 14px}.card h3{font-size:13px;color:#c7d5ef;margin:18px 0 9px}.formgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.field{display:flex;flex-direction:column;gap:5px}.field.full{grid-column:1/-1}.field label{color:var(--muted);font-size:11px;letter-spacing:.09em;text-transform:uppercase}.field input,.field select,.field textarea{width:100%;color:var(--text);background:#0a1020;border:1px solid var(--line);border-radius:10px;padding:10px 11px;outline:none}.field textarea{min-height:74px;resize:vertical}.field input:focus,.field textarea:focus{border-color:var(--blue)}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.btn{padding:10px 14px;border-radius:10px;color:#07111f;background:linear-gradient(135deg,#6ea8ff,#a87aff);font-weight:800;font-variant-caps:small-caps;text-transform:lowercase;letter-spacing:.05em}.btn.alt{color:#dbe8ff;background:#1b2a47;border:1px solid #38517c}.btn.danger{color:#fff;background:#612637}.row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 0;border-bottom:1px solid #1d2940}.row:last-child{border-bottom:0}.row strong{font-size:13px}.row .meta{color:var(--muted);font-size:12px}.status{font-size:11px;padding:4px 8px;border-radius:999px;background:#193d35;color:var(--green)}.status.off{background:#34232b;color:#ff9aa5}.plan-row{display:grid;grid-template-columns:1fr auto;align-items:center;gap:10px}.plan-actions{display:flex;gap:6px}.mini{padding:7px 9px;border-radius:8px;color:#d9e6ff;background:#1b2a47;border:1px solid #344b72;font-size:11px;font-variant-caps:small-caps;text-transform:lowercase}.mini.delete{background:#3a202b;color:#ffadb6;border-color:#6b3546}.notice{display:none;margin-bottom:14px;padding:10px 12px;border-radius:10px;background:#153a34;color:#9af0cc}.notice.error{background:#452530;color:#ffb2bb}.login{max-width:440px;margin:13vh auto}.hidden{display:none!important}.log{max-height:220px;overflow:auto;font:12px/1.55 ui-monospace,monospace;color:#a9bad8;white-space:pre-wrap}@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}}@media(max-width:480px){.shell{padding:16px 10px 36px}.top{align-items:flex-start}.top .pill{display:none}.grid{gap:8px}.stat{padding:13px}.stat b{font-size:21px}.card{padding:14px;border-radius:15px}.formgrid{grid-template-columns:1fr}.field.full{grid-column:auto}.plan-row{grid-template-columns:1fr}.plan-actions{justify-content:flex-start}}
 </style></head><body><div class="shell">
 <div id="login" class="card login"><div class="brand"><div class="mark">↗</div><div><strong>teradrop</strong><span>admin control panel</span></div></div><p class="muted">enter the admin password configured in <code>ADMIN_PANEL_PASSWORD</code>.</p><div class="field"><label>admin password</label><input id="token" type="password" autocomplete="current-password" placeholder="enter password"></div><div class="actions"><button class="btn" onclick="saveToken()">open panel</button></div></div>
<div id="app" class="hidden"><header class="top"><div class="brand"><div class="mark">↗</div><div><strong>teradrop</strong><span>admin control panel</span></div></div><div class="pill">secure operations dashboard <button class="mini" onclick="logout()">log out</button></div></header><div id="notice" class="notice"></div>
<section class="grid"><div class="stat"><b id="users">—</b><span>total users</span></div><div class="stat"><b id="downloads">—</b><span>downloads</span></div><div class="stat"><b id="premium">—</b><span>active premium</span></div><div class="stat"><b id="queue">—</b><span>queued tasks</span></div></section>
<div class="layout"><div>
<section class="card"><h2>premium plans</h2><div id="plans"></div><h3>add or edit plan</h3><form id="plan-form" class="formgrid"><div class="field"><label>key</label><input name="key" maxlength="8" required></div><div class="field"><label>name</label><input name="label" required></div><div class="field"><label>short name</label><input name="short_label" required></div><div class="field"><label>price ₹</label><input name="price" type="number" min="0" step="0.01" required></div><div class="field"><label>validity days</label><input name="duration_days" type="number" min="1" required></div><div class="field"><label>batch limit</label><input name="batch_limit" type="number" min="1" required></div><div class="field"><label>total links, 0 = unlimited</label><input name="total_links" type="number" min="0" required></div><div class="field"><label>active</label><select name="active"><option value="true">enabled</option><option value="false">disabled</option></select></div><div class="actions field full"><button class="btn">save plan</button><button type="button" class="btn alt" onclick="clearPlan()">clear</button></div></form></section>
<section class="card"><h2>user controls</h2><form id="user-form" class="formgrid"><div class="field"><label>telegram user id</label><input name="user_id" type="number" required></div><div class="field"><label>action</label><select name="action"><option value="premium">grant premium</option><option value="ban">ban user</option><option value="unban">unban user</option></select></div><div class="field"><label>plan key, for premium</label><input name="plan_key" value="r"></div><div class="field"><label>days, for premium</label><input name="days" type="number" value="30" min="1"></div><div class="actions field full"><button class="btn">apply user action</button></div></form></section>
</div><div>
<section class="card"><h2>runtime & features</h2><div id="runtime"></div><form id="settings-form" class="formgrid"><div class="field"><label>upload limit mb</label><input name="limit" type="number" min="1"></div><div class="field"><label>maintenance</label><select name="maintenance"><option value="off">off</option><option value="on">on</option></select></div><div class="field"><label>bot access</label><select name="bot_public"><option value="true">public</option><option value="false">authorised users only</option></select></div><div class="field"><label>log channel id</label><input name="log_channel"></div><div class="field"><label>dump channel id</label><input name="dump_channel"></div><div class="field full"><label>welcome text override</label><textarea name="welcome"></textarea></div><div class="field full"><label>file caption template</label><textarea name="caption"></textarea></div><div class="actions field full"><button class="btn">save settings</button></div></form></section>
<section class="card"><h2>force-sub channels</h2><div id="forcesubs"></div><form id="force-form" class="formgrid"><div class="field"><label>channel id or @username</label><input name="chat_id" required></div><div class="field"><label>invite url, optional</label><input name="invite_url" placeholder="auto-generated when possible"></div><div class="actions field full"><button class="btn">add channel</button></div></form></section>
<section class="card"><h2>mini app connections</h2><div id="miniapps"></div></section><section class="card"><h2>recent logs</h2><div id="logs" class="log">loading…</div></section>
</div></div></div></div>
<script>
 let plans=[];const $=id=>document.getElementById(id);function normalizePassword(value){return String(value||"").trim().replace(/^['"]|['"]$/g,"").trim()}function token(){return normalizePassword(sessionStorage.getItem("teradrop_admin_password")||"")}
function notice(msg,error=false){$("notice").textContent=msg;$("notice").className="notice"+(error?" error":"");$("notice").style.display="block";setTimeout(()=>{$("notice").style.display="none"},4200)}
 async function api(path,opts={}){const res=await fetch(path,{...opts,headers:{"content-type":"application/json","authorization":"Bearer "+token(),...(opts.headers||{})}});const data=await res.json().catch(()=>({error:"invalid server response"}));if(res.status===401)throw new Error("invalid or missing admin password");if(!res.ok)throw new Error(data.error||"request failed");return data}
 function saveToken(){const value=normalizePassword($("token").value);if(!value){notice("enter the admin password",true);return}sessionStorage.setItem("teradrop_admin_password",value);load().catch(err=>{sessionStorage.removeItem("teradrop_admin_password");notice(err.message,true)})}
 function logout(){sessionStorage.removeItem("teradrop_admin_password");$("app").classList.add("hidden");$("login").classList.remove("hidden")}
function clearPlan(){document.querySelector("#plan-form").reset()}
function fillPlan(key){const p=plans.find(x=>x.key===key);if(!p)return;const f=$("plan-form");Object.keys(p).forEach(k=>{if(f.elements[k])f.elements[k].value=String(p[k])})}
function render(data){$("users").textContent=data.stats.users;$("downloads").textContent=data.stats.downloads;$("premium").textContent=data.stats.premium;$("queue").textContent=data.queue;
plans=data.plans;$("plans").innerHTML=plans.length?plans.map(p=>`<div class="row plan-row"><div><strong>${esc(p.label)}</strong><div class="meta">${esc(p.key)} · ₹${p.price} · ${p.duration_days} days · batch ${p.batch_limit} · ${p.total_links||"unlimited"} total</div></div><div class="plan-actions"><button class="mini" onclick="fillPlan('${esc(p.key)}')">edit</button><button class="mini delete" onclick="deletePlan('${esc(p.key)}')">hide</button></div></div>`).join(""):"<span class='muted'>no plans</span>";
const s=data.settings;$("settings-form").limit.value=s.limit;$("settings-form").maintenance.value=s.maintenance;$("settings-form").bot_public.value=s.bot_public;$("settings-form").log_channel.value=s.log_channel;$("settings-form").dump_channel.value=s.dump_channel;$("settings-form").welcome.value=s.welcome;$("settings-form").caption.value=s.caption;
$("runtime").innerHTML=`<div class="row"><span>transport</span><strong>${esc(data.transport)}</strong></div><div class="row"><span>maintenance</span><span class="status ${s.maintenance==="on"?"off":""}">${s.maintenance}</span></div>`;
$("forcesubs").innerHTML=data.force_subs.length?data.force_subs.map(x=>`<div class="row"><div><strong>${esc(x.chat_id)}</strong><div class="meta">${esc(x.invite_url||"invite unavailable")}</div></div><button class="mini delete" onclick="removeForce('${esc(x.chat_id)}')">remove</button></div>`).join(""):"<span class='muted'>no force-sub channels</span>";
$("miniapps").innerHTML=Object.entries(data.mini_apps).map(([name,x])=>`<div class="row"><div><strong>${esc(name)}</strong><div class="meta">${esc(x.url||"not configured")}</div></div><span class="status ${x.status==="ready"?"":"off"}">${esc(x.status)}</span></div>`).join("");
$("logs").textContent=data.logs.join("\\n")||"no logs yet"}
function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
async function load(){if(!token()){$("login").classList.remove("hidden");return}const data=await api("/admin/api/summary");$("login").classList.add("hidden");$("app").classList.remove("hidden");render(data)}
async function deletePlan(key){if(!confirm("hide this plan from new purchases?"))return;try{await api("/admin/api/plan/delete",{method:"POST",body:JSON.stringify({key})});notice("plan hidden");load()}catch(e){notice(e.message,true)}}
document.querySelector("#plan-form").addEventListener("submit",async e=>{e.preventDefault();try{const body=Object.fromEntries(new FormData(e.target));body.price=Number(body.price);body.duration_days=Number(body.duration_days);body.batch_limit=Number(body.batch_limit);body.total_links=Number(body.total_links);body.active=body.active==="true";await api("/admin/api/plan",{method:"POST",body:JSON.stringify(body)});notice("plan saved");load()}catch(err){notice(err.message,true)}})
document.querySelector("#settings-form").addEventListener("submit",async e=>{e.preventDefault();try{await api("/admin/api/settings",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});notice("settings saved");load()}catch(err){notice(err.message,true)}})
document.querySelector("#user-form").addEventListener("submit",async e=>{e.preventDefault();try{await api("/admin/api/user",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});notice("user action applied");load()}catch(err){notice(err.message,true)}})
document.querySelector("#force-form").addEventListener("submit",async e=>{e.preventDefault();try{await api("/admin/api/force-sub",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});notice("force-sub channel saved");e.target.reset();load()}catch(err){notice(err.message,true)}})
async function removeForce(chat_id){try{await api("/admin/api/force-sub",{method:"POST",body:JSON.stringify({chat_id,remove:true})});notice("force-sub channel removed");load()}catch(e){notice(e.message,true)}}load().catch(e=>notice(e.message,true));
</script></body></html>"""


def _not_found(handler: BaseHTTPRequestHandler) -> None:
    body = b"This link has expired. Open the file again in the bot."
    handler.send_response(404)
    handler.send_header("content-type", "text/plain")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _normalize_admin_password(value: str) -> str:
    value = (value or "").strip()
    match = re.match(r"^ADMIN_PANEL_PASSWORD\s*=\s*(.*)$", value, re.I)
    if match:
        value = match.group(1).strip()
    return value.strip("\"'")


def _admin_authorized(handler: BaseHTTPRequestHandler) -> bool:
    expected = _normalize_admin_password(settings.admin_panel_password)
    if not expected:
        return False
    supplied = handler.headers.get("Authorization", "")
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    supplied = supplied or handler.headers.get("X-Admin-Token", "")
    supplied = _normalize_admin_password(supplied)
    return bool(supplied) and secrets.compare_digest(supplied, expected)


def _admin_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, default=str).encode()
    handler.send_response(status)
    handler.send_header("content-type", "application/json; charset=utf-8")
    handler.send_header("cache-control", "no-store")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _admin_body(handler: BaseHTTPRequestHandler) -> dict:
    try:
        length = min(int(handler.headers.get("Content-Length", "0") or "0"), 1_000_000)
    except ValueError:
        length = 0
    raw = handler.rfile.read(length) if length else b"{}"
    data = json.loads(raw or b"{}")
    if not isinstance(data, dict):
        raise ValueError("request body must be an object")
    return data


def _mini_app_snapshot() -> dict[str, dict[str, str]]:
    configs = (
        ("flezen", settings.flezen_tg_bot, settings.flezen_webapp_url),
        ("diskwala", settings.diskwala_tg_bot, settings.diskwala_webapp_url),
        ("vidbunker", settings.vidbunker_tg_bot, settings.vidbunker_webapp_url),
    )
    out: dict[str, dict[str, str]] = {}
    for name, bot_name, url in configs:
        fetched = storage.kv_get(f"tg_init_data_fetched_at:{name}")
        out[name] = {
            "url": url if bot_name else "",
            "status": "ready" if bot_name and fetched else ("configured" if bot_name else "not configured"),
        }
    return out


def _admin_summary() -> dict:
    from app.job_queue import JOB_QUEUE

    stats = storage.stats()
    queue = JOB_QUEUE.snapshot()
    return {
        "stats": stats,
        "queue": queue.get("queued", 0),
        "queue_detail": queue,
        "plans": storage.list_plans(False),
        "force_subs": storage.list_force_subs(),
        "logs": storage.recent_logs(30),
        "users": storage.list_users(40),
        "transport": "local bot api · up to 2 gb" if settings.bot_api_enabled else "telegram api · 49 mb",
        "settings": {
            "limit": storage.kv_get("limit") or str(settings.effective_max_file_mb),
            "maintenance": storage.kv_get("maintenance") or ("on" if settings.maintenance else "off"),
            "bot_public": storage.kv_get("bot_public") or ("true" if settings.bot_public else "false"),
            "log_channel": storage.kv_get("log_channel") or settings.log_channel,
            "dump_channel": storage.kv_get("dump_channel") or settings.dump_channel,
            "welcome": storage.kv_get("welcome") or settings.welcome_text,
            "caption": storage.kv_get("caption") or settings.caption_template,
            "max_concurrent": settings.max_concurrent,
            "bot_name": settings.bot_name,
        },
        "mini_apps": _mini_app_snapshot(),
    }


def _telegram_call(method: str, payload: dict) -> dict:
    if not settings.bot_token:
        return {}
    try:
        response = httpx.post(
            settings.telegram_method_url(method),
            json=payload,
            timeout=httpx.Timeout(15, connect=8),
        )
        return response.json() if response.content else {}
    except Exception:
        return {}


def _admin_notify_premium(user_id: int, plan: dict, days: int, source: str) -> None:
    expiry = storage.activate_plan(user_id, str(plan["key"]), days)
    expiry_text = expiry.strftime("%d %b %Y, %I:%M %p UTC")
    user_text = (
        "<b>✅ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ</b>\n\n"
        f"ʏᴏᴜʀ <b>{html.escape(str(plan['label']))}</b> ɪs ɴᴏᴡ ᴀᴄᴛɪᴠᴇ.\n"
        f"ᴇxᴘɪʀᴇs: <code>{expiry_text}</code>"
    )
    _telegram_call("sendMessage", {"chat_id": user_id, "text": user_text, "parse_mode": "HTML"})
    log_text = (
        "<b>🛠 ᴡᴇʙ ᴀᴅᴍɪɴ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛɪᴏɴ</b>\n\n"
        f"user: <code>{user_id}</code>\nplan: <b>{html.escape(str(plan['label']))}</b>\n"
        f"source: <b>{html.escape(source)}</b>\nexpires: <code>{expiry_text}</code>"
    )
    storage.log("info", f"{source}: premium activated for user {user_id}")
    targets = [
        storage.kv_get("log_channel") or settings.log_channel,
        storage.kv_get("dump_channel") or settings.dump_channel,
    ]
    targets.extend(str(x) for x in storage.admin_ids())
    for target in dict.fromkeys(
        str(x).strip() for x in targets if str(x).strip() and str(x).strip() != "0"
    ):
        _telegram_call("sendMessage", {"chat_id": target, "text": log_text, "parse_mode": "HTML"})


def _generate_invite_sync(chat_id: str) -> str:
    for method, payload in (
        ("createChatInviteLink", {"chat_id": chat_id, "name": "TeraDrop force subscription"}),
        ("exportChatInviteLink", {"chat_id": chat_id}),
    ):
        result = _telegram_call(method, payload)
        if result.get("ok"):
            value = result.get("result")
            if isinstance(value, dict):
                value = value.get("invite_link")
            if value:
                return str(value)
    if chat_id.startswith("@") and len(chat_id) > 1:
        return f"https://t.me/{chat_id[1:]}"
    return ""


_ADMIN_UI_PATH = Path(__file__).with_name("admin_ui.html")


def serve_admin_page(handler: BaseHTTPRequestHandler) -> None:
    if _ADMIN_UI_PATH.exists():
        body = _ADMIN_UI_PATH.read_bytes()
    else:
        body = _ADMIN_PAGE.encode()
    handler.send_response(200)
    handler.send_header("content-type", "text/html; charset=utf-8")
    handler.send_header("cache-control", "no-store")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def serve_admin_api(handler: BaseHTTPRequestHandler, parsed, method: str = "GET") -> None:
    if not _admin_authorized(handler):
        _admin_json(handler, 401, {"error": "admin password required"})
        return
    try:
        if method == "GET" and parsed.path == "/admin/api/summary":
            _admin_json(handler, 200, _admin_summary())
            return
        if method == "GET" and parsed.path == "/admin/api/logs":
            _admin_json(handler, 200, {"logs": storage.recent_logs(100)})
            return
        if method == "GET" and parsed.path == "/admin/api/env":
            reveal = parse_qs(parsed.query).get("reveal", ["0"])[0] == "1"
            _admin_json(handler, 200, env_manager.list_variables(reveal=reveal))
            return
        if method == "GET" and parsed.path == "/admin/api/queue":
            from app.job_queue import JOB_QUEUE

            _admin_json(handler, 200, JOB_QUEUE.snapshot())
            return
        if method != "POST":
            _admin_json(handler, 404, {"error": "not found"})
            return
        data = _admin_body(handler)
        if parsed.path == "/admin/api/env":
            key = str(data.get("key", "")).strip()
            if data.get("delete"):
                _admin_json(handler, 200, env_manager.delete_variable(key))
                return
            value = "" if data.get("value") is None else str(data.get("value"))
            result = env_manager.set_variable(key, value, reveal=bool(data.get("reveal")))
            if data.get("restart"):
                env_manager.request_restart()
                result["restarting"] = True
            _admin_json(handler, 200, result)
            return
        if parsed.path == "/admin/api/env/bulk":
            entries = data.get("entries") or []
            last = None
            restart = False
            for item in entries:
                key = str(item.get("key", "")).strip()
                value = "" if item.get("value") is None else str(item.get("value"))
                last = env_manager.set_variable(key, value, reveal=False)
                restart = restart or bool((last.get("result") or {}).get("restart_required"))
            if data.get("restart") or (restart and data.get("restart_if_needed")):
                env_manager.request_restart()
                if last is not None:
                    last["restarting"] = True
            _admin_json(handler, 200, last or env_manager.list_variables())
            return
        if parsed.path == "/admin/api/restart":
            env_manager.request_restart()
            _admin_json(handler, 200, {"ok": True, "restarting": True})
            return
        if parsed.path == "/admin/api/plan":
            key = str(data.get("key", "")).strip().lower()
            if not key or not re.fullmatch(r"[a-z0-9_-]{1,12}", key):
                raise ValueError("plan key must use 1-12 lowercase letters, numbers, _ or -")
            plan = {
                "key": key,
                "label": str(data.get("label", "")).strip()[:80],
                "short_label": str(data.get("short_label", key)).strip()[:40],
                "price": float(data.get("price", 0)),
                "duration_days": int(data.get("duration_days", 0)),
                "batch_limit": int(data.get("batch_limit", 0)),
                "total_links": int(data.get("total_links", 0)),
                "active": bool(data.get("active", True)),
            }
            if not plan["label"] or plan["price"] < 0 or plan["duration_days"] < 1 or plan["batch_limit"] < 1 or plan["total_links"] < 0:
                raise ValueError("plan values are invalid")
            storage.upsert_plan(plan)
            _admin_json(handler, 200, {"ok": True})
            return
        if parsed.path == "/admin/api/plan/delete":
            key = str(data.get("key", "")).strip().lower()
            if not key:
                raise ValueError("plan key is required")
            storage.delete_plan(key)
            _admin_json(handler, 200, {"ok": True})
            return
        if parsed.path == "/admin/api/settings":
            allowed = {"limit", "maintenance", "bot_public", "log_channel", "dump_channel", "welcome", "caption"}
            for key in allowed:
                if key not in data:
                    continue
                value = str(data[key])
                if key == "limit":
                    value = str(max(1, int(value)))
                if key == "maintenance":
                    value = "on" if value == "on" else "off"
                if key == "bot_public":
                    value = "true" if value == "true" else "false"
                storage.kv_set(key, value[:4000])
            _admin_json(handler, 200, {"ok": True})
            return
        if parsed.path == "/admin/api/user":
            user_id = int(data.get("user_id", 0))
            action = str(data.get("action", ""))
            if user_id <= 0:
                raise ValueError("valid user id is required")
            if action == "ban":
                storage.ban(user_id)
            elif action == "unban":
                storage.unban(user_id)
            elif action == "premium":
                plan = storage.get_plan(str(data.get("plan_key", "r")).lower())
                if not plan:
                    raise ValueError("active plan not found")
                _admin_notify_premium(user_id, plan, max(1, int(data.get("days", plan["duration_days"]))), "web admin")
            else:
                raise ValueError("unknown user action")
            _admin_json(handler, 200, {"ok": True})
            return
        if parsed.path == "/admin/api/force-sub":
            chat_id = str(data.get("chat_id", "")).strip()
            if not chat_id:
                raise ValueError("channel id is required")
            if data.get("remove"):
                storage.remove_force_sub(chat_id)
            else:
                invite = str(data.get("invite_url", "")).strip() or _generate_invite_sync(chat_id)
                storage.add_force_sub(chat_id, invite)
            _admin_json(handler, 200, {"ok": True})
            return
        _admin_json(handler, 404, {"error": "not found"})
    except Exception as exc:
        _admin_json(handler, 400, {"error": str(exc)})


def _check_captcha(handler: BaseHTTPRequestHandler) -> bool:
    cookie = handler.headers.get("Cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("cap_token="):
            return captcha.validate(part[len("cap_token="):])
    return False


def _route_base(path: str) -> str:
    return path.split("/go/", 1)[0].rstrip("/")


def _route(base: str, path: str) -> str:
    return f"{base}{path}" if base else path

_KIND_CACHE: dict[str, tuple[float, str]] = {}
_KIND_TTL = 300.0
_URI_RE = re.compile(r'URI="([^"]+)"', re.I)
_CORS = {
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "Range, Origin, Accept, Content-Type",
    "access-control-allow-methods": "GET, HEAD, OPTIONS",
    "access-control-expose-headers": "Content-Length, Content-Range, Content-Type, Accept-Ranges",
}


def _sign_media_url(url: str) -> str:
    key = (settings.bot_token or "teradrop-media").encode()
    return hmac.new(key, url.encode(), hashlib.sha256).hexdigest()[:20]


def _verify_media_url(url: str, sig: str) -> bool:
    if not url or not sig:
        return False
    expected = _sign_media_url(url)
    if len(expected) != len(sig):
        return False
    return secrets.compare_digest(expected, sig)


def _b64url_encode(value: str) -> str:
    return urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _b64url_decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(value + padding).decode()


def _proxied_url(base: str, token: str, target: str) -> str:
    signed = _sign_media_url(target)
    path = f"/media/{token}?t=p&u={_b64url_encode(target)}&s={signed}"
    return _route(base, path)


def _rewrite_playlist(text: str, playlist_url: str, token: str, base: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if stripped.startswith("#"):
            def _repl(match: re.Match[str]) -> str:
                abs_url = urljoin(playlist_url, match.group(1))
                return f'URI="{_proxied_url(base, token, abs_url)}"'
            lines.append(_URI_RE.sub(_repl, line))
            continue
        abs_url = urljoin(playlist_url, stripped)
        lines.append(_proxied_url(base, token, abs_url))
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _kind_from_peek(content_type: str, peek: bytes) -> str:
    ctype = (content_type or "").lower()
    head = (peek or b"").lstrip()
    if "mpegurl" in ctype or head.startswith(b"#EXTM3U"):
        return "hls"
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return "mp4"
    if "mp4" in ctype or "m4v" in ctype or "quicktime" in ctype:
        return "mp4"
    if head.startswith(b"\x1aE\xdf\xa3"):
        return "webm" if b"webm" in head[:64].lower() else "mkv"
    if "webm" in ctype:
        return "webm"
    if "matroska" in ctype or "x-mkv" in ctype:
        return "mkv"
    if ctype.startswith("audio/") or head.startswith(b"ID3") or head[:2] == b"\xff\xfb":
        return "audio"
    if "mp2t" in ctype or (head[:1] == b"G" and len(head) >= 188):
        return "ts"
    if any(x in ctype for x in ("x-msvideo", "x-flv", "x-matroska", "video/x-ms-wmv")):
        return "mkv"
    if ctype.startswith("video/"):
        return "mp4"
    return "unknown"


def _sniff_kind(url: str, extra_headers: dict[str, str] | None) -> str:
    headers = _request_headers(url, extra_headers)
    headers["range"] = "bytes=0-512"
    try:
        with httpx.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=True,
            timeout=httpx.Timeout(12.0, connect=8.0),
        ) as res:
            peek = b""
            for chunk in res.iter_bytes(512):
                peek += chunk
                if len(peek) >= 512:
                    break
            return _kind_from_peek(res.headers.get("content-type", ""), peek)
    except Exception:
        path = urlparse(url).path.lower()
        if path.endswith(".m3u8"):
            return "hls"
        if path.endswith(".mp4") or path.endswith(".m4v"):
            return "mp4"
        if path.endswith(".webm"):
            return "webm"
        if path.endswith((".mkv", ".avi", ".flv", ".wmv")):
            return "mkv"
        if path.endswith(".ts"):
            return "ts"
        return "auto"


def _cached_kind(token: str, url: str, extra_headers: dict[str, str] | None) -> str:
    hit = _KIND_CACHE.get(token)
    now = time.monotonic()
    if hit and hit[0] > now:
        return hit[1]
    kind = _sniff_kind(url, extra_headers)
    _KIND_CACHE[token] = (now + _KIND_TTL, kind)
    return kind


def _media_base(path: str) -> str:
    if "/media/" in path:
        return path.split("/media/", 1)[0].rstrip("/")
    return _route_base(path)


def _apply_common_headers(handler: BaseHTTPRequestHandler, extra: dict[str, str] | None = None) -> None:
    for key, value in _CORS.items():
        handler.send_header(key, value)
    handler.send_header("cache-control", "private, no-store")
    handler.send_header("x-content-type-options", "nosniff")
    if extra:
        for key, value in extra.items():
            handler.send_header(key, value)


def serve_media_options(handler: BaseHTTPRequestHandler) -> None:
    handler.send_response(204)
    _apply_common_headers(handler)
    handler.send_header("content-length", "0")
    handler.end_headers()



def serve_page(handler: BaseHTTPRequestHandler, parsed) -> None:
    token = parsed.path.removeprefix("/go/").strip("/")
    kind = (parse_qs(parsed.query).get("t") or [""])[0]
    file = resolve_cached_file(token) if token else None
    if not file or kind not in ("stream", "direct"):
        _not_found(handler)
        return

    if not _check_captcha(handler):
        base = _route_base(parsed.path)
        next_url = _route(base, f"/go/{token}?t={kind}")
        page = (
            _CAPTCHA_PAGE_V2
            .replace("__NEXT_URL__", next_url)
            .replace("__CHALLENGE_URL__", _route(base, "/_cap/challenge"))
            .replace("__REDEEM_URL__", _route(base, "/_cap/redeem"))
            .encode()
        )
        handler.send_response(200)
        handler.send_header("content-type", "text/html; charset=utf-8")
        handler.send_header("content-length", str(len(page)))
        handler.end_headers()
        handler.wfile.write(page)
        return

    title = html.escape(file.file_name)
    base = _route_base(parsed.path)
    media_url = _route(base, f"/media/{token}?t={kind}")
    if kind == "stream":
        direct_url = _route(base, f"/media/{token}?t=direct")
        remux_url = _route(base, f"/media/{token}?t=transmux")
        target = resolve_redirect(token, "stream")
        extra_headers = getattr(file, "request_headers", None) or {}
        media_kind = _cached_kind(token, target, extra_headers) if target else "auto"
        body = (
            _STREAM_BODY
            .replace("__SRC__", html.escape(media_url, quote=True))
            .replace("__DIRECT__", html.escape(direct_url, quote=True))
            .replace("__REMUX__", html.escape(remux_url, quote=True))
            .replace("__KIND__", html.escape(media_kind, quote=True))
        )
        mode = "online stream"
    else:
        body = (
            '<div class="download-card"><div class="download-icon">↓</div>'
            f'<p class="sub">ready to save · {html.escape(file.formatted_size)}</p>'
            f'<a class="button" href="{html.escape(media_url, quote=True)}" '
            f'download="{title}">download file</a>'
            '<div class="hint">your browser will download the file directly from this page.</div></div>'
        )
        mode = "direct download"
    page = (
        _PAGE.replace("__TITLE__", title)
        .replace("__MODE__", mode)
        .replace("__BODY__", body)
        .encode()
    )
    handler.send_response(200)
    handler.send_header("content-type", "text/html; charset=utf-8")
    handler.send_header("content-length", str(len(page)))
    handler.end_headers()
    handler.wfile.write(page)


def serve_captcha_api(handler: BaseHTTPRequestHandler, parsed) -> None:
    path = parsed.path
    if path == "/_cap/challenge":
        ch = captcha.create_challenge()
        body = json.dumps({"token": ch["token"], "challenges": ch["challenges"]}).encode()
        handler.send_response(200)
        handler.send_header("content-type", "application/json")
        handler.send_header("content-length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
        return
    if path == "/_cap/redeem":
        try:
            length = int(handler.headers.get("Content-Length", "0") or "0")
        except ValueError:
            length = 0
        raw = handler.rfile.read(length) if length > 0 else b""
        vtoken = None
        if raw:
            try:
                data = json.loads(raw)
                vtoken = captcha.redeem(data.get("token", ""), data.get("solutions", []))
            except Exception:
                vtoken = None
        body = json.dumps({"token": vtoken}).encode()
        handler.send_response(200)
        handler.send_header("content-type", "application/json")
        handler.send_header("content-length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
        return
    _not_found(handler)


def _drain_stderr(proc: subprocess.Popen, sink: bytearray) -> None:
    try:
        while True:
            chunk = proc.stderr.read(4096)
            if not chunk:
                return
            sink.extend(chunk)
            del sink[:-4000]
    except Exception:
        return


def _redact(text: str, secret_url: str) -> str:
    if secret_url and secret_url in text:
        text = text.replace(secret_url, "[hidden]")
    return text


def _transmux_stream(
    handler: BaseHTTPRequestHandler,
    source_url: str,
    head_only: bool,
    extra_headers: dict[str, str] | None = None,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        _proxy_raw(handler, source_url, head_only, extra_headers)
        return

    headers = _request_headers(source_url, extra_headers)
    ua = headers.pop("user-agent")
    ffmpeg_headers = "".join(
        f"{key.title()}: {value}\r\n" for key, value in headers.items()
    )
    cmd = [
        ffmpeg, "-loglevel", "error",
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto,httpproxy",
        "-user_agent", ua,
        "-headers", ffmpeg_headers,
        "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
        "-rw_timeout", "30000000",
        "-i", source_url,
        "-analyzeduration", "20M", "-probesize", "50M",
        "-fflags", "+genpts",
        "-c", "copy", "-f", "mp4",
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "pipe:1",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr_tail = bytearray()
    threading.Thread(target=_drain_stderr, args=(proc, stderr_tail), daemon=True).start()

    first_chunk = b""
    try:
        readable, _, _ = select.select([proc.stdout], [], [], 45.0)
        if readable:
            first_chunk = proc.stdout.read(256 * 1024) or b""
    except Exception:
        first_chunk = b""

    if not first_chunk:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        _redact(bytes(stderr_tail).decode("utf-8", "replace").strip(), source_url)
        _proxy_raw(handler, source_url, head_only, extra_headers)
        return

    handler.send_response(200)
    handler.send_header("content-type", "video/mp4")
    handler.send_header("accept-ranges", "none")
    _apply_common_headers(handler)
    handler.end_headers()
    if head_only:
        proc.kill()
        return
    try:
        handler.wfile.write(first_chunk)
        while True:
            chunk = proc.stdout.read(256 * 1024)
            if not chunk:
                break
            handler.wfile.write(chunk)
    except (BrokenPipeError, ConnectionResetError):
        pass
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def _proxy_raw(
    handler: BaseHTTPRequestHandler,
    target: str,
    head_only: bool,
    extra_headers: dict[str, str] | None = None,
    *,
    forward_range: bool = True,
) -> None:
    req_headers = _request_headers(target, extra_headers)
    range_header = handler.headers.get("Range") if forward_range else None
    if range_header:
        req_headers["range"] = range_header
    try:
        with httpx.stream("GET", target, headers=req_headers, follow_redirects=True, timeout=_TIMEOUT) as res:
            status = res.status_code if res.status_code in (200, 206) else 502
            handler.send_response(status)
            for name in ("content-type", "content-length", "content-range", "last-modified", "etag"):
                if name in res.headers:
                    handler.send_header(name, res.headers[name])
            if "accept-ranges" in res.headers:
                handler.send_header("accept-ranges", res.headers["accept-ranges"])
            else:
                handler.send_header("accept-ranges", "bytes")
            _apply_common_headers(handler)
            handler.end_headers()
            if head_only or status == 502:
                return
            for chunk in res.iter_bytes(256 * 1024):
                try:
                    handler.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
    except httpx.HTTPError:
        try:
            handler.send_response(502)
            handler.end_headers()
        except Exception:
            pass


def _proxy_hls_or_bytes(
    handler: BaseHTTPRequestHandler,
    target: str,
    token: str,
    base: str,
    head_only: bool,
    extra_headers: dict[str, str] | None,
    *,
    force_playlist: bool = False,
) -> None:
    req_headers = _request_headers(target, extra_headers)
    range_header = None if force_playlist else handler.headers.get("Range")
    if range_header:
        req_headers["range"] = range_header
    try:
        with httpx.stream("GET", target, headers=req_headers, follow_redirects=True, timeout=_TIMEOUT) as res:
            first = b""
            iterator = res.iter_bytes(64 * 1024)
            try:
                first = next(iterator)
            except StopIteration:
                first = b""
            ctype = res.headers.get("content-type", "")
            is_hls = force_playlist or _kind_from_peek(ctype, first) == "hls"
            if is_hls:
                chunks = [first]
                for chunk in iterator:
                    chunks.append(chunk)
                    if sum(len(c) for c in chunks) > 8_000_000:
                        break
                raw = b"".join(chunks)
                text = raw.decode("utf-8", "replace")
                rewritten = _rewrite_playlist(text, str(res.url), token, base)
                body = rewritten.encode("utf-8")
                handler.send_response(200)
                handler.send_header("content-type", "application/vnd.apple.mpegurl")
                handler.send_header("content-length", str(len(body)))
                handler.send_header("accept-ranges", "none")
                _apply_common_headers(handler)
                handler.end_headers()
                if not head_only:
                    handler.wfile.write(body)
                return

            status = res.status_code if res.status_code in (200, 206) else 502
            handler.send_response(status)
            for name in ("content-type", "content-length", "content-range", "last-modified", "etag"):
                if name in res.headers:
                    handler.send_header(name, res.headers[name])
            handler.send_header("accept-ranges", res.headers.get("accept-ranges", "bytes"))
            _apply_common_headers(handler)
            handler.end_headers()
            if head_only or status == 502:
                return
            if first:
                handler.wfile.write(first)
            for chunk in iterator:
                try:
                    handler.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
    except (httpx.HTTPError, BrokenPipeError, ConnectionResetError):
        try:
            handler.send_response(502)
            handler.end_headers()
        except Exception:
            pass


def serve_media(handler: BaseHTTPRequestHandler, parsed, head_only: bool = False) -> None:
    token = parsed.path.removeprefix("/media/").strip("/")
    query = parse_qs(parsed.query)
    kind = (query.get("t") or [""])[0]
    file = resolve_cached_file(token) if token else None
    extra_headers = getattr(file, "request_headers", None) if file else None
    base = _media_base(parsed.path)

    if kind == "p":
        raw_target = (query.get("u") or [""])[0]
        sig = (query.get("s") or [""])[0]
        try:
            target = _b64url_decode(raw_target)
        except Exception:
            target = ""
        if not file or not target.startswith(("http://", "https://")) or not _verify_media_url(target, sig):
            _not_found(handler)
            return
        _proxy_hls_or_bytes(handler, target, token, base, head_only, extra_headers)
        return

    target = resolve_redirect(token, "direct" if kind == "direct" else "stream") if file else None
    if kind == "direct":
        if not target:
            _not_found(handler)
            return
        _proxy_raw(handler, target, head_only, extra_headers)
        return

    if not target:
        _not_found(handler)
        return

    if kind == "transmux":
        _transmux_stream(handler, target, head_only, extra_headers)
        return

    media_kind = _cached_kind(token, target, extra_headers)
    if media_kind == "hls":
        _proxy_hls_or_bytes(
            handler, target, token, base, head_only, extra_headers, force_playlist=True
        )
        return
    if media_kind in {"mp4", "webm", "audio"}:
        _proxy_raw(handler, target, head_only, extra_headers)
        return
    if media_kind in {"mkv", "ts", "avi"}:
        _transmux_stream(handler, target, head_only, extra_headers)
        return
    # Unknown: prefer a direct byte proxy so browser-native MP4/WebM still
    # plays, then the page can fall back to /media/<token>?t=transmux.
    _proxy_raw(handler, target, head_only, extra_headers)
