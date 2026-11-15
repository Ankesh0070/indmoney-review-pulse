"""Unit tests for the Python core.  Run:  python -m unittest discover -s tests -v"""
import datetime, re, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pulse

CFG = pulse.load_config()
ROOT = pulse.ROOT


def synth(counts_by_week, theme="Charges & Fees", rating=1, start=datetime.date(2026, 1, 5)):
    rows = []
    for w, n in enumerate(counts_by_week):
        for i in range(n):
            d = start + datetime.timedelta(days=7 * w + i % 7)
            rows.append({"review_id": f"S{w}-{i}", "date": d.isoformat(), "week": "", "source": "App Store",
                         "rating": rating, "title": "t", "text": "hidden fee charged again", "theme": theme})
    return rows


class Rounding(unittest.TestCase):
    def test_half_up(self):
        self.assertEqual([pulse.rhu(x) for x in (0.5, 1.5, 2.5, 2.4)], [1, 2, 3, 2])
        self.assertEqual(pulse.r2(2.125), 2.13)


class Redaction(unittest.TestCase):
    def test_pii_removed(self):
        t, n = pulse.redact("mail a.b@x.com call +91 9876543210 PAN ABCDE1234F folio 123456 @handle1 http://x.io")
        for bad in ("a.b@x.com", "9876543210", "ABCDE1234F", "123456", "handle1", "x.io"):
            self.assertNotIn(bad, t)
        self.assertGreaterEqual(n, 6)

    def test_plain_text_untouched(self):
        s = "Withdrawal took 10 days and 3 reminders."
        self.assertEqual(pulse.redact(s), (s, 0))


class Classifier(unittest.TestCase):
    def test_sample_labels_reproduced(self):
        raw = pulse.read_csv(ROOT / "data" / "reviews_sample.csv")
        wrong = [r["title"] for r in raw if pulse.classify(r["title"] + " " + r["text"], CFG) != r["theme"]]
        self.assertEqual(wrong, [])

    def test_unknown_is_none(self):
        self.assertIsNone(pulse.classify("lovely weather today", CFG))

    def test_exact_word_keywords(self):
        self.assertEqual(pulse.classify("my panel looks nice", CFG), None)       # 'pan$' must not match 'panel'
        self.assertEqual(pulse.classify("PAN upload keeps failing", CFG), "Onboarding & KYC")


class Weeks(unittest.TestCase):
    def test_labels_are_monday_start(self):
        s = pulse.week_start(datetime.date(2026, 6, 21))                          # a Sunday
        self.assertEqual(pulse.week_label(s), "Jun 15-21")
        self.assertEqual(pulse.week_label(pulse.week_start(datetime.date(2026, 3, 31))), "Mar 30-05")

    def test_date_formats(self):
        for s in ("2026-06-16", "2026-06-16T10:00:00Z", "16/06/2026", "Jun 16, 2026"):
            self.assertEqual(pulse.parse_date(s), datetime.date(2026, 6, 16), s)


class Normalise(unittest.TestCase):
    def test_play_console_layout_and_report(self):
        raw = [{"Review Text": "Withdrawal stuck, call 9123456780", "Star Rating": "1", "Review Last Update Date and Time": "2026-06-16T10:00:00Z"},
               {"Review Text": "bad", "Star Rating": "x", "Review Last Update Date and Time": "2026-06-16"},
               {"Review Text": "no date", "Star Rating": "3", "Review Last Update Date and Time": ""}]
        rows, rep = pulse.normalise(raw, CFG, default_source="Play Store")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["theme"], "Withdrawals & Fund Holds")
        self.assertIn("[phone]", rows[0]["text"])
        self.assertEqual((rep["dropped_no_rating"], rep["dropped_no_date"], rep["redactions"]), (1, 1, 1))


class Analysis(unittest.TestCase):
    def test_spike_is_flagged_and_ranks_first(self):
        rows = synth([2, 2, 3, 2, 2, 3, 2, 2, 9])                                # last week spikes
        rows += synth([4] * 9, theme="Customer Support", rating=5)
        p = pulse.analyze(rows, CFG)
        self.assertEqual(p["top_themes"][0]["theme"], "Charges & Fees")
        self.assertTrue(any(s["type"] == "spike" and s["theme"] == "Charges & Fees" for s in p["signals"]))

    def test_quiet_data_has_no_spike(self):
        p = pulse.analyze(synth([3] * 10), CFG)
        self.assertFalse(any(s["type"] == "spike" for s in p["signals"]))

    def test_single_week_does_not_crash(self):
        p = pulse.analyze(synth([5]), CFG)
        self.assertIsNone(p["prev_week"]); self.assertEqual(p["kpi"]["delta"], 0)

    def test_gap_weeks_are_kept(self):
        p = pulse.analyze(synth([3, 0, 0, 3]), CFG)
        self.assertEqual(len(p["weeks"]), 4); self.assertIsNone(p["pulse_avg"][1])

    def test_window_capped_at_12_weeks(self):
        self.assertEqual(len(pulse.analyze(synth([2] * 20), CFG)["weeks"]), 12)

    def test_weights_change_ranking_but_stay_bounded(self):
        rows = pulse.load_rows(ROOT / "data" / "reviews_sample.csv", CFG)
        a = pulse.analyze(rows, CFG, weights=(1, 0, 0)); b = pulse.analyze(rows, CFG, weights=(0, 0, 1))
        self.assertNotEqual([t["theme"] for t in a["all_priorities"]], [t["theme"] for t in b["all_priorities"]])
        for t in a["all_priorities"] + b["all_priorities"]:
            self.assertTrue(0 <= t["priority"] <= 100)

    def test_source_filter(self):
        rows = pulse.load_rows(ROOT / "data" / "reviews_sample.csv", CFG)
        p = pulse.analyze(rows, CFG, source="Play Store")
        self.assertEqual(p["kpi"]["n"], p["kpi"]["src"].get("Play Store", 0))


class Outputs(unittest.TestCase):
    def setUp(self):
        self.p = pulse.analyze(pulse.load_rows(ROOT / "data" / "reviews_sample.csv", CFG), CFG)

    def test_note_fits_budget(self):
        self.assertLessEqual(pulse.count_words(pulse.fit_note(self.p)), 250)

    def test_max_five_themes_and_top_three(self):
        self.assertLessEqual(len(self.p["all_priorities"]), 5); self.assertEqual(len(self.p["top_themes"]), 3)

    def test_no_pii_in_outputs(self):
        blob = pulse.fit_note(self.p) + pulse.build_email(self.p)
        self.assertIsNone(re.search(r"[\w.+-]+@[\w-]+\.\w+|\b\d{10}\b|[A-Z]{5}\d{4}[A-Z]", blob.replace("me+indmoney-pulse@myteam.example", "")))


if __name__ == "__main__":
    unittest.main()
