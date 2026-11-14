(() => {
  const tables = [...document.querySelectorAll('table[id]')];

  function updateCount(table) {
    const card = table.closest('[data-table-card]');
    const visible = [...table.tBodies[0].rows].filter(row => !row.hidden).length;
    const count = card.querySelector('.row-count');
    const empty = card.querySelector('[data-empty-for]');
    count.textContent = `${visible} of ${table.tBodies[0].rows.length} rows`;
    empty.hidden = visible !== 0;
  }

  for (const table of tables) {
    const card = table.closest('[data-table-card]');
    const input = card.querySelector('[data-search-for]');
    input.addEventListener('input', () => {
      const needle = input.value.trim().toLocaleLowerCase();
      for (const row of table.tBodies[0].rows) {
        row.hidden = !row.textContent.toLocaleLowerCase().includes(needle);
      }
      updateCount(table);
    });

    for (const button of table.querySelectorAll('thead button[data-sort]')) {
      button.addEventListener('click', () => {
        const index = Number(button.dataset.sort);
        const header = button.closest('th');
        const ascending = header.getAttribute('aria-sort') !== 'ascending';
        const rows = [...table.tBodies[0].rows];
        const value = row => {
          const cell = row.cells[index];
          if (cell.dataset.value !== undefined) return Number(cell.dataset.value);
          return cell.textContent.trim().toLocaleLowerCase();
        };
        rows.sort((a, b) => {
          const left = value(a);
          const right = value(b);
          const compared = typeof left === 'number' && typeof right === 'number'
            ? left - right
            : String(left).localeCompare(String(right), undefined, {numeric: true, sensitivity: 'base'});
          return ascending ? compared : -compared;
        });
        for (const row of rows) table.tBodies[0].append(row);
        for (const other of table.querySelectorAll('thead th')) other.setAttribute('aria-sort', 'none');
        header.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
      });
    }
    updateCount(table);
  }

  function csvCell(value) {
    return `"${String(value).replaceAll('"', '""')}"`;
  }

  for (const button of document.querySelectorAll('[data-export]')) {
    button.addEventListener('click', () => {
      const table = document.getElementById(button.dataset.export);
      const rows = [...table.querySelectorAll('tr')].filter(row => !row.hidden);
      const lines = rows.map(row => [...row.cells].map(cell => {
        const links = [...cell.querySelectorAll('a')].map(link => link.href);
        const text = cell.hasAttribute('data-empty') ? '' : cell.textContent.trim();
        return csvCell([text, ...links].filter(Boolean).join(' '));
      }).join(','));
      const blob = new Blob([lines.join('\r\n') + '\r\n'], {type: 'text/csv;charset=utf-8'});
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${table.id}.csv`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    });
  }
})();
