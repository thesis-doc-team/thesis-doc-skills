/* Diagram render probe for project-technical-doc (single-shot, no event waiting).
 * Measures each embedded SVG the way a reader sees it:
 *   - height_ratio: rendered height vs viewBox natural height (<1 = CSS squash)
 *   - container_scroll: diagram container shows an inner scrollbar (must be false:
 *     diagrams must display fully, no scrolling bars)
 *   - black_shape_fills: node/edge shapes with computed fill = pure black
 *     (the signature of broken style selectors after id prefixing)
 *   - text_fills / shape_fills: label text color vs node fill for contrast checks
 * Writes its JSON result exactly once into <pre id="screenshot-audit-probe">.
 */
(function () {
  function measure() {
    var out = [];
    var nodes = document.querySelectorAll('.vector-diagram svg');
    for (var i = 0; i < nodes.length; i++) {
      var svg = nodes[i];
      var r = svg.getBoundingClientRect();
      var vb = svg.viewBox && svg.viewBox.baseVal;
      var vw = vb && vb.width, vh = vb && vb.height;
      var natural = (vw && vh && r.width) ? vh * (r.width / vw) : null;
      var box = svg.parentNode;
      var scroll = !!box && ((box.scrollHeight > box.clientHeight + 1) ||
                             (box.scrollWidth > box.clientWidth + 1));
      var shapes = svg.querySelectorAll('rect,polygon,path,circle,ellipse');
      var black = 0, total = 0, fills = {};
      for (var j = 0; j < shapes.length; j++) {
        var el = shapes[j];
        /* arrowhead marker bodies and filter defs are intentionally dark — not node fills */
        if (el.closest && el.closest('defs,marker')) continue;
        var f = getComputedStyle(el).fill;
        if (!f || f === 'none') continue;
        total++;
        fills[f] = (fills[f] || 0) + 1;
        if (f === 'rgb(0, 0, 0)') black++;
      }
      var texts = svg.querySelectorAll('text');
      var tfills = {};
      for (var k = 0; k < texts.length; k++) {
        var tf = getComputedStyle(texts[k]).fill || '';
        tfills[tf] = (tfills[tf] || 0) + 1;
      }
      out.push({
        index: i + 1,
        svg_width_px: Math.round(r.width * 10) / 10,
        svg_height_px: Math.round(r.height * 10) / 10,
        natural_height_px: natural ? Math.round(natural * 10) / 10 : null,
        height_ratio: natural ? Math.round((r.height / natural) * 1000) / 1000 : null,
        container_scroll: scroll,
        shape_fill_total: total,
        black_shape_fills: black,
        black_fill_ratio: total ? Math.round((black / total) * 1000) / 1000 : 0,
        shape_fills: fills,
        text_fills: tfills,
        text_count: texts.length
      });
    }
    return { ok: true, result: { diagrams: out } };
  }
  var pre = document.createElement('pre');
  pre.id = 'screenshot-audit-probe';
  pre.style.display = 'none';
  pre.textContent = JSON.stringify(measure());
  document.body.appendChild(pre);
})();
