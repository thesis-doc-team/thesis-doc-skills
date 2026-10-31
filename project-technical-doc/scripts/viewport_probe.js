/* viewport_probe.js — single-shot layout measurement probe.
 *
 * Injected into a copy of the page under test (see screenshot_audit.py).
 * Hard rules learned from real debugging sessions:
 *   1. Run immediately — do NOT wait for load/readystatechange (unreliable
 *      under Chrome's --virtual-time-budget virtual clock).
 *   2. Measure once and write once — never clear/rewrite the DOM on a timer
 *      (a re-measure pass saw its own garbage and reported MISSING).
 *   3. No shell-escaped heredocs — this file is written/inlined by Python
 *      file I/O, so backslashes and newlines are never re-interpreted.
 */
(function () {
  function measure() {
    var doc = document.documentElement, body = document.body;
    if (!doc || !body) return null;
    var clientW = doc.clientWidth || window.innerWidth;
    var scrollW = Math.max(body.scrollWidth || 0, doc.scrollWidth || 0);
    var offenders = [];
    var all = body.querySelectorAll('*');
    for (var i = 0; i < all.length && offenders.length < 8; i++) {
      var r = all[i].getBoundingClientRect();
      if (r.right > clientW + 1 && r.width > 0 && r.height > 0) {
        var cls = (all[i].className && all[i].className.toString) ? all[i].className.toString().slice(0, 60) : '';
        offenders.push({ tag: all[i].tagName.toLowerCase(), cls: cls, right: Math.round(r.right) });
      }
    }
    return {
      innerWidth: window.innerWidth,
      clientWidth: clientW,
      bodyScrollWidth: body.scrollWidth || 0,
      docScrollWidth: doc.scrollWidth || 0,
      realHorizontalOverflow: scrollW > clientW + 1,
      docHeight: Math.max(body.scrollHeight || 0, doc.scrollHeight || 0),
      overflowOffenders: offenders
    };
  }
  function emit(data) {
    var pre = document.getElementById('screenshot-audit-probe');
    if (!pre) {
      pre = document.createElement('pre');
      pre.id = 'screenshot-audit-probe';
      pre.style.display = 'none';
      (document.body || document.documentElement).appendChild(pre);
    }
    pre.textContent = JSON.stringify(data); /* textContent: no HTML escaping issues */
  }
  try {
    emit({ ok: true, probe: 'screenshot-audit', result: measure() });
  } catch (e) {
    emit({ ok: false, probe: 'screenshot-audit', error: String(e) });
  }
})();
