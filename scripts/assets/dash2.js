var tb=document.getElementById('tb');
tb.addEventListener('click',function(ev){
  var b=ev.target.closest('button');if(!b)return;
  [].forEach.call(tb.children,function(x){x.className=''});
  b.className='on';
  var v=b.getAttribute('data-v');
  [].forEach.call(document.querySelectorAll('.sec'),function(s){s.className='sec'+(s.id==v?' on':'')});
  try{window.scrollTo({top:0,behavior:'smooth'})}catch(e){window.scrollTo(0,0)}
});
var q=document.getElementById('q'),kf=document.getElementById('kf'),sk=document.getElementById('sk');
function apply(){
  var rows=[].slice.call(document.querySelectorAll('#db tr'));
  var s=(q.value||'').toLowerCase();
  var k=kf.value;
  var shown=0;
  rows.forEach(function(r){
    var ok=true;
    if(k&&r.getAttribute('data-k')!=k)ok=false;
    if(ok&&s&&(r.getAttribute('data-txt')||'').toLowerCase().indexOf(s)<0)ok=false;
    r.style.display=ok?'':'none';
    if(ok)shown++;
  });
  document.getElementById('cnt').textContent='命中 '+shown+' 只 / 共 '+rows.length+' 只';
}
function sortBy(){
  var key=sk.value;
  var tb2=document.getElementById('db');
  var rows=[].slice.call(tb2.querySelectorAll('tr'));
  rows.sort(function(a,b){
    if(key=='d')return a.getAttribute('data-d')>b.getAttribute('data-d')?-1:1;
    var x=parseFloat(a.getAttribute(key=='cum'?'data-cum':'data-d1'));
    var y=parseFloat(b.getAttribute(key=='cum'?'data-cum':'data-d1'));
    return y-x;
  });
  rows.forEach(function(r){tb2.appendChild(r)});
}
if(q)q.addEventListener('input',apply);
if(kf)kf.addEventListener('change',apply);
if(sk)sk.addEventListener('change',function(){sortBy();apply()});
