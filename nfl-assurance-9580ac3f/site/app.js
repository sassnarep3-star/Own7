
(function(){
  function rows(table){return Array.from(table.tBodies[0]?table.tBodies[0].rows:[]);}
  function apply(table){
    var search=document.querySelector('[data-search="'+table.id+'"]');
    var filters=Array.from(document.querySelectorAll('[data-filter="'+table.id+'"]'));
    var q=search?search.value.trim().toLowerCase():'';
    var visible=0;
    rows(table).forEach(function(tr){
      var ok=!q||tr.textContent.toLowerCase().indexOf(q)>=0;
      filters.forEach(function(sel){var key=sel.getAttribute('data-filter-key');var val=sel.value;if(val&&tr.getAttribute('data-'+key)!==val)ok=false;});
      tr.hidden=!ok;if(ok)visible++;
    });
    var count=document.querySelector('[data-count="'+table.id+'"]');if(count)count.textContent=visible+' / '+rows(table).length+' rows';
    var empty=document.querySelector('[data-empty-for="'+table.id+'"]');if(empty)empty.hidden=visible!==0;
  }
  document.querySelectorAll('table[id]').forEach(function(table){
    var search=document.querySelector('[data-search="'+table.id+'"]');if(search)search.addEventListener('input',function(){apply(table);});
    document.querySelectorAll('[data-filter="'+table.id+'"]').forEach(function(sel){sel.addEventListener('change',function(){apply(table);});});
    var exportBtn=document.querySelector('[data-export="'+table.id+'"]');
    if(exportBtn)exportBtn.addEventListener('click',function(){
      var headers=Array.from(table.tHead.rows[0].cells).map(function(th){return th.textContent.trim();});
      var lines=[headers.map(csv).join(',')];
      rows(table).filter(function(tr){return !tr.hidden;}).forEach(function(tr){lines.push(Array.from(tr.cells).map(function(td){return csv(td.textContent.trim());}).join(','));});
      download(table.id+'-visible.csv',lines.join('\r\n'),'text/csv');
    });
    apply(table);
  });
  function csv(value){return '"'+value.replace(/"/g,'""')+'"';}
  function download(name,text,type){var blob=new Blob([text],{type:type});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);}
  var key='nfl-assurance-shortlist-v1';
  function loadShortlist(){try{return JSON.parse(localStorage.getItem(key)||'[]');}catch(e){return [];}}
  function saveShortlist(list){try{localStorage.setItem(key,JSON.stringify(list));}catch(e){}}
  var boxes=Array.from(document.querySelectorAll('[data-shortlist]'));
  if(boxes.length){
    var list=loadShortlist();boxes.forEach(function(box){box.checked=list.indexOf(box.getAttribute('data-shortlist'))>=0;box.addEventListener('change',function(){var current=loadShortlist();var id=box.getAttribute('data-shortlist');if(box.checked&&current.indexOf(id)<0)current.push(id);if(!box.checked)current=current.filter(function(x){return x!==id;});saveShortlist(current);status();});});
    function status(){var el=document.getElementById('shortlist-status');if(el)el.textContent=loadShortlist().length+' shortlisted locally (not approval)';}
    var btn=document.getElementById('export-shortlist');if(btn)btn.addEventListener('click',function(){download('nfl-assurance-shortlist.json',JSON.stringify({shortlist:loadShortlist(),note:'Local preference only; not shared approval or implementation authorization.'},null,2),'application/json');});
    status();
  }
})();
