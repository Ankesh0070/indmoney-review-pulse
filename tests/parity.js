// Asserts the browser core (dashboard/pulse-core.js) reproduces the Python pipeline.
// Run AFTER `python src/build_note.py`:   node tests/parity.js
const fs = require("fs"), path = require("path"), assert = require("assert");
const root = path.join(__dirname, "..");
const core = require(path.join(root, "dashboard", "pulse-core.js"));
const cfg = core.prepare(JSON.parse(fs.readFileSync(path.join(root, "data", "themes.json"), "utf8")));
const py = JSON.parse(fs.readFileSync(path.join(root, "output", "pulse_data.json"), "utf8"));
const raw = core.parseCSV(fs.readFileSync(path.join(root, "data", "reviews_sample.csv"), "utf8"));
const [rows, rep] = core.normalise(raw, cfg, { defaultSource: "App Store" });
let failures = 0;
const check = (name, fn) => { try { fn(); console.log("  ok  ", name); } catch (e) { failures++; console.log("  FAIL", name, "\n      ", e.message.split("\n").slice(0, 6).join("\n       ")); } };

const js = core.analyze(rows, cfg, {});
const strip = o => JSON.parse(JSON.stringify(o, (k, v) => (k.startsWith("_") ? undefined : v)));
const J = strip(js);

console.log("Parity: JS core vs Python output (" + rows.length + " reviews)");
check("all reviews imported, none dropped", () => assert.strictEqual(rep.dropped, 0));
check("week + year + weeks list", () => assert.deepStrictEqual([J.pulse_week, J.prev_week, J.year, J.weeks], [py.pulse_week, py.prev_week, py.year, py.weeks]));
check("KPIs", () => assert.deepStrictEqual(J.kpi, py.kpi));
check("headline", () => assert.strictEqual(J.headline, py.headline));
check("top themes + priorities", () => assert.deepStrictEqual(J.top_themes, py.top_themes));
check("full priority ranking", () => assert.deepStrictEqual(J.all_priorities, py.all_priorities));
check("12-week trends", () => assert.deepStrictEqual(J.trend, py.trend));
check("pulse series (avg/neg/vol)", () => assert.deepStrictEqual([J.pulse_avg, J.pulse_neg, J.pulse_vol], [py.pulse_avg, py.pulse_neg, py.pulse_vol]));
check("rating distribution", () => assert.deepStrictEqual(J.rating_dist, py.rating_dist));
check("quotes + actions", () => assert.deepStrictEqual([J.quotes, J.actions], [py.quotes, py.actions]));
check("signals", () => assert.deepStrictEqual(J.signals, py.signals));
check("trending phrases", () => assert.deepStrictEqual(J.trending, py.trending));
check("weekly note is byte-identical", () => assert.strictEqual(core.fitNote(js), fs.readFileSync(path.join(root, "output", "weekly_note.md"), "utf8")));
check("note <= 250 words", () => assert.ok(core.words(core.fitNote(js)) <= 250));
check("email draft identical", () => { const e = core.buildEmail(js); assert.strictEqual("Subject: " + e.subject + "\n\n" + e.body, fs.readFileSync(path.join(root, "output", "email_draft.txt"), "utf8")); });

console.log("Behaviour checks");
check("classifier reproduces every sample label", () => {
  const bad = raw.filter(r => core.classify(r.title + " " + r.text, cfg) !== r.theme);
  assert.strictEqual(bad.length, 0, bad.length + " mislabelled");
});
check("PII redaction", () => {
  const [t, n] = core.redact("mail me a.b@x.com or call 9876543210, PAN ABCDE1234F, folio 123456789, @someuser https://x.io/y");
  assert.ok(!/[@]x\.com|9876543210|ABCDE1234F|123456789|someuser|x\.io/.test(t), t); assert.ok(n >= 6);
});
check("CSV round-trip with quotes/newlines", () => {
  const r = [{ review_id: "a", date: "2026-01-05", week: "Jan 05-11", source: "App Store", rating: 3, title: 'He said "hi"', text: "line1\nline2, ok", theme: "" }];
  assert.deepStrictEqual(core.parseCSV(core.toCSV(r))[0].text, "line1\nline2, ok");
});
check("analysis works for every week and source", () => {
  js.weeks.forEach(w => ["All", ...js.sources].forEach(s => { const a = core.analyze(rows, cfg, { week: w, source: s }); assert.ok(a && a.kpi); }));
});
check("weights are normalised (priority stays 0-100)", () => {
  const a = core.analyze(rows, cfg, { weights: [5, 5, 5] }); a.all_priorities.forEach(t => assert.ok(t.priority >= 0 && t.priority <= 100));
});
check("Play-Store style export maps and redacts", () => {
  const csv = 'Review Text,Star Rating,Review Last Update Date and Time,Review Title\n"Withdrawal stuck, call 9123456780",1,2026-06-16T10:00:00Z,Bad\n';
  const [o] = core.normalise(core.parseCSV(csv), cfg, { defaultSource: "Play Store" });
  assert.strictEqual(o[0].theme, "Withdrawals & Fund Holds"); assert.ok(o[0].text.includes("[phone]")); assert.strictEqual(o[0].week, "Jun 15-21");
});

console.log(failures ? `\n${failures} check(s) FAILED` : "\nAll parity checks passed");
process.exit(failures ? 1 : 0);
