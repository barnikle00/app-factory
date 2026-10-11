/* ds.js — enhancement, never mechanism.
 *
 * THE RULE THIS FILE EXISTS TO OBEY: delete it and every page still works. Every
 * form submits, every link navigates, every dialog opens through its own <form
 * method="dialog">. Nothing here creates behaviour; it only removes steps.
 *
 * That is checkable, and verify_design.py checks it — by fetching the page's own
 * HTML and counting the mechanism, not by reading this file and believing it.
 *
 * No build step, no dependency, no framework. The whole layer is four behaviours.
 */

(function () {
  "use strict";

  /* 1. Dialogs. <dialog> already closes itself via method="dialog"; all that is
   *    missing is opening one from a button elsewhere on the page. A plain link
   *    to the same data on its own URL remains the correct fallback, which is
   *    why nothing here is required.                                          */
  document.addEventListener("click", function (e) {
    var opener = e.target.closest("[data-ds-open]");
    if (opener) {
      var dlg = document.getElementById(opener.getAttribute("data-ds-open"));
      if (dlg && typeof dlg.showModal === "function") {
        e.preventDefault();
        dlg.showModal();
      }
      return;
    }
    var closer = e.target.closest("[data-ds-close]");
    if (closer) {
      var own = closer.closest("dialog");
      if (own) { e.preventDefault(); own.close(); }
    }
  });

  /* 2. Native-script digits in number fields. A phone keyboard set to Persian or Arabic produces
   *    ۱۲۳ and the server's int() raises on it. Normalising on the way out means
   *    no screen has to remember, and the server still normalises too — this is
   *    convenience, not validation. Four projects have re-solved this one.    */
  var FA = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩";
  function toAscii(s) {
    return s.replace(/[۰-۹٠-٩]/g, function (ch) {
      return String(FA.indexOf(ch) % 10);
    });
  }
  document.addEventListener("submit", function (e) {
    var fields = e.target.querySelectorAll('input[type="number"], input[inputmode="numeric"], .w-amount, .w-count');
    for (var i = 0; i < fields.length; i++) {
      if (fields[i].value) fields[i].value = toAscii(fields[i].value);
    }
  }, true);

  /* 3. Filter bars submit on change. The toolbar is a real <form method="get">
   *    with a real submit button, so this only saves a click. The button is
   *    hidden ONLY once this file has run — if it never runs, the button is
   *    still there and the filter still works.                                */
  document.querySelectorAll(".toolbar").forEach(function (form) {
    var submit = form.querySelector('[type="submit"]');
    if (!submit) return;
    form.addEventListener("change", function (e) {
      if (e.target.matches("select, input[type=date], input[type=checkbox]")) {
        form.requestSubmit ? form.requestSubmit() : form.submit();
      }
    });
    submit.classList.add("visually-hidden");
  });

  /* 4. Destructive actions confirm. Marked in the template, never inferred from
   *    a label — "Delete" appears in plenty of harmless places.                  */
  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-ds-confirm]");
    if (el && !window.confirm(el.getAttribute("data-ds-confirm"))) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);
})();
