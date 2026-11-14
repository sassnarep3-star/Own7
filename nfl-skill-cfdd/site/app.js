/* Skill desk: the only client-side behaviour is exporting a preference file.
   Nothing on any page computes a published value; every number is baked in by build.py. */
(function () {
  'use strict';
  var btn = document.getElementById('export-choices');
  if (!btn) { return; }
  btn.addEventListener('click', function () {
    var ids = Array.prototype.slice.call(document.querySelectorAll('input[type=radio]'))
      .map(function (r) { return r.name.replace(/^d-/, ''); })
      .filter(function (v, i, a) { return a.indexOf(v) === i; });
    var lines = ['suggestion_id,decision,reason'];
    ids.forEach(function (id) {
      var picked = document.querySelector('input[name="d-' + id + '"]:checked');
      var reasonEl = picked && picked.closest('td')
        ? picked.closest('td').querySelector('.reason') : null;
      function esc(v) { return '"' + String(v || '').replace(/"/g, '""') + '"'; }
      lines.push([esc(id), esc(picked ? picked.value : ''), esc(reasonEl ? reasonEl.value : '')].join(','));
    });
    var blob = new Blob([lines.join('\n') + '\n'], { type: 'text/csv' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'own7-skill-desk-choices.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  });
}());
