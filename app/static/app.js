/* VADA search UI - one form, one endpoint, no framework. */
(function () {
  "use strict";

  var form = document.getElementById("search-form");
  var input = document.getElementById("query");
  var submit = document.getElementById("submit");
  var chips = document.getElementById("chips");
  var results = document.getElementById("results");
  var modeBadge = document.getElementById("mode");
  var limit = 5;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* Render `code spans` from chunk text without injecting HTML. */
  function richText(text) {
    var fragment = document.createDocumentFragment();
    text.split(/`([^`]+)`/).forEach(function (part, index) {
      if (!part) return;
      if (index % 2 === 1) {
        fragment.appendChild(el("code", null, part));
      } else {
        fragment.appendChild(document.createTextNode(part));
      }
    });
    return fragment;
  }

  function excerpt(text) {
    var lines = (text || "").split("\n");
    var kept = [];

    lines.forEach(function (line) {
      var value = line.trim();
      if (!value) return;

      /* Drop markdown table separator rows: |---|---| */
      if (/^\|?[\s:|-]+\|[\s:|-]*$/.test(value)) return;

      /* Flatten a table row into a readable sentence fragment. */
      if (value.charAt(0) === "|") {
        value = value
          .replace(/^\||\|$/g, "")
          .split("|")
          .map(function (cell) {
            return cell.trim();
          })
          .filter(Boolean)
          .join(" \u00b7 ");
      }

      kept.push(value.replace(/^#+\s*/, ""));
    });

    var flat = kept.join(" ").replace(/\s+/g, " ").trim();
    if (flat.length <= 280) return flat;
    return flat.slice(0, 280).replace(/\s+\S*$/, "") + "...";
  }

  function setBusy(isBusy) {
    results.setAttribute("aria-busy", isBusy ? "true" : "false");
    submit.disabled = isBusy;
    submit.textContent = isBusy ? "Searching" : "Search";
  }

  function clearResults() {
    while (results.firstChild) results.removeChild(results.firstChild);
  }

  function showMode(mode) {
    if (!mode) return;
    modeBadge.textContent = mode === "hybrid" ? "Hybrid search" : "Keyword search";
    modeBadge.hidden = false;
  }

  function sourceCard(result) {
    var item = el("li", "card");

    var top = el("div", "card__top");
    top.appendChild(el("span", "badge badge--version", result.version || "unknown"));
    if (result.status) {
      var statusClass =
        result.status === "current" ? "badge badge--current" : "badge badge--superseded";
      top.appendChild(el("span", statusClass, result.status));
    }
    top.appendChild(el("span", "card__type", result.doc_type || "doc"));
    item.appendChild(top);

    item.appendChild(el("h2", "card__title", result.title || result.doc_id));

    var meta = [result.section, result.last_updated ? "Updated " + result.last_updated : ""]
      .filter(Boolean)
      .join(" - ");
    item.appendChild(el("p", "card__meta", meta));

    var body = el("p", "card__text");
    body.appendChild(richText(excerpt(result.text)));
    item.appendChild(body);

    var foot = el("div", "card__foot");
    var link = el("a", "card__link", "Open source");
    link.href = result.source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", "Open source: " + (result.title || result.doc_id));
    foot.appendChild(link);

    var via = el("span", "card__score");
    via.textContent =
      result.matched_by === "both"
        ? "keyword + vector"
        : (result.matched_by || "keyword") + " match";
    foot.appendChild(via);
    item.appendChild(foot);

    return item;
  }

  function renderResults(data, query) {
    clearResults();
    showMode(data.mode);

    var summary = el("div", "summary");
    var count = el("span");
    count.appendChild(el("strong", null, String(data.count)));
    count.appendChild(
      document.createTextNode(
        " " + (data.count === 1 ? "result" : "results") + " for \u201c" + query + "\u201d",
      ),
    );
    summary.appendChild(count);
    summary.appendChild(el("span", null, "versioned documentation"));
    results.appendChild(summary);

    if (!data.results || data.results.length === 0) {
      var empty = el("div", "empty");
      empty.appendChild(el("h2", null, "No matches in the indexed docs"));
      empty.appendChild(
        el(
          "p",
          null,
          "Try different wording. The corpus covers users, authentication, pagination, webhooks, errors, and rate limits.",
        ),
      );
      results.appendChild(empty);
      return;
    }

    var list = el("ul", "cards");
    data.results.forEach(function (result) {
      list.appendChild(sourceCard(result));
    });
    results.appendChild(list);
  }

  function renderError() {
    clearResults();
    var box = el("div", "empty");
    box.appendChild(el("h2", "error", "The search service did not respond"));
    box.appendChild(
      el("p", null, "Check that the API is running, then try again. No results were changed."),
    );
    results.appendChild(box);
  }

  function renderLoading() {
    clearResults();
    var summary = el("div", "summary");
    summary.appendChild(el("span", null, "Searching the documentation..."));
    results.appendChild(summary);

    var list = el("div", "cards");
    for (var i = 0; i < 3; i += 1) {
      list.appendChild(el("div", "skeleton"));
    }
    results.appendChild(list);
  }

  async function search(query) {
    setBusy(true);
    renderLoading();

    try {
      var response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, limit: limit }),
      });

      if (!response.ok) throw new Error("HTTP " + response.status);

      renderResults(await response.json(), query);
    } catch (error) {
      renderError();
    } finally {
      setBusy(false);
    }
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var query = input.value.trim();
    if (!query) {
      input.focus();
      return;
    }
    search(query);
  });

  chips.addEventListener("click", function (event) {
    var chip = event.target.closest(".chip");
    if (!chip) return;
    input.value = chip.getAttribute("data-query");
    search(input.value);
    input.focus();
  });
})();
