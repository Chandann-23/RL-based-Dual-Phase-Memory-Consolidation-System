(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const o of document.querySelectorAll('link[rel="modulepreload"]'))t(o);new MutationObserver(o=>{for(const r of o)if(r.type==="childList")for(const c of r.addedNodes)c.tagName==="LINK"&&c.rel==="modulepreload"&&t(c)}).observe(document,{childList:!0,subtree:!0});function s(o){const r={};return o.integrity&&(r.integrity=o.integrity),o.referrerPolicy&&(r.referrerPolicy=o.referrerPolicy),o.crossOrigin==="use-credentials"?r.credentials="include":o.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function t(o){if(o.ep)return;o.ep=!0;const r=s(o);fetch(o.href,r)}})();const m="";document.getElementById("userInput").addEventListener("keydown",n=>{n.key==="Enter"&&l()});window.sendMessage=l;window.toggleBreakdown=y;async function l(){const n=document.getElementById("userInput"),e=n.value.trim();if(e){n.value="",d("user",e);try{const t=await(await fetch(`${m}/chat`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:e})})).json();f(t.response,t.memory_details),v(t.agent_stats),b(t.persistent_memory),h(t.consolidation_log)}catch{d("bot","⚠️ Could not reach backend. Make sure Flask is running.")}}}function d(n,e){const s=document.getElementById("messages"),t=document.createElement("div");t.className=`msg ${n}`,t.innerHTML=`<div class="bubble">${e}</div>`,s.appendChild(t),s.scrollTop=s.scrollHeight}function f(n,e){var r;const s=document.getElementById("messages"),t=document.createElement("div");t.className="msg bot";let o="";if(e&&e.length){const c=e.map(a=>a.concept).join(", "),p=e.map(a=>{const i=Math.round(a.importance*100),g=i>=65?"var(--ok)":i>=35?"var(--mid)":"var(--warn)";return`
          <div class="concept-row">
            <span class="concept-name">${a.concept}</span>
            <span style="color:var(--muted)">${a.frequency}</span>
            <div class="importance-bar-wrap">
              <div class="importance-bar" style="width:${i}%;background:${g}"></div>
            </div>
            <span style="font-weight:600;font-size:0.68rem">${a.importance}</span>
            <span class="action-badge badge-${a.action}">${a.action}</span>
          </div>`}).join(""),u=(((r=e[0])==null?void 0:r.reasons)||[]).map(a=>`<li>${a}</li>`).join("");o=`
        <div class="memory-breakdown">
          <div class="breakdown-section">
            <h4>Detected Concepts</h4>
            <p style="color:var(--accent2);font-weight:600;font-size:0.72rem">${c}</p>
          </div>
          <div class="breakdown-section">
            <h4>Importance + RL Decision</h4>
            ${p}
          </div>
          <div class="breakdown-section">
            <h4>Reasons (top concept)</h4>
            <ul class="reasons-list">${u}</ul>
          </div>
        </div>`}t.innerHTML=`
      <div class="bubble">${n}</div>
      ${e!=null&&e.length?'<button class="show-details-btn" onclick="toggleBreakdown(this)">▾ Show Memory Details</button>':""}
      ${o}
    `,s.appendChild(t),s.scrollTop=s.scrollHeight}function y(n){const e=n.nextElementSibling;if(!e)return;const s=e.classList.toggle("open");n.textContent=s?"▴ Hide Memory Details":"▾ Show Memory Details"}function v(n){n&&(document.getElementById("agentStats").innerHTML=`
      <span>Steps: <b>${n.steps}</b></span>
      <span>ε: <b>${n.epsilon}</b></span>
      <span>Avg Reward: <b>${n.avg_reward}</b></span>
    `)}function b(n){const e=document.getElementById("persistentMemory");if(!n||n.length===0){e.innerHTML='<p class="empty-state">Nothing stored yet.</p>';return}e.innerHTML=n.map(s=>`
      <div class="mem-item">
        <span class="mem-key">${s.concept}</span>
        <span class="mem-val">freq ${s.frequency}</span>
      </div>`).join("")}function h(n){const e=document.getElementById("consolidationLog");if(!n||n.length===0)return;const s=n.map(t=>`<div class="log-entry">
        <span style="color:${t.action==="STORE"?"var(--ok)":t.action==="REINFORCE"?"var(--mid)":"var(--warn)"}">●</span>
        <span style="color:var(--accent2)">${t.concept}</span>
        <span class="action-badge badge-${t.action}">${t.action}</span>
        <span style="color:var(--muted)">${t.importance}</span>
      </div>`).join("");e.innerHTML=s+e.innerHTML}
