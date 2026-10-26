"use strict";

function toCents(dollars) {
  return Math.round(dollars * 100);
}

function fromCents(cents) {
  return cents / 100;
}

function splitBill(total, tipPercent, people) {
  if (!Number.isFinite(total) || total < 0) {
    throw new RangeError("Bill total must be a number zero or greater.");
  }
  if (!Number.isFinite(tipPercent) || tipPercent < 0) {
    throw new RangeError("Tip percent must be a number zero or greater.");
  }
  if (!Number.isFinite(people) || people < 1 || !Number.isInteger(people)) {
    throw new RangeError("Number of people must be a whole number of at least 1.");
  }

  const billCents = toCents(total);
  const tipCents = Math.round(billCents * tipPercent / 100);
  const totalCents = billCents + tipCents;

  const base = Math.floor(totalCents / people);
  const extra = totalCents % people;
  const shares = [];
  for (let i = 0; i < people; i += 1) {
    shares.push(fromCents(base + (i < extra ? 1 : 0)));
  }

  return {
    tip: fromCents(tipCents),
    total: fromCents(totalCents),
    shares,
  };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { splitBill };
}
if (typeof window !== "undefined") {
  window.splitBill = splitBill;
}
