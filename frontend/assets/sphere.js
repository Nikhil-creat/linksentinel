const M=[["Base62 Shortener","core"],["Redis Redirect","speed"],["Edge Tracking","clicks"],["Malware Agent","agent"],["CNN Inspector","vision"],["Quarantine","shield"],["RAG Analytics","rag"],["pgvector Search","vector"],["Social Previews","agent"],["Sliding Limiter","lua"],["JWT + RBAC","auth"],["GDPR Hashing","privacy"],["SSRF Guard","net"],["Celery Workers","async"],["Alembic","db"],["Docker Compose","ops"],["Healthchecks","ops"],["Groq Router","llm"],["Gemini Router","llm"],["Retention Jobs","gdpr"],["Audit Trail","gov"]];
const orb=$("orb"),world=$("world"),hl=$("headline"),N=21,GA=Math.PI*(3-Math.sqrt(5)),cards=[];
M.forEach(([t,k],i)=>{
const y=1-i/(N-1)*2,r=Math.sqrt(Math.max(0,1-y*y)),th=i*GA,x=Math.cos(th)*r,z=Math.sin(th)*r,c=document.createElement("div");c.className="card";c.innerHTML=`<figure><small>${k}</small><b>${t}</b></figure>`;orb.appendChild(c);cards.push({c,x,y,z,lat:Math.asin(y)*180/Math.PI,lon:Math.atan2(x,z)*180/Math.PI})});
let R=300,rx=-8,ry=0,vy=.12,drag=0,lx=0,ly=0;
function layout(){const w=innerWidth,h=innerHeight,s=w<=380?0:w<=640?1:2,st=document.documentElement.style;R=Math.max([108,120,155][s],Math.min(480,h*[.38,.42,.46][s],w*[.48,.52,.58][s]));st.setProperty("--cw",Math.round(Math.max(72,R*[.44,.46,.47][s]))+"px");st.setProperty("--persp",[620,760,920,1150][w<=380?0:w<=640?1:w<=900?2:3]+"px");
cards.forEach(o=>o.c.style.transform=`translate3d(${o.x*R}px,${-o.y*R}px,${o.z*R}px) rotateY(${o.lon}deg) rotateX(${o.lat}deg)`)}
let lw=innerWidth,lh=innerHeight;addEventListener("resize",()=>{if(Math.abs(innerWidth-lw)<20&&Math.abs(innerHeight-lh)<20)return;lw=innerWidth;lh=innerHeight;layout()});layout();
$("stage").onpointerdown=e=>{drag=1;lx=e.clientX;ly=e.clientY};addEventListener("pointerup",()=>drag=0);
addEventListener("pointermove",e=>{if(!drag)return;vy=(e.clientX-lx)*.25;ry+=vy;rx=Math.max(-60,Math.min(60,rx+(e.clientY-ly)*-.12));lx=e.clientX;ly=e.clientY});
(function loop(){if(!drag){ry+=vy;vy+=(.12-vy)*.03}world.style.transform=`rotateX(${rx}deg) rotateY(${ry}deg)`;hl.style.transform=`rotateY(${-ry}deg) rotateX(${-rx}deg)`;
const a=ry*Math.PI/180;cards.forEach(o=>{const zz=-o.x*Math.sin(a)+o.z*Math.cos(a);o.c.firstChild.style.setProperty("--d",(.55*(1-(zz+1)/2)).toFixed(2))});requestAnimationFrame(loop)})();
$("bar").style.transform="scaleX(.6)";const t0=Date.now();
function done(){$("bar").style.transform="scaleX(1)";setTimeout(()=>{$("splash").classList.add("out");document.body.classList.add("on");setTimeout(()=>$("splash").remove(),950)},300)}
Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,9000))]).then(()=>setTimeout(done,Math.max(0,1150-(Date.now()-t0))));
