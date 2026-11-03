/* Own7 NBA Lines — table sorting helpers */
(function () {
  function parseCell(v) {
    var t = String(v).trim().replace(/,/g, "");
    var n = Number(t);
    return !isNaN(n) ? n : t.toLowerCase();
  }
  function sortTable(table, colIndex) {
    var tbody = table.tBodies[0];
    var rows = Array.from(tbody.rows);
    var dir = table.dataset.sortDir === String(colIndex) && table.dataset.sortAsc === "true" ? -1 : 1;
    var isNumeric = true;
    for (var i = 0; i < Math.min(rows.length, 10); i++) {
      var c = rows[i].cells[colIndex];
      if (c && isNaN(parseCell(c.textContent)) && c.textContent.trim() !== "") { isNumeric = false; break; }
    }
    rows.sort(function (a, b) {
      var x = parseCell(a.cells[colIndex].textContent);
      var y = parseCell(b.cells[colIndex].textContent);
      if (isNumeric) { return (x - y) * dir; }
      return String(x).localeCompare(String(y), undefined, { numeric: true }) * dir;
    });
    rows.forEach(function (r) { tbody.appendChild(r); });
    table.dataset.sortDir = colIndex;
    table.dataset.sortAsc = dir === 1 ? "true" : "false";
  }
  document.querySelectorAll("table").forEach(function (table) {
    var headers = table.querySelectorAll("th");
    headers.forEach(function (th, i) {
      th.classList.add("sort");
      th.addEventListener("click", function () { sortTable(table, i); });
    });
  });
})();
