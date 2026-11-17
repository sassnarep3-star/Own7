/* OWN7 competition lab — suggestion decision controls.
 *
 * This file only records a reader's preference in their own browser. It never sends
 * anything, never changes a published value, and never implements a suggestion. If the
 * markup is absent the script does nothing at all.
 */
(function () {
  "use strict";

  var STORE = "own7-competition-decisions";
  var board = document.getElementById("decision-board");
  if (!board) { return; }

  var rows = [];
  try {
    rows = JSON.parse(board.getAttribute("data-choices") || "[]");
  } catch (err) {
    rows = [];
  }
  if (!rows.length) { return; }

  var saved = {};
  try {
    saved = JSON.parse(window.localStorage.getItem(STORE) || "{}");
  } catch (err) {
    saved = {};
  }

  function persist() {
    try {
      window.localStorage.setItem(STORE, JSON.stringify(saved));
    } catch (err) {
      /* Private browsing or a full store: the controls still work for this session. */
    }
  }

  function render() {
    board.textContent = "";
    rows.forEach(function (item) {
      var row = document.createElement("div");
      row.className = "decision-row";

      var id = document.createElement("span");
      id.className = "id";
      id.textContent = item.id;
      row.appendChild(id);

      var title = document.createElement("span");
      title.className = "title";
      title.textContent = item.title;
      row.appendChild(title);

      ["Adopt", "Defer", "Reject"].forEach(function (choice) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "btn";
        button.textContent = choice;
        button.setAttribute("aria-pressed", saved[item.id] === choice ? "true" : "false");
        button.addEventListener("click", function () {
          saved[item.id] = saved[item.id] === choice ? "" : choice;
          if (!saved[item.id]) { delete saved[item.id]; }
          persist();
          render();
        });
        row.appendChild(button);
      });

      board.appendChild(row);
    });
    var chosen = Object.keys(saved).filter(function (k) { return saved[k]; }).length;
    var note = document.createElement("p");
    note.className = "muted";
    note.textContent = chosen + " of " + rows.length + " suggestions have a choice "
      + "recorded. Nothing has been implemented: this is your preference, stored in your "
      + "browser only.";
    board.appendChild(note);
  }

  function download() {
    var payload = JSON.stringify({
      recorded_on: new Date().toISOString().slice(0, 10),
      note: "Reader preference only. No suggestion here has been implemented.",
      decisions: saved
    }, null, 2);
    var blob = new Blob([payload], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = "own7-suggestion-decisions.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  var exportButton = document.getElementById("export-decisions");
  if (exportButton) { exportButton.addEventListener("click", download); }

  var clearButton = document.getElementById("clear-decisions");
  if (clearButton) {
    clearButton.addEventListener("click", function () {
      saved = {};
      persist();
      render();
    });
  }

  render();
})();
