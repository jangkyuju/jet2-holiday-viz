/* Jet2 Holiday charts + interactions (D3 v7). Fare numbers come from the team
   process book; state medians are clearly-marked layout SAMPLES until the team
   pastes real values (see STATE_FARES below). All code is original. */
(function () {
  "use strict";
  if (typeof d3 === "undefined") {
    document.querySelectorAll(".vis-container").forEach(function (el) {
      el.innerHTML = "<p>Charts need D3 from CDN (offline?). Reconnect and reload.</p>";
    });
    return;
  }
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- tooltip ---------- */
  var tip = d3.select("#tip");
  function showTip(html, x, y) {
    tip.html(html).attr("hidden", null);
    tip.style("left", Math.min(window.innerWidth - 272, x + 14) + "px")
       .style("top", Math.max(8, y - 90) + "px");
  }
  function hideTip() { tip.attr("hidden", true); }
  function svg(el, W, H) {
    return d3.select(el).html("").append("svg")
      .attr("viewBox", "0 0 " + W + " " + H).attr("role", "img");
  }
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* ---------- dot nav ---------- */
  (function () {
    var nav = document.getElementById("dots");
    var secs = Array.prototype.slice.call(document.querySelectorAll("#fullpage .section"));
    secs.forEach(function (s, i) {
      var a = document.createElement("a");
      a.href = "#" + s.id;
      a.title = s.dataset.label || ("Section " + (i + 1));
      a.setAttribute("aria-label", a.title);
      nav.appendChild(a);
    });
    var links = nav.querySelectorAll("a");
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          var idx = secs.indexOf(en.target);
          links.forEach(function (l, i) { l.classList.toggle("active", i === idx); });
        }
      });
    }, { threshold: 0.45 });
    secs.forEach(function (s) { io.observe(s); });
  })();

  /* ---------- title canvas: stars + clouds + flights ---------- */
  (function () {
    var cv = document.getElementById("title-canvas");
    if (!cv) return;
    var ctx = cv.getContext("2d"), W, H, planes = [], clouds = [];
    function size() {
      var r = cv.parentElement.getBoundingClientRect();
      W = cv.width = r.width; H = cv.height = r.height;
    }
    size(); window.addEventListener("resize", size);
    function spawn(init) {
      return { x: init ? Math.random() * W : -60, y: Math.random() * H * 0.8,
        v: 0.6 + Math.random() * 1.4, s: 0.6 + Math.random() * 0.9, wob: Math.random() * 6.28 };
    }
    for (var i = 0; i < 7; i++) planes.push(spawn(true));
    for (var c = 0; c < 9; c++) clouds.push({ x: Math.random(), y: 0.3 + Math.random() * 0.52, s: 30 + Math.random() * 70, v: 0.0002 + Math.random() * 0.0005 });
    var stars = [];
    for (var st = 0; st < 80; st++) stars.push({ x: Math.random(), y: Math.random() * 0.36,
      r: 0.6 + Math.random() * 1.7, p: Math.random() * 6.28, sp: 0.5 + Math.random() * 2 });
    function drawPlane(x, y, s, t, seed) {
      var bob = Math.sin(t / 700 + seed) * 5;
      ctx.save(); ctx.translate(x, y + bob); ctx.scale(s, s); ctx.rotate(-0.25);
      ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(255,255,255,0.35)"; ctx.lineWidth = 7;
      ctx.beginPath(); ctx.moveTo(-34, 3); ctx.lineTo(-80, 9); ctx.stroke();
      ctx.strokeStyle = "rgba(255,255,255,0.8)"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(-30, 2); ctx.lineTo(-95, 10); ctx.stroke();
      ctx.fillStyle = "#0b2540";
      ctx.beginPath();
      ctx.moveTo(-24, -2); ctx.lineTo(-16, -16); ctx.lineTo(-9, -16); ctx.lineTo(-8, -2);
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#ffd200"; ctx.strokeStyle = "#06182c"; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(-26, -2); ctx.lineTo(12, -5);
      ctx.quadraticCurveTo(26, -4, 28, 0);
      ctx.quadraticCurveTo(26, 4, 12, 5);
      ctx.lineTo(-24, 4);
      ctx.quadraticCurveTo(-29, 1, -26, -2);
      ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#e0a800"; ctx.strokeStyle = "#06182c";
      ctx.beginPath();
      ctx.moveTo(-2, 4); ctx.lineTo(-14, 16); ctx.lineTo(-6, 16); ctx.lineTo(8, 5);
      ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(-22, 3); ctx.lineTo(-28, 9); ctx.lineTo(-23, 9); ctx.lineTo(-17, 4);
      ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#0b2540";
      [16, 10, 4].forEach(function (wx) { ctx.beginPath(); ctx.arc(wx, -1, 1.8, 0, 6.29); ctx.fill(); });
      ctx.restore();
    }
    function cloud(cx, cy, s) {
      ctx.fillStyle = "rgba(170,192,208,0.9)";
      ctx.beginPath(); ctx.ellipse(cx, cy + s * 0.22, s * 0.62, s * 0.2, 0, 0, 6.29); ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.95)";
      ctx.beginPath();
      ctx.arc(cx - s * 0.42, cy, s * 0.3, 0, 6.29);
      ctx.arc(cx - s * 0.1, cy - s * 0.2, s * 0.38, 0, 6.29);
      ctx.arc(cx + s * 0.28, cy - s * 0.08, s * 0.3, 0, 6.29);
      ctx.arc(cx + s * 0.05, cy + s * 0.1, s * 0.36, 0, 6.29);
      ctx.fill();
    }
    var last = 0;
    function frame(t) {
      if (t - last < 33) { requestAnimationFrame(frame); return; }
      last = t;
      ctx.clearRect(0, 0, W, H);
      var g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, "#0b2540"); g.addColorStop(0.65, "#274f78"); g.addColorStop(1, "#7fb6d9");
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      stars.forEach(function (s0) {
        var tw = 0.35 + 0.65 * Math.abs(Math.sin(t * s0.sp / 900 + s0.p));
        ctx.globalAlpha = tw * (1 - (s0.y / 0.36) * 0.55);
        ctx.fillStyle = "#ffffff";
        var sx = s0.x * W, sy = s0.y * H;
        ctx.beginPath(); ctx.arc(sx, sy, s0.r, 0, 6.29); ctx.fill();
        if (s0.r > 1.6) {
          ctx.fillRect(sx - s0.r * 3, sy - 0.75, s0.r * 6, 1.5);
          ctx.fillRect(sx - 0.75, sy - s0.r * 3, 1.5, s0.r * 6);
        }
        ctx.globalAlpha = 1;
      });
      clouds.forEach(function (cl) {
        cl.x += cl.v * 16; if (cl.x > 1.15) cl.x = -0.15;
        cloud(cl.x * W, cl.y * H, cl.s);
      });
      ctx.fillStyle = "#06182c"; ctx.fillRect(0, H - 26, W, 26);
      planes.forEach(function (p, idx) {
        p.x += p.v; p.wob += 0.02;
        if (p.x > W + 60) planes[idx] = spawn(false); else drawPlane(p.x, p.y, p.s, t + idx * 300, idx * 1.7);
      });
      requestAnimationFrame(frame);
    }
    if (reduceMotion) {
      size();
      var g0 = ctx.createLinearGradient(0, 0, 0, H);
      g0.addColorStop(0, "#0b2540"); g0.addColorStop(0.65, "#274f78"); g0.addColorStop(1, "#7fb6d9");
      ctx.fillStyle = g0; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = "#ffffff";
      stars.forEach(function (s0) {
        ctx.globalAlpha = 0.8 * (1 - (s0.y / 0.36) * 0.55);
        ctx.beginPath(); ctx.arc(s0.x * W, s0.y * H, s0.r, 0, 6.29); ctx.fill();
      });
      ctx.globalAlpha = 1;
      clouds.forEach(function (cl) { cloud(cl.x * W, cl.y * H, cl.s); });
      ctx.fillStyle = "#06182c"; ctx.fillRect(0, H - 26, W, 26);
      planes.forEach(function (p, idx) { drawPlane(p.x, p.y, p.s, 0, idx * 1.7); });
    } else requestAnimationFrame(frame);
  })();

  /* ---------- scroll-driven hero plane (title -> intro) ---------- */
  (function () {
    var plane = document.getElementById("plane");
    var hero = document.getElementById("title-sec"), next = document.getElementById("intro-sec");
    if (!plane || !hero || !next || reduceMotion) return;
    var ticking = false;
    function frame() {
      ticking = false;
      var end = next.offsetTop - window.innerHeight * 0.5;
      var p = Math.min(1, Math.max(0, window.scrollY / Math.max(1, end)));
      var dx = p * Math.min(window.innerWidth * 0.72, 640);
      var dy = -p * hero.offsetHeight * 0.55;
      plane.style.transform = "translate(" + dx.toFixed(1) + "px," + dy.toFixed(1) + "px) scale(" + (1 - p * 0.2).toFixed(3) + ")";
      plane.style.opacity = p > 0.985 ? "0" : "1";
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(frame); }
    }, { passive: true });
    frame();
  })();

  /* ---------- AG01 destination map ---------- */
  /* SAMPLE medians from origin (USD) — replace with real route medians.
     The team can also override at runtime: window.JET2_STATE_FARES = {...} */
  var STATE_FARES = {
    AL: 238, AK: 486, AZ: 342, AR: 262, CA: 398, CO: 296, CT: 228, DE: 219, FL: 252,
    GA: 196, HI: 512, ID: 348, IL: 248, IN: 242, IA: 272, KS: 282, KY: 236, LA: 258,
    ME: 264, MD: 224, MA: 238, MI: 246, MN: 278, MS: 252, MO: 268, MT: 372, NE: 292,
    NV: 362, NH: 252, NJ: 226, NM: 318, NY: 242, NC: 228, ND: 322, OH: 238, OK: 282,
    OR: 382, PA: 232, RI: 244, SC: 232, SD: 318, TN: 234, TX: 288, UT: 332, VT: 268,
    VA: 226, WA: 392, WV: 258, WI: 262, WY: 358, DC: 222
  };
  if (window.JET2_STATE_FARES) STATE_FARES = window.JET2_STATE_FARES;
  var picked = {};
  function renderShortlist() {
    var box = document.getElementById("map-shortlist");
    var keys = Object.keys(picked);
    if (!keys.length) { box.innerHTML = "<p class='caption'>No states picked yet — click the map.</p>"; return; }
    keys.sort(function (a, b) { return STATE_FARES[a] - STATE_FARES[b]; });
    box.innerHTML = "<p class='caption'>Your shortlist (click a row to remove):</p><ul>" +
      keys.map(function (k) { return "<li data-k='" + k + "'><span>" + k + "</span><span>$" + STATE_FARES[k] + "</span></li>"; }).join("") + "</ul>";
    box.querySelectorAll("li").forEach(function (li) {
      li.addEventListener("click", function () {
        delete picked[li.dataset.k];
        d3.selectAll(".map-state").classed("picked", function (d) { return !!picked[d.id]; });
        renderShortlist();
      });
    });
  }
  (function map() {
    var W = 720, H = 440;
    var vals = Object.keys(STATE_FARES).map(function (k) { return STATE_FARES[k]; });
    var color = d3.scaleQuantize()
      .domain([d3.min(vals), d3.max(vals)])
      .range(["#fdf6d8", "#f9e79f", "#f5c542", "#e67e22", "#c0392b"]);
    function legend(s, x0) {
      var r = color.range(), ext = vals.slice().sort(function (a, b) { return a - b; });
      var lg = s.append("g").attr("transform", "translate(" + x0 + "," + (H - 24) + ")").attr("font-size", 12);
      lg.append("text").attr("x", -8).attr("y", 12).text("$" + ext[0]);
      r.forEach(function (c, i) { lg.append("rect").attr("x", i * 34).attr("width", 32).attr("height", 14).attr("fill", c).attr("stroke", "#111"); });
      lg.append("text").attr("x", r.length * 34 + 6).attr("y", 12).text("$" + ext[ext.length - 1]);
    }
    function hover(sel) {
      sel.on("mousemove", function (e, d) {
          var nm = d.properties ? d.properties.name : d.id;
          var f = STATE_FARES[d.id];
          showTip("<strong>" + nm + "</strong><br>" + (f ? "Median fare $" + f + " (sample)" : "No data"), e.clientX, e.clientY);
        })
        .on("mouseleave", hideTip)
        .on("click", function (e, d) {
          if (picked[d.id]) delete picked[d.id]; else picked[d.id] = true;
          d3.selectAll(".map-state").classed("picked", function (o) { return !!picked[o.id]; });
          renderShortlist();
        });
    }
    function fallback() {
      var s = svg("#map-vis", W, H);
      var top = Object.keys(STATE_FARES).sort(function (a, b) { return STATE_FARES[a] - STATE_FARES[b]; }).slice(0, 14);
      var x = d3.scaleLinear().domain([0, d3.max(vals)]).range([70, W - 70]);
      top.forEach(function (k, i) {
        var y = 14 + i * 29;
        s.append("text").attr("x", 8).attr("y", y + 15).attr("font-size", 13).attr("font-family", "Acme, sans-serif").text(k);
        s.append("rect").attr("x", 70).attr("y", y).attr("width", x(STATE_FARES[k]) - 70).attr("height", 20)
          .attr("rx", 4).attr("fill", color(STATE_FARES[k])).attr("stroke", "#111");
        s.append("text").attr("x", x(STATE_FARES[k]) + 6).attr("y", y + 15).attr("font-size", 12).text("$" + STATE_FARES[k]);
      });
      s.append("text").attr("x", 8).attr("y", H - 8).attr("font-size", 12).attr("fill", "#51606f")
        .text("Map tiles unavailable offline — 14 cheapest sample states shown.");
    }
    if (typeof topojson === "undefined") { fallback(); renderShortlist(); return; }
    d3.json("https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json").then(function (us) {
      var s = svg("#map-vis", W, H);
      var states = topojson.feature(us, us.objects.states).features;
      // us-atlas uses FIPS ids; map to postal codes
      var FIPS = { "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY" };
      states.forEach(function (f) { f.id = FIPS[f.id] || f.id; });
      var proj = d3.geoAlbersUsa().fitExtent([[8, 8], [W - 8, H - 44]], { type: "FeatureCollection", features: states });
      var path = d3.geoPath(proj);
      s.selectAll("path").data(states).join("path")
        .attr("d", path)
        .attr("class", "map-state")
        .attr("fill", function (d) { return STATE_FARES[d.id] ? color(STATE_FARES[d.id]) : "#e3e8ed"; })
        .call(hover);
      s.append("path")
        .datum(topojson.mesh(us, us.objects.states, function (a, b) { return a !== b; }))
        .attr("d", path).attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 1)
        .attr("pointer-events", "none");
      legend(s, 30);
      renderShortlist();
    }).catch(function () { fallback(); renderShortlist(); });
  })();

  /* ---------- YH02 nonstop vs connecting ---------- */
  (function () {
    var s1 = svg("#nonstop-vis", 560, 220);
    var d1 = [["Nonstop", 318], ["Connecting", 356]];
    var x1 = d3.scaleLinear().domain([0, 400]).range([150, 470]);
    d1.forEach(function (d, i) {
      var y = 30 + i * 72;
      s1.append("text").attr("x", 8).attr("y", y + 24).attr("font-size", 15).attr("font-family", "Acme, sans-serif").text(d[0]);
      s1.append("rect").attr("x", 150).attr("y", y).attr("width", x1(d[1]) - 150).attr("height", 32).attr("rx", 4)
        .attr("fill", i === 0 ? "#0b2540" : "#8aa0b4").attr("stroke", "#111")
        .on("mousemove", function (e) { showTip("<strong>" + d[0] + "</strong><br>Sample median $" + d[1] + " (July 4 window)", e.clientX, e.clientY); })
        .on("mouseleave", hideTip);
      s1.append("text").attr("x", x1(d[1]) + 8).attr("y", y + 23).attr("font-size", 14).attr("font-weight", "bold").text("$" + d[1]);
    });
    s1.append("text").attr("x", 8).attr("y", 205).attr("font-size", 13).attr("fill", "#51606f")
      .text("Sketch YH-02 · July 4 sample medians — backwards from the usual assumption.");
  })();

  /* ---------- CZ01 price diary ---------- */
  function diaryData() {
    var r = rng(11), out = [];
    for (var d = 60; d >= 1; d--) {
      var i = 60 - d, upP = (i === 40) ? 0.25 : (i === 47) ? 0.34 : (i === 55) ? 0.48 : 0.10;
      var v = r();
      out.push({ day: d, idx: i, s: v < upP ? "up" : (v < upP + 0.10 ? "down" : "flat"),
        spike: (i === 40 || i === 47 || i === 55) });
    }
    return out;
  }
  var DIARY = diaryData(), diaryStage = 1, diaryMax = 60;
  var DCOL = { up: "#c0392b", down: "#1e7d4f", flat: "#cfd8e1" };
  var DLAB = { up: "rose 10%+", down: "fell 10%+", flat: "barely moved" };
  function drawDiary() {
    var data = DIARY.filter(function (d) { return d.day <= diaryMax; });
    var W = 720, H = 300, cols = 12, cw = 56, top = 14;
    var s = svg("#diary-vis", W, H);
    data.forEach(function (d, i) {
      var gx, gy;
      if (diaryStage === 1) { gx = (i % cols) * cw; gy = Math.floor(i / cols) * 52; }
      else {
        var row = d.s === "up" ? 0 : d.s === "down" ? 1 : 2;
        var order = data.filter(function (o) { return o.s === d.s; }).indexOf(d);
        gx = (order % cols) * cw; gy = row * 84;
      }
      var dim = (diaryStage >= 3 && !(d.spike && d.s === "up")) ? 0.28 : 1;
      s.append("rect")
        .attr("x", 24 + gx).attr("y", top + gy).attr("width", 46).attr("height", diaryStage === 1 ? 42 : 68)
        .attr("rx", 5).attr("fill", DCOL[d.s]).attr("opacity", dim)
        .attr("stroke", d.spike && d.s === "up" && diaryStage >= 3 ? "#111" : "none")
        .attr("stroke-width", 3)
        .on("mousemove", function (e) { showTip("<strong>" + d.day + " days out</strong><br>Fare " + DLAB[d.s], e.clientX, e.clientY); })
        .on("mouseleave", hideTip);
    });
    var lg = s.append("g").attr("transform", "translate(24,282)").attr("font-size", 12).attr("fill", "#333");
    [["#c0392b", "rose 10%+"], ["#1e7d4f", "fell 10%+"], ["#cfd8e1", "barely moved"]]
      .forEach(function (L, i) {
        lg.append("rect").attr("x", i * 170).attr("y", -12).attr("width", 13).attr("height", 13).attr("fill", L[0]).attr("stroke", "#111");
        lg.append("text").attr("x", i * 170 + 18).attr("y", 0).text(L[1]);
      });
  }
  function setStage(n) {
    diaryStage = n;
    for (var k = 1; k <= 4; k++) document.getElementById("diary-text-" + k).hidden = (k !== n);
    drawDiary();
  }
  document.getElementById("play-button").addEventListener("click", function () {
    setStage(diaryStage >= 4 ? 1 : diaryStage + 1);
  });
  var slider = document.getElementById("diary-slider"), sval = document.getElementById("diary-slider-val");
  slider.addEventListener("input", function () {
    diaryMax = +slider.value; sval.textContent = slider.value; drawDiary();
  });
  drawDiary();

  /* ---------- CZ03 staircase ---------- */
  (function () {
    var data = [
      { d: 60, f: 290 }, { d: 45, f: 285 }, { d: 30, f: 278 }, { d: 21, f: 270 },
      { d: 14, f: 258 }, { d: 13, f: 284 }, { d: 7, f: 320 }, { d: 3, f: 350 }, { d: 1, f: 371 }
    ];
    var W = 560, H = 380, m = { t: 20, r: 16, b: 44, l: 58 };
    var s = svg("#stairs-vis", W, H);
    var x = d3.scaleLinear().domain([60, 0]).range([m.l, W - m.r]);
    var y = d3.scaleLinear().domain([240, 390]).range([H - m.b, m.t]);
    s.append("g").attr("transform", "translate(0," + (H - m.b) + ")").call(d3.axisBottom(x).ticks(7));
    s.append("g").attr("transform", "translate(" + m.l + ",0)").call(d3.axisLeft(y).tickFormat(function (v) { return "$" + v; }));
    s.append("text").attr("x", (W + m.l - m.r) / 2).attr("y", H - 8).attr("text-anchor", "middle").attr("font-size", 13).text("Days before departure");
    var line = d3.line().x(function (d) { return x(d.d); }).y(function (d) { return y(d.f); }).curve(d3.curveStepAfter);
    s.append("path").datum(data).attr("d", line).attr("fill", "none").attr("stroke", "#0b2540").attr("stroke-width", 3.5);
    s.selectAll("circle").data(data).join("circle")
      .attr("cx", function (d) { return x(d.d); }).attr("cy", function (d) { return y(d.f); })
      .attr("r", 6).attr("fill", "#ffd200").attr("stroke", "#111").attr("stroke-width", 2)
      .on("mousemove", function (e, d) { showTip("<strong>" + d.d + " days out</strong><br>Median lowest fare $" + d.f, e.clientX, e.clientY); })
      .on("mouseleave", hideTip);
    [{ d: 14, f: 258, t: "floor $258" }, { d: 13, f: 284, t: "+$26 overnight" }, { d: 1, f: 371, t: "$371 (+44%)" }]
      .forEach(function (a) {
        s.append("text").attr("x", x(a.d)).attr("y", y(a.f) - 13).attr("text-anchor", "middle")
          .attr("font-size", 13).attr("font-weight", "bold").attr("font-family", "Acme, sans-serif").text(a.t);
      });
  })();

  /* ---------- JK3 heatmap ---------- */
  (function () {
    var routes = ["ATL-JFK", "ATL-BOS", "ATL-LAX", "ATL-DFW", "ATL-LGA"];
    var wins = ["60–50", "50–40", "40–30", "30–20", "20–10", "10–0"];
    var vals = [
      [0.5, -1.2, 0.8, 1.5, 3.1, 8.4], [-0.6, 0.9, -2.1, 1.1, 2.6, 7.8],
      [1.2, 0.4, 1.8, 2.2, 4.0, 9.2], [0.2, -0.8, 1.0, 0.6, 2.9, 8.0],
      [-1.0, 0.5, -0.4, 1.8, 2.2, 6.5]
    ];
    var W = 720, H = 280, m = { t: 32, r: 14, b: 26, l: 92 };
    var s = svg("#heatmap-vis", W, H);
    var x = d3.scaleBand().domain(wins).range([m.l, W - m.r]).padding(0.08);
    var y = d3.scaleBand().domain(routes).range([m.t, H - m.b]).padding(0.12);
    var c = d3.scaleLinear().domain([-3, 0, 9]).range(["#1e7d4f", "#ffffff", "#c0392b"]);
    wins.forEach(function (w) {
      s.append("text").attr("x", x(w) + x.bandwidth() / 2).attr("y", 18)
        .attr("text-anchor", "middle").attr("font-size", 12).attr("font-family", "Acme, sans-serif").text(w);
    });
    routes.forEach(function (r, ri) {
      s.append("text").attr("x", m.l - 8).attr("y", y(r) + y.bandwidth() / 2 + 4)
        .attr("text-anchor", "end").attr("font-size", 13).attr("font-weight", "bold").attr("font-family", "Acme, sans-serif").text(r);
      wins.forEach(function (w, ci) {
        var v = vals[ri][ci];
        s.append("rect").attr("x", x(w)).attr("y", y(r))
          .attr("width", x.bandwidth()).attr("height", y.bandwidth()).attr("rx", 4)
          .attr("fill", c(v)).attr("stroke", "#111")
          .on("mousemove", function (e) { showTip("<strong>" + r + " · " + w + " days</strong><br>" + (v > 0 ? "+" : "") + v + "% move", e.clientX, e.clientY); })
          .on("mouseleave", hideTip);
      });
    });
  })();

  /* ---------- route curves ---------- */
  var SERIES = {
    "ATL-JFK": [[60, 352], [50, 348], [40, 365], [32, 365], [24, 300], [16, 243], [8, 255], [2, 290]],
    "ATL-BOS": [[60, 310], [50, 305], [40, 330], [32, 318], [24, 290], [16, 265], [8, 280], [2, 305]],
    "ATL-LAX": [[60, 430], [50, 388], [40, 440], [32, 470], [24, 450], [16, 490], [8, 505], [2, 518]],
    "ATL-LGA": [[60, 210], [50, 187], [40, 220], [32, 205], [24, 230], [16, 240], [8, 235], [2, 254]]
  };
  function drawRoute(key) {
    var data = SERIES[key], W = 720, H = 260, m = { t: 14, r: 14, b: 38, l: 52 };
    var s = svg("#routes-vis", W, H);
    var x = d3.scaleLinear().domain([60, 0]).range([m.l, W - m.r]);
    var y = d3.scaleLinear().domain([150, 550]).range([H - m.b, m.t]);
    s.append("g").attr("transform", "translate(0," + (H - m.b) + ")").call(d3.axisBottom(x).ticks(7));
    s.append("g").attr("transform", "translate(" + m.l + ",0)").call(d3.axisLeft(y).ticks(5).tickFormat(function (v) { return "$" + v; }));
    var line = d3.line().x(function (d) { return x(d[0]); }).y(function (d) { return y(d[1]); }).curve(d3.curveMonotoneX);
    s.append("path").datum(data).attr("d", line).attr("fill", "none").attr("stroke", "#0b2540").attr("stroke-width", 3);
    s.selectAll("circle").data(data).join("circle")
      .attr("cx", function (d) { return x(d[0]); }).attr("cy", function (d) { return y(d[1]); })
      .attr("r", 5).attr("fill", "#ffd200").attr("stroke", "#111").attr("stroke-width", 1.8)
      .on("mousemove", function (e, d) { showTip("<strong>" + key + "</strong><br>" + d[0] + " days out · $" + d[1], e.clientX, e.clientY); })
      .on("mouseleave", hideTip);
    s.append("text").attr("x", m.l + 6).attr("y", m.t + 14).attr("font-size", 14)
      .attr("font-family", "Acme, sans-serif").text(key + " · July 4 median fare");
  }
  d3.selectAll("#route-btns button").on("click", function () {
    d3.selectAll("#route-btns button").classed("on", false);
    d3.select(this).classed("on", true);
    drawRoute(this.dataset.r);
  });
  drawRoute("ATL-JFK");

  /* ---------- SS5 odds ribbon ---------- */
  /* Share of matched fares per outcome. Spike heights follow Chart 2
     (baseline ~10% jumps; 25/34/46% at 20/13/5 days out). */
  var RIBBON = {
    labor:    { jump: [[20, 25], [13, 34], [5, 46]], fell: 9 },
    july4:    { jump: [[20, 22], [13, 30], [5, 36]], fell: 12 },
    memorial: { jump: [[20, 20], [13, 28], [5, 33]], fell: 11 },
    base:     { jump: [[20, 24], [13, 31], [5, 38]], fell: 10 }
  };
  function ribbonData(key) {
    var cfg = RIBBON[key], out = [];
    function spike(d, at, h) {
      var sum = 0;
      cfg.jump.forEach(function (j) {
        var dist = (d - j[0]) / 1.6;
        sum += (j[1] - 10) * Math.exp(-dist * dist);
      });
      return 10 + sum;
    }
    for (var d = 60; d >= 0; d--) {
      var j = Math.min(52, spike(d));
      out.push({ d: d, jump: +j.toFixed(1), fell: cfg.fell, steady: +(100 - j - cfg.fell).toFixed(1) });
    }
    return out;
  }
  function drawRibbon(key) {
    var data = ribbonData(key), W = 720, H = 320, m = { t: 16, r: 16, b: 40, l: 52 };
    var s = svg("#ribbon-vis", W, H);
    var x = d3.scaleLinear().domain([60, 0]).range([m.l, W - m.r]);
    var y = d3.scaleLinear().domain([0, 100]).range([H - m.b, m.t]);
    var keys = ["jump", "fell", "steady"];
    var col = { jump: "#c0392b", fell: "#1e7d4f", steady: "#cfd8e1" };
    var lab = { jump: "jumped 10%+", fell: "fell 10%+", steady: "sat steady" };
    var stacked = d3.stack().keys(keys)(data);
    var area = d3.area()
      .x(function (d) { return x(d.data.d); })
      .y0(function (d) { return y(d[0]); })
      .y1(function (d) { return y(d[1]); })
      .curve(d3.curveMonotoneX);
    s.selectAll("path.band").data(stacked).join("path")
      .attr("class", "band").attr("d", area)
      .attr("fill", function (d) { return col[d.key]; })
      .attr("stroke", "#111").attr("stroke-width", 1)
      .attr("opacity", 0.92)
      .on("mousemove", function (e, d) {
        var xm = d3.pointer(e)[0], day = Math.round(x.invert(xm));
        var row = data.filter(function (r) { return r.d === day; })[0] || data[0];
        showTip("<strong>" + row.d + " days out</strong><br>" +
          "Jumped: " + row.jump + "% · Fell: " + row.fell + "% · Steady: " + row.steady + "%",
          e.clientX, e.clientY);
      })
      .on("mouseleave", hideTip);
    s.append("g").attr("transform", "translate(0," + (H - m.b) + ")").call(d3.axisBottom(x).ticks(7));
    s.append("g").attr("transform", "translate(" + m.l + ",0)").call(d3.axisLeft(y).ticks(5).tickFormat(function (v) { return v + "%"; }));
    s.append("text").attr("x", (W + m.l - m.r) / 2).attr("y", H - 8).attr("text-anchor", "middle").attr("font-size", 13).text("Days before departure");
    var lg = s.append("g").attr("transform", "translate(" + m.l + ",2)").attr("font-size", 12);
    keys.forEach(function (k, i) {
      lg.append("rect").attr("x", i * 150).attr("width", 12).attr("height", 12).attr("fill", col[k]).attr("stroke", "#111");
      lg.append("text").attr("x", i * 150 + 16).attr("y", 11).text(lab[k]);
    });
  }
  d3.selectAll("#ribbon-btns button").on("click", function () {
    d3.selectAll("#ribbon-btns button").classed("on", false);
    d3.select(this).classed("on", true);
    drawRibbon(this.dataset.w);
  });
  drawRibbon("labor");
})();
