(function () {
  var themes = [["ocean", "Ocean"], ["sunset", "Sunset"], ["forest", "Forest"],
                ["midnight", "Midnight"], ["pastel", "Pastel"], ["custom", "My photo"]];
  var saved = "ocean";
  try { saved = localStorage.getItem("fi_theme") || "ocean"; } catch (e) {}
  if (!themes.some(function (t) { return t[0] === saved; })) saved = "ocean";

  function apply(name) {
    document.body.className = document.body.className.replace(/\bbg-\S+/g, "").trim();
    document.body.classList.add("bg-" + name);
    try { localStorage.setItem("fi_theme", name); } catch (e) {}
  }
  apply(saved);

  var old = document.querySelector(".hero, .appbar");
  while (old) { old.remove(); old = document.querySelector(".hero, .appbar"); }

  var id = null;
  var m = location.pathname.match(/[0-9a-f]{32}/);
  if (m) id = m[0];
  if (!id) {
    var links = document.querySelectorAll("a[href]");
    for (var i = 0; i < links.length && !id; i++) {
      var mm = (links[i].getAttribute("href") || "").match(/[0-9a-f]{32}/);
      if (mm) id = mm[0];
    }
  }

  var bar = document.createElement("div");
  bar.className = "appbar";
  var brand = document.createElement("div");
  var t1 = document.createElement("div"); t1.className = "brand-title"; t1.textContent = "Customer Feedback Intelligence";
  var t2 = document.createElement("div"); t2.className = "brand-sub"; t2.textContent = "Sentiment, analytics, RAG, AI analyst and predictions";
  brand.appendChild(t1); brand.appendChild(t2);
  var art = document.createElement("img");
  art.src = "/static/hero_art.svg"; art.alt = "";
  bar.appendChild(brand); bar.appendChild(art);

  var nav = document.createElement("nav");
  nav.className = "appnav";
  var items = [["Dashboard", "/", "/"]];
  if (id) {
    items.push(["RAG Assistant", "/rag/" + id, "/rag/"]);
    items.push(["AI Analyst", "/agent/" + id, "/agent/"]);
    items.push(["Predictions", "/predict/" + id, "/predict/"]);
  }
  items.forEach(function (it) {
    var a = document.createElement("a");
    a.href = it[1]; a.textContent = it[0];
    var p = location.pathname;
    var active = it[2] === "/" ? (p === "/" || p.indexOf("/download") === 0) : p.indexOf(it[2]) === 0;
    if (active) a.className = "active";
    nav.appendChild(a);
  });
  bar.appendChild(nav);
  document.body.insertBefore(bar, document.body.firstChild);

  var old2 = document.getElementById("themeBox");
  if (old2) old2.remove();
  var box = document.createElement("div");
  box.id = "themeBox";
  var label = document.createElement("label");
  label.textContent = "Theme: ";
  var sel = document.createElement("select");
  themes.forEach(function (t) {
    var o = document.createElement("option");
    o.value = t[0]; o.textContent = t[1];
    if (t[0] === saved) o.selected = true;
    sel.appendChild(o);
  });
  sel.addEventListener("change", function () { apply(sel.value); });
  label.appendChild(sel);
  box.appendChild(label);
  document.body.appendChild(box);
})();
