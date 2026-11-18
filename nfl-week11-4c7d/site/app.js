document.addEventListener('click',function(event){
  var trigger=event.target.closest('[data-sort]');
  if(!trigger)return;
  var table=trigger.closest('table');
  if(!table)return;
  var index=Number(trigger.dataset.sort);
  var body=table.tBodies[0];
  var rows=Array.prototype.slice.call(body.rows);
  var direction=trigger.dataset.direction==='asc'?'desc':'asc';
  trigger.dataset.direction=direction;
  rows.sort(function(a,b){
    var left=a.cells[index]?a.cells[index].textContent.trim():'';
    var right=b.cells[index]?b.cells[index].textContent.trim():'';
    var ln=parseFloat(left.replace(/[^0-9.\-]/g,'')),rn=parseFloat(right.replace(/[^0-9.\-]/g,''));
    if(!isNaN(ln)&&!isNaN(rn)&&left!==''&&right!==''&&/[-0-9.]/.test(left)&&/[-0-9.]/.test(right)){
      return direction==='asc'?ln-rn:rn-ln;
    }
    return direction==='asc'?left.localeCompare(right):right.localeCompare(left);
  });
  rows.forEach(function(r){body.appendChild(r);});
});
