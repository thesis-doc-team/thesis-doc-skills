/* Thesis Doc Suite Taru — 离线交互脚本（无外部依赖） */
(function () {
  'use strict';

  /* ---------- 移动端导航 ---------- */
  var navToggle = document.getElementById('navToggle');
  var navLinks = document.getElementById('navLinks');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function () {
      var open = navLinks.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    navLinks.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        navLinks.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ---------- 命令复制（含 file:// 回退） ---------- */
  function flash(btn, text) {
    var old = btn.textContent;
    btn.textContent = text;
    btn.classList.add('copied');
    setTimeout(function () {
      btn.textContent = old;
      btn.classList.remove('copied');
    }, 1600);
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try {
        var ok = document.execCommand('copy');
        document.body.removeChild(ta);
        ok ? resolve() : reject(new Error('copy failed'));
      } catch (err) {
        document.body.removeChild(ta);
        reject(err);
      }
    });
  }

  document.querySelectorAll('.copy-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var cmdBox = btn.closest('.cmd');
      var textEl = cmdBox && cmdBox.querySelector('.cmd-text');
      if (!textEl) return;
      copyText(textEl.textContent.trim()).then(function () {
        flash(btn, '已复制');
      }).catch(function () {
        flash(btn, '复制失败');
      });
    });
  });

  /* ---------- 滚动高亮当前导航 ---------- */
  var sectionIds = ['home', 'skills', 'relations', 'assets', 'workflow', 'prereq', 'commands', 'faq'];
  var linkBySection = {};
  document.querySelectorAll('.nav-links a').forEach(function (a) {
    var id = (a.getAttribute('href') || '').replace('#', '');
    if (id) linkBySection[id] = a;
  });

  function setActive() {
    var pos = window.scrollY + 120;
    var current = sectionIds[0];
    sectionIds.forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.offsetTop <= pos) current = id;
    });
    Object.keys(linkBySection).forEach(function (id) {
      linkBySection[id].classList.toggle('active', id === current);
    });
  }
  window.addEventListener('scroll', setActive, { passive: true });
  setActive();
})();
