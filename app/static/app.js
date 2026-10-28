/* VADA UI - one question box, one answer, and the sources behind it. */
(function () {
  "use strict";

  var form = document.getElementById("search-form");
  var input = document.getElementById("query");
  var submit = document.getElementById("submit");
  var chips = document.getElementById("chips");
  var versionSelect = document.getElementById("version");
  var results = document.getElementById("results");
  var hint = document.getElementById("hint");
  var answerBox = document.getElementById("answer");
  var cardBox = document.getElementById("cards");
  var modeBadge = document.getElementById("mode");
  var limit = 5;
  var CITATION_RE = /(\[\d+(?:\s*,\s*\d+)*\])/g;

  var REASONS = {
    model_not_found: "Nothing in the indexed documentation answers this question.",
    no_matches: "No indexed document matched this question.",
    invalid_citations:
      "The draft answer could not be traced to a retrieved source, so it was withheld.",
    generation_failed: "The language model was unavailable, so no generated answer is shown.",
  };

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

  /* Turn [1] and [1, 3] into links to the matching source cards. */
  function citationText(text) {
    var fragment = document.createDocumentFragment();

    text.split(CITATION_RE).forEach(function (part) {
      if (!part) return;

      var group = part.match(/^\[([\d,\s]+)\]$/);
      if (!group) {
        fragment.appendChild(richText(part));
        return;
      }

      fragment.appendChild(document.createTextNode("["));
      group[1]
        .split(",")
        .map(function (value) {
          return value.trim();
        })
        .filter(Boolean)
        .forEach(function (number, position) {
          if (position > 0) fragment.appendChild(document.createTextNode(", "));
          var link = el("a", "cite", number);
          link.href = "#source-" + number;
          link.setAttribute("aria-label", "Jump to source " + number);
          fragment.appendChild(link);
        });
      fragment.appendChild(document.createTextNode("]"));
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

  function payloadFor(query, questionKey) {
    var payload = { limit: limit };
    payload[questionKey] = query;
    if (versionSelect && versionSelect.value) payload.version = versionSelect.value;
    return payload;
  }

  function scopeLabel() {
    return versionSelect && versionSelect.value ? " in " + versionSelect.value : "";
  }

  function setBusy(isBusy) {
    results.setAttribute("aria-busy", isBusy ? "true" : "false");
    submit.disabled = isBusy;
    submit.textContent = isBusy ? "Searching" : "Search";
  }

  function setHint(text) {
    hint.textContent = text;
    hint.hidden = false;
  }

  function reset() {
    hint.hidden = true;
    hint.textContent = "";
    answerBox.hidden = true;
    answerBox.className = "answer";
    answerBox.textContent = "";
    cardBox.textContent = "";
  }

  function showMode(mode) {
    if (!mode) return;
    modeBadge.textContent = mode === "hybrid" ? "Hybrid search" : "Keyword search";
    modeBadge.hidden = false;
  }

  function sourceCard(source) {
    var item = el("li", "card");
    item.id = "source-" + source.index;

    var top = el("div", "card__top");
    top.appendChild(el("span", "card__cite", String(source.index)));
    top.appendChild(el("span", "badge badge--version", source.version || "unknown"));
    if (source.status) {
      var statusClass =
        source.status === "current" ? "badge badge--current" : "badge badge--superseded";
      top.appendChild(el("span", statusClass, source.status));
    }
    top.appendChild(el("span", "card__type", source.doc_type || "doc"));
    item.appendChild(top);

    item.appendChild(el("h2", "card__title", source.title || source.doc_id));

    var meta = [source.section, source.last_updated ? "Updated " + source.last_updated : ""]
      .filter(Boolean)
      .join(" - ");
    item.appendChild(el("p", "card__meta", meta));

    var body = el("p", "card__text");
    body.appendChild(richText(excerpt(source.text)));
    item.appendChild(body);

    var foot = el("div", "card__foot");
    var link = el("a", "card__link", "Open source");
    link.href = source.source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", "Open source: " + (source.title || source.doc_id));
    foot.appendChild(link);
    foot.appendChild(el("span", "card__score", "cited as [" + source.index + "]"));
    item.appendChild(foot);

    return item;
  }

  function renderSources(sources) {
    var list = el("ul", "cards");
    sources.forEach(function (source) {
      list.appendChild(sourceCard(source));
    });
    cardBox.appendChild(list);
  }

  function answerPanel(kind, body, meta, footText) {
    answerBox.className = "answer answer--" + (kind === "answered" ? "ok" : "miss");
    answerBox.textContent = "";

    var head = el("div", "answer__head");
    head.appendChild(
      el(
        "span",
        kind === "answered" ? "badge badge--answered" : "badge badge--miss",
        kind === "answered" ? "Answered" : "Not found",
      ),
    );
    if (meta) head.appendChild(el("span", "answer__meta", meta));
    answerBox.appendChild(head);

    var paragraph = el("p", "answer__body");
    if (typeof body === "string") {
      paragraph.textContent = body;
    } else {
      paragraph.appendChild(body);
    }
    answerBox.appendChild(paragraph);

    if (footText) answerBox.appendChild(el("p", "answer__foot", footText));
    answerBox.hidden = false;
  }

  function renderAnswer(data, query) {
    reset();
    showMode(data.mode);

    var sources = data.sources || [];

    if (data.status !== "answered") {
      setHint("No verified answer for \u201c" + query + "\u201d" + scopeLabel());
      answerPanel(
        "not_found",
        REASONS[data.reason] || REASONS.model_not_found,
        "",
        "The answer was withheld rather than guessed.",
      );
      return;
    }

    setHint(
      sources.length +
        (sources.length === 1 ? " source" : " sources") +
        scopeLabel() +
        " for \u201c" +
        query +
        "\u201d",
    );

    var versions = sources
      .map(function (source) {
        return source.version;
      })
      .filter(function (version, index, all) {
        return version && all.indexOf(version) === index;
      })
      .join(", ");

    answerPanel(
      "answered",
      citationText(data.answer),
      [versions, data.mode === "hybrid" ? "hybrid" : "keyword"].filter(Boolean).join(" \u00b7 "),
      (data.model || "extractive") + " \u00b7 every claim is cited",
    );
    renderSources(sources);
  }

  function renderLoading() {
    reset();
    setHint("Reading the documentation...");

    var list = el("div", "cards");
    for (var i = 0; i < 2; i += 1) {
      list.appendChild(el("div", "skeleton"));
    }
    cardBox.appendChild(list);
  }

  function renderFailure() {
    reset();
    setHint("The service did not respond");

    var empty = el("div", "empty");
    empty.appendChild(el("h2", "error", "Something went wrong"));
    empty.appendChild(
      el("p", null, "Check that the API is running, then try again. Nothing was saved."),
    );
    cardBox.appendChild(empty);
  }

  /* If /api/ask is unavailable, fall back to plain retrieval so the page is
     still useful instead of blank. */
  async function fallbackSearch(query) {
    try {
      var response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payloadFor(query, "query")),
      });
      if (!response.ok) throw new Error("HTTP " + response.status);

      var data = await response.json();
      reset();
      showMode(data.mode);
      setHint(
        "Answer unavailable - showing " + data.count + " matching documents" + scopeLabel(),
      );
      renderSources(data.results || []);
    } catch (error) {
      renderFailure();
    }
  }

  async function search(query) {
    setBusy(true);
    renderLoading();

    try {
      var response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payloadFor(query, "question")),
      });

      if (!response.ok) throw new Error("HTTP " + response.status);

      renderAnswer(await response.json(), query);
    } catch (error) {
      await fallbackSearch(query);
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
