// ═══════════════════════════════════════════════════════════════════
//  GLOBAL ELEMENTS & CURSOR
// ═══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    initCursor();
    initHeader();
    initReveal();
    
    // Only run if we are on the index page
    if (document.getElementById('bg-canvas')) initCanvas();
    if (document.getElementById('pg')) {
        loadProperties();
        initProvinceGrid();
    }
});

function initCursor() {
    const cur = document.getElementById('cursor');
    const ring = document.getElementById('cursor-ring');
    if(!cur || !ring) return;
    let mx=0, my=0, rx=0, ry=0;
    document.addEventListener('mousemove', e => {
        mx=e.clientX; my=e.clientY;
        cur.style.left=mx+'px'; cur.style.top=my+'px';
    });
    (function anim(){
        rx+=(mx-rx)*.12; ry+=(my-ry)*.12;
        ring.style.left=rx+'px'; ring.style.top=ry+'px';
        requestAnimationFrame(anim);
    })();
}

function initHeader() {
    window.addEventListener('scroll', () => {
        document.getElementById('hdr').classList.toggle('scrolled', window.scrollY > 50);
    });
}

function initReveal() {
    const ro = new IntersectionObserver(es => es.forEach(e => { if(e.isIntersecting) e.target.classList.add('in')}), {threshold:.15});
    document.querySelectorAll('.reveal').forEach(el => ro.observe(el));
}

// ═══════════════════════════════════════════════════════════════════
//  PROPERTY ENGINE
// ═══════════════════════════════════════════════════════════════════
let ALL_PROPS = [];
let TAB = 'rent', TTYPE = '';

async function loadProperties() {
    try {
        const res = await fetch('data/properties.json');
        ALL_PROPS = await res.json();
        doFilter();
    } catch (e) { console.error("Error loading properties:", e); }
}

function setTab(t, btn) {
    TAB = t;
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    doFilter();
}

function tFilter(t, btn) {
    TTYPE = t;
    document.querySelectorAll('.tp').forEach(b => b.classList.remove('on'));
    btn.classList.add('on');
    doFilter();
}

function doFilter() {
    const type = TTYPE || document.getElementById('f-type')?.value.replace(/^[^\w]*/, '');
    const loc = document.getElementById('f-loc')?.value;
    const pr = document.getElementById('f-price')?.value;
    const beds = document.getElementById('f-beds')?.value;

    let list = ALL_PROPS.filter(p => {
        if(TAB === 'rent' && p.listing !== 'rent') return false;
        if(TAB === 'buy' && p.listing !== 'sale') return false;
        if(type && !p.type.includes(type)) return false;
        if(loc && p.loc !== loc) return false;
        if(beds && p.beds < +beds) return false;
        if(pr) {
            const [lo, hi] = pr.split('-').map(Number);
            if(p.price < lo || p.price > hi) return false;
        }
        return true;
    });

    list.sort((a, b) => (b.isFeatured === true) - (a.isFeatured === true));
    render(list);
}

function render(list) {
    const pg = document.getElementById('pg');
    if(!pg) return;
    document.getElementById('res-count').textContent = `${list.length} properties found`;
    
    pg.innerHTML = list.map((p, i) => `
        <div class="pc reveal ${p.isFeatured?'featured':''}" style="transition-delay:${i*.07}s">
            ${p.isFeatured ? '<div class="featured-badge">⭐ FEATURED</div>' : ''}
            <div class="pi">
                <span class="pi-em">${p.em}</span>
                <span class="pi-b1 ${p.listing==='rent'?'b-rent':'b-sale'}">${p.listing==='rent'?'For Rent':'For Sale'}</span>
                ${p.hot?'<span class="pi-hot">🔥 HOT</span>':''}
                ${p.tour ? '<div class="pi-tour" style="position:absolute;bottom:10px;right:10px;font-size:10px;background:#fff;padding:3px 8px;border-radius:4px">🔄 360° Tour</div>' : ''}
            </div>
            <div class="pb">
                <div class="pp">${p.listing==='rent' ? '$'+p.price.toLocaleString()+'<span>/mo</span>' : '$'+p.price.toLocaleString()}</div>
                <div class="pt">${p.title}</div>
                <div class="pl">📍 ${p.loc}</div>
                <div class="pd">${p.desc}</div>
                <div class="pf">
                    ${p.beds?`<span>🛏 ${p.beds}bd</span>`:''}
                    ${p.baths?`<span>🚿 ${p.baths}ba</span>`:''}
                    <span>📐 ${p.size}m²</span>
                    <span style="margin-left:auto;color:var(--gold)">${p.type}</span>
                </div>
            </div>
        </div>`).join('');
    
    document.querySelectorAll('.pc.reveal:not(.in)').forEach(el => {
        const ro = new IntersectionObserver(es => es.forEach(e => { if(e.isIntersecting) e.target.classList.add('in')}), {threshold:.15});
        ro.observe(el);
    });
}

