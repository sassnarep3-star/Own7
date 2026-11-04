/* Progressive enhancement only. Observations, tables, sources and flags are pre-rendered. */
(() => {
  'use strict';
  const pageSearch = document.querySelector('#page-search');
  const normalized = value => String(value).toLocaleLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim();
  const states = new Map();
  document.querySelectorAll('table[data-research-table]').forEach(table => {
    const input = document.querySelector(`[data-search-for="${table.id}"]`);
    const status = document.querySelector(`[data-status-filter="${table.id}"]`);
    const state = {table, rows: Array.from(table.tBodies[0].rows), input, status, column: null, direction: 1};
    states.set(table.id, state);
    state.apply = () => {
      const global = normalized(pageSearch?.value || '');
      const local = normalized(input?.value || '');
      const selected = status?.value || '';
      let visible = 0;
      state.rows.forEach(row => {
        const content = normalized(row.textContent);
        const match = (!global || content.includes(global)) && (!local || content.includes(local)) && (!selected || row.dataset.status === selected);
        row.hidden = !match;
        if (match) visible++;
      });
      const count = document.querySelector(`[data-count-for="${table.id}"]`);
      if (count) count.textContent = `${visible} of ${state.rows.length} entries`;
      const empty = document.querySelector(`[data-empty-for="${table.id}"]`);
      if (empty) empty.hidden = visible !== 0;
    };
    input?.addEventListener('input', state.apply);
    status?.addEventListener('change', state.apply);
    table.querySelectorAll('th button[data-sort]').forEach(button => {
      button.addEventListener('click', () => {
        const column = Number(button.dataset.sort);
        state.direction = state.column === column ? -state.direction : 1;
        state.column = column;
        table.querySelectorAll('th').forEach(th => th.setAttribute('aria-sort', 'none'));
        button.closest('th').setAttribute('aria-sort', state.direction === 1 ? 'ascending' : 'descending');
        table.querySelectorAll('.sort-mark').forEach(mark => mark.textContent = '↕');
        button.querySelector('.sort-mark').textContent = state.direction === 1 ? '↑' : '↓';
        state.rows.sort((a, b) => {
          const x = a.cells[column], y = b.cells[column];
          // Missing values stay last in BOTH directions; never coerce blank to zero.
          if (x.dataset.empty && y.dataset.empty) return 0;
          if (x.dataset.empty) return 1;
          if (y.dataset.empty) return -1;
          if (x.dataset.value !== undefined && y.dataset.value !== undefined) {
            return (Number(x.dataset.value) - Number(y.dataset.value)) * state.direction;
          }
          return normalized(x.textContent).localeCompare(normalized(y.textContent), undefined, {numeric: true}) * state.direction;
        });
        state.rows.forEach(row => table.tBodies[0].appendChild(row));
        state.apply();
      });
    });
    state.apply();
  });
  pageSearch?.addEventListener('input', () => states.forEach(state => state.apply()));

  const csvCell = raw => {
    let text = String(raw).replace(/\s+/g, ' ').trim();
    // Prevent exported prose from being interpreted as a spreadsheet formula.
    if (/^[=+@-]/.test(text) && !/^[+-]?\d+(\.\d+)?$/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  document.querySelectorAll('[data-export]').forEach(button => {
    button.addEventListener('click', () => {
      const state = states.get(button.dataset.export);
      if (!state) return;
      const head = Array.from(state.table.tHead.rows[0].cells).map(cell => csvCell(cell.textContent.replace(/[↕↑↓]/g, '')));
      const rows = state.rows.filter(row => !row.hidden).map(row => Array.from(row.cells).map(cell => {
        const links = Array.from(cell.querySelectorAll('a'));
        return csvCell(links.length && cell.classList.contains('refs') ? links.map(a => a.href).join(' ; ') : cell.textContent);
      }).join(','));
      const blob = new Blob(['\uFEFF' + [head.join(','), ...rows].join('\r\n')], {type: 'text/csv;charset=utf-8'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `own7-${state.table.id}-snapshot.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    });
  });

  const toggle = document.querySelector('.menu-button');
  const aside = document.querySelector('#sidebar');
  const backdrop = document.querySelector('.nav-backdrop');
  const mobile = window.matchMedia('(max-width: 760px)');
  let navOpen = false;
  function setNavigation(open, returnFocus = false) {
    navOpen = open && mobile.matches;
    document.body.classList.toggle('nav-open', navOpen);
    toggle?.setAttribute('aria-expanded', String(navOpen));
    toggle?.setAttribute('aria-label', navOpen ? 'Close navigation' : 'Open navigation');
    if (aside) {
      aside.inert = mobile.matches && !navOpen;
      if (mobile.matches && !navOpen) aside.setAttribute('aria-hidden', 'true');
      else aside.removeAttribute('aria-hidden');
    }
    if (backdrop) backdrop.hidden = !navOpen;
    if (navOpen) aside?.querySelector('a')?.focus();
    else if (returnFocus) toggle?.focus();
  }
  toggle?.addEventListener('click', () => setNavigation(!navOpen, navOpen));
  backdrop?.addEventListener('click', () => setNavigation(false, true));
  aside?.querySelectorAll('nav a').forEach(a => a.addEventListener('click', () => setNavigation(false)));
  mobile.addEventListener('change', () => setNavigation(false));
  setNavigation(false);
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
      event.preventDefault();
      pageSearch?.focus();
    }
    if (event.key === 'Escape') {
      if (navOpen) setNavigation(false, true);
      else if (document.activeElement === pageSearch) {
        pageSearch.value = '';
        states.forEach(state => state.apply());
        pageSearch.blur();
      }
    }
    if (event.key === 'Tab' && navOpen && aside) {
      const focusables = Array.from(aside.querySelectorAll('a, button, input, [tabindex="0"]')).filter(node => !node.hidden);
      const first = focusables[0], last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last?.focus();}
      if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first?.focus();}
    }
  });
})();
