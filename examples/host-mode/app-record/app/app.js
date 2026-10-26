"use strict";

(function () {
  const form = document.getElementById("bill-form");
  const totalInput = document.getElementById("bill-total");
  const tipInput = document.getElementById("tip-percent");
  const peopleInput = document.getElementById("people-count");
  const errorEl = document.getElementById("form-error");
  const resultsEl = document.getElementById("results");
  const tipOut = document.getElementById("out-tip");
  const totalOut = document.getElementById("out-total");
  const sharesList = document.getElementById("shares-list");

  function formatMoney(amount) {
    return "$" + amount.toFixed(2);
  }

  function isBlank(input) {
    return input.value.trim() === "";
  }

  function readNumber(input, label) {
    const raw = input.value.trim();
    if (raw === "") {
      return { ok: false, empty: true, message: "Enter " + label + "." };
    }
    const n = Number(raw);
    if (!Number.isFinite(n)) {
      return { ok: false, message: label + " must be a plain number." };
    }
    return { ok: true, value: n };
  }

  function update() {
    errorEl.hidden = true;
    resultsEl.hidden = true;
    sharesList.replaceChildren();

    if (isBlank(totalInput)) {
      return;
    }

    const total = readNumber(totalInput, "the bill total");
    if (!total.ok) {
      errorEl.textContent = total.message;
      errorEl.hidden = false;
      return;
    }
    const tip = readNumber(tipInput, "the tip percent");
    if (!tip.ok) {
      errorEl.textContent = tip.message;
      errorEl.hidden = false;
      return;
    }
    const people = readNumber(peopleInput, "how many people");
    if (!people.ok) {
      errorEl.textContent = people.message;
      errorEl.hidden = false;
      return;
    }
    if (!Number.isInteger(people.value)) {
      errorEl.textContent = "People must be a whole number (no decimals).";
      errorEl.hidden = false;
      return;
    }

    let result;
    try {
      result = splitBill(total.value, tip.value, people.value);
    } catch (e) {
      errorEl.textContent = e instanceof RangeError ? e.message : "Could not split this bill.";
      errorEl.hidden = false;
      return;
    }

    tipOut.textContent = formatMoney(result.tip);
    totalOut.textContent = formatMoney(result.total);

    result.shares.forEach(function (share, index) {
      const li = document.createElement("li");
      li.className = "share-row";
      const label = document.createElement("span");
      label.className = "share-label";
      label.textContent = "Person " + (index + 1);
      const amount = document.createElement("span");
      amount.className = "share-amount";
      amount.textContent = formatMoney(share);
      li.append(label, amount);
      sharesList.append(li);
    });

    resultsEl.hidden = false;
  }

  form.addEventListener("input", update);
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    update();
  });

  update();
})();