function initProvinceGrid() {
    const grid = document.getElementById('prov-grid');
    if(!grid) return;
    const PROV = [
        {n:"Phnom Penh",e:"🏙️"},{n:"Siem Reap",e:"🛕"},{n:"Sihanoukville",e:"🏖️"},
        {n:"Battambang",e:"🌾"},{n:"Kampot",e:"🏞️"},{n:"Kep",e:"🦀"}
    ];
    grid.innerHTML = PROV.map(p => `
        <div class="prov" onclick="goProvince('${p.n}')">
            <span class="prov-em">${p.e}</span>
            <div><div class="prov-n">${p.n}</div><div class="prov-c">View Listings</div></div>
        </div>`).join('');
}

window.goProvince = function(n) {
    document.getElementById('f-loc').value = n;
    document.getElementById('properties').scrollIntoView({behavior:'smooth'});
    doFilter();
}

// ═══════════════════════════════════════════════════════════════════
//  BUSINESS TOOLS
// ═══════════════════════════════════════════════════════════════════
window.calcMortgage = function() {
    const P = parseFloat(document.getElementById('mort-amt').value) || 0;
    const r = (parseFloat(document.getElementById('mort-rate').value) || 0) / 100 / 12;
    const n = (parseFloat(document.getElementById('mort-year').value) || 0) * 12;
    const payment = (r === 0) ? P/n : P * (r * Math.pow(1+r, n)) / (Math.pow(1+r, n) - 1);
    document.getElementById('mort-res').textContent = `$${payment.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
}

window.calcValue = function() {
    const rate = parseFloat(document.getElementById('val-loc').value) || 0;
    const size = parseFloat(document.getElementById('val-size').value) || 0;
    document.getElementById('val-res').textContent = `$${(rate * size).toLocaleString()}`;
}

// ═══════════════════════════════════════════════════════════════════
//  CANVAS
// ═══════════════════════════════════════════════════════════════════
function initCanvas() {
    const canvas=document.getElementById('bg-canvas');
    const ctx=canvas.getContext('2d');
    let W, H, pts=[];
    function resize(){ W=canvas.width=canvas.offsetWidth; H=canvas.height=canvas.offsetHeight; initPts(); }
    function initPts(){ pts=Array.from({length:6},(_,i)=>({ x:Math.random()*W, y:Math.random()*H, vx:(Math.random()-.5)*.4, vy:(Math.random()-.5)*.4, r:300, hue:i%2===0?[200,168,90]:[14,32,52], a:.1 })); }
    function draw(){
        ctx.clearRect(0,0,W,H);
        ctx.fillStyle='#08111E'; ctx.fillRect(0,0,W,H);
        pts.forEach(p=>{
            const g=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r);
            const [r,g2,b]=p.hue;
            g.addColorStop(0,`rgba(${r},${g2},${b},${p.a})`); g.addColorStop(1,'rgba(0,0,0,0)');
            ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fillStyle=g; ctx.fill();
            p.x+=p.vx; p.y+=p.vy;
            if(p.x<-p.r||p.x>W+p.r) p.vx*=-1; if(p.y<-p.r||p.y>H+p.r) p.vy*=-1;
        });
        requestAnimationFrame(draw);
    }
    window.addEventListener('resize', resize); resize(); draw();
}