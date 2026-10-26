"use strict";

const { splitBill } = require("./logic.js");

function cents(n) {
  return Math.round(n * 100);
}

function sumCents(arr) {
  return arr.reduce((a, b) => a + cents(b), 0);
}

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL:", msg);
    process.exit(1);
  }
}

// Classic rounding: 118 / 3 -> 39.34, 39.33, 39.33
{
  const r = splitBill(100, 18, 3);
  assert(cents(r.tip) === 1800, "tip on 100 @ 18%");
  assert(cents(r.total) === 11800, "total with tip");
  assert(r.shares.length === 3, "three shares");
  assert(sumCents(r.shares) === 11800, "shares sum to total");
  assert(cents(r.shares[0]) === 3934 && cents(r.shares[1]) === 3933 && cents(r.shares[2]) === 3933,
    "extra cent goes to first person");
}

// Zero tip
{
  const r = splitBill(10, 0, 3);
  assert(cents(r.tip) === 0, "zero tip");
  assert(sumCents(r.shares) === 1000, "no cent lost with zero tip");
}

// One person gets everything
{
  const r = splitBill(42.5, 20, 1);
  assert(r.shares.length === 1, "one share");
  assert(cents(r.shares[0]) === cents(r.total), "solo payer pays total");
}

// Zero bill
{
  const z = splitBill(0, 15, 2);
  assert(cents(z.total) === 0, "zero bill total");
  assert(z.shares.every((s) => cents(s) === 0), "zero shares");
}

// Bad input throws RangeError
for (const bad of [
  [-1, 10, 2],
  [10, -5, 2],
  [10, 10, 0],
  [10, 10, 1.5],
  [NaN, 10, 2],
  [10, NaN, 2],
  [10, 10, NaN],
]) {
  let threw = false;
  try {
    splitBill(...bad);
  } catch (e) {
    threw = e instanceof RangeError;
  }
  assert(threw, "RangeError for " + JSON.stringify(bad));
}

console.log("All logic tests passed.");
