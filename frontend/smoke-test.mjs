#!/usr/bin/env node
/**
 * HIWALOY frontend smoke tests.
 *
 * Runs against a live dev or production server.
 * Usage:
 *   node smoke-test.mjs                    # → http://localhost:3000
 *   node smoke-test.mjs http://localhost:3000
 *
 * Exit 0 = all checks passed.
 * Exit 1 = at least one check failed.
 */

const BASE = process.argv[2] ?? "http://localhost:3000";

let passed = 0;
let failed = 0;

function ok(label) {
  console.log(`  ✓  ${label}`);
  passed++;
}

function fail(label, reason) {
  console.error(`  ✗  ${label}: ${reason}`);
  failed++;
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  const text = await res.text();
  return { status: res.status, text };
}

// ── Checks ──────────────────────────────────────────────────────────────────

async function checkRoute(path, label, expectedStrings = []) {
  try {
    const { status, text } = await get(path);
    if (status !== 200) {
      fail(label, `HTTP ${status}`);
      return;
    }
    for (const s of expectedStrings) {
      if (!text.includes(s)) {
        fail(`${label} — content check`, `"${s}" not found in response`);
        return;
      }
    }
    ok(label);
  } catch (err) {
    fail(label, err.message);
  }
}

async function checkNoSecret(path, secrets, label) {
  try {
    const { text } = await get(path);
    const lower = text.toLowerCase();
    for (const s of secrets) {
      if (lower.includes(s.toLowerCase())) {
        fail(label, `secret "${s}" found in page source`);
        return;
      }
    }
    ok(label);
  } catch (err) {
    fail(label, err.message);
  }
}

// ── Run all checks ───────────────────────────────────────────────────────────

console.log(`\nHIWALOY frontend smoke tests → ${BASE}\n`);

await checkRoute("/", "Landing page loads (200)", [
  "HIWALOY",
  "Kıyafetin sizde",          // Turkish hero headline
  "Ücretsiz Başla",            // primary CTA
]);

await checkRoute("/onboarding", "Onboarding page loads (200)", [
  "Profil Oluştur",            // page title
  "Boy (cm)",                   // height field label
  "Kilo (kg)",                  // weight field label
  "Tercih Ettiğiniz Kesim",    // fit preference label
]);

await checkRoute("/analyze", "Analyze page loads (200)", [
  "Kıyafet",                   // garment-related Turkish text
]);

await checkRoute("/history", "History page loads (200)", [
  "Geçmiş",                    // history page Turkish text
]);

await checkNoSecret("/", ["password", "api_key", "gemini_api_key", "postgres"], "Landing — no secrets in HTML");
await checkNoSecret("/onboarding", ["password", "api_key", "secret"], "Onboarding — no secrets in HTML");

// Nav links present on all pages
for (const [path, navText] of [
  ["/", "Analiz"],
  ["/onboarding", "Analiz"],
  ["/analyze", "Analiz"],
]) {
  await checkRoute(path, `Nav "Analiz" link present on ${path}`, [navText]);
}

// Turkish locale content
await checkRoute("/", "Turkish language content on landing", [
  "Vücut Analizi",
  "Kıyafet Analizi",
  "Topluluk Yorumları",
]);

// ── Summary ──────────────────────────────────────────────────────────────────

console.log(`\n${"─".repeat(48)}`);
console.log(`Passed: ${passed}   Failed: ${failed}`);

if (failed > 0) {
  console.error(`\n${failed} check(s) failed.\n`);
  process.exit(1);
} else {
  console.log(`\nAll checks passed.\n`);
  process.exit(0);
}
