
(function(){
  function rows(table){return Array.from(table.tBodies[0]?table.tBodies[0].rows:[]);}
  function apply(table){
    var search=document.querySelector('[data-search="'+table.id+'"]');
    var filters=Array.from(document.querySelectorAll('[data-filter="'+table.id+'"]'));
    var q=search?search.value.trim().toLowerCase():'';
    var visible=0;
    rows(table).forEach(function(tr){
      var ok=!q||tr.textContent.toLowerCase().indexOf(q)>=0;
      filters.forEach(function(sel){
        var key=sel.getAttribute('data-filter-key');var val=sel.value;
        if(!val)return;
        if(key==='status'&&val==='none published'){if((tr.getAttribute('data-status')||'')!=='')ok=false;return;}
        if(key==='status'&&tr.hasAttribute('data-choice')){
          if((tr.getAttribute('data-path')||'no choice recorded')!==val)ok=false;return;
        }
        if(tr.getAttribute('data-'+key)!==val)ok=false;
      });
      tr.hidden=!ok;if(ok)visible++;
    });
    var count=document.querySelector('[data-count="'+table.id+'"]');
    if(count)count.textContent=visible+' / '+rows(table).length+' rows';
    var empty=document.querySelector('[data-empty-for="'+table.id+'"]');
    if(empty)empty.hidden=visible!==0;
  }
  document.querySelectorAll('table[id]').forEach(function(table){
    var search=document.querySelector('[data-search="'+table.id+'"]');
    if(search)search.addEventListener('input',function(){apply(table);});
    document.querySelectorAll('[data-filter="'+table.id+'"]').forEach(function(sel){
      sel.addEventListener('change',function(){apply(table);});});
    var exportBtn=document.querySelector('[data-export="'+table.id+'"]');
    if(exportBtn)exportBtn.addEventListener('click',function(){
      var headers=Array.from(table.tHead.rows[0].cells).map(function(th){return th.textContent.trim();});
      var lines=[headers.map(csv).join(',')];
      rows(table).filter(function(tr){return !tr.hidden;}).forEach(function(tr){
        lines.push(Array.from(tr.cells).map(function(td){return csv(td.textContent.trim());}).join(','));});
      download(table.id+'-visible.csv',lines.join('\r\n'),'text/csv');
    });
    apply(table);
  });
  function csv(value){return '"'+value.replace(/"/g,'""')+'"';}
  function download(name,text,type){var blob=new Blob([text],{type:type});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);}

  // ---- suggestion review workflow (local preference only) -------------------
  var key='nfl-availability-28ef-decisions-v1';
  var choices=Array.from(document.querySelectorAll('[data-choice]'));
  var reasons=Array.from(document.querySelectorAll('[data-reason]'));
  function load(){try{return JSON.parse(localStorage.getItem(key)||'{}');}catch(e){return {};}}
  function save(state){try{localStorage.setItem(key,JSON.stringify(state));}catch(e){}}
  function pathOf(id){var state=load();return (state[id]&&state[id].path)||'';}
  function status(){
    var el=document.getElementById('decision-status');if(!el)return;
    var state=load();var n=Object.keys(state).filter(function(k){return state[k]&&state[k].path;}).length;
    el.textContent=n+' of '+choices.length+' proposals have a path recorded in this browser. '
      +'Local preference only: this does not implement anything or change published data.';
  }
  function paint(){
    choices.forEach(function(input){
      var id=input.getAttribute('data-choice');
      input.checked=pathOf(id)===input.value;
    });
    reasons.forEach(function(input){
      var id=input.getAttribute('data-reason');var state=load();
      input.value=(state[id]&&state[id].reason)||'';
    });
    document.querySelectorAll('tr[data-source-ids]').forEach(function(tr){
      var input=tr.querySelector('[data-choice]');
      if(!input)return;
      var path=pathOf(input.getAttribute('data-choice'))||'no choice recorded';
      tr.setAttribute('data-path',path);
    });
    status();
    var table=document.getElementById('tbl-suggestions');
    if(table)apply(table);
  }
  choices.forEach(function(input){
    input.addEventListener('change',function(){
      var id=input.getAttribute('data-choice');var state=load();
      state[id]=Object.assign({},state[id],{path:input.value});
      save(state);paint();
    });
  });
  reasons.forEach(function(input){
    input.addEventListener('input',function(){
      var id=input.getAttribute('data-reason');var state=load();
      state[id]=Object.assign({},state[id],{reason:input.value});
      save(state);
    });
  });
  var exportBtn=document.getElementById('export-decisions');
  if(exportBtn)exportBtn.addEventListener('click',function(){
    download('availability-desk-decisions.json',JSON.stringify({
      desk:'nfl-availability-28ef',checked_on:'2026-11-13',decisions:load(),
      note:'Local review preference only. Not approval, not authorisation, not an implementation record.'
    },null,2),'application/json');
  });
  var clearBtn=document.getElementById('clear-decisions');
  if(clearBtn)clearBtn.addEventListener('click',function(){save({});paint();});
  paint();
})();
