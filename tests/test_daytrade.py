import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from _load import load, ROOT

dt = load("trader-daytrade", "daytrade")
EXAMPLE = os.path.join(ROOT, "trader-daytrade", "daytrade.example.json")


def cfg(**kw):
    c = dt.load_config(EXAMPLE)
    c.update(kw)
    return c


class Formats(unittest.TestCase):
    def test_euro_and_numbers_in_german(self):
        self.assertEqual(dt.eur(1234.5), "1.234,50 €")
        self.assertEqual(dt.eur(-42), "-42,00 €")
        self.assertEqual(dt.parse_num("52,40"), 52.40)
        self.assertEqual(dt.parse_num("52.40"), 52.40)
        self.assertEqual(dt.parse_num("1.234,56"), 1234.56)
        self.assertEqual(dt.parse_num("12,5 €"), 12.5)
        with self.assertRaises(dt.DayError):
            dt.parse_num("abc")


class Size(unittest.TestCase):
    def test_risk_sizing_with_fees(self):
        r = dt.size(cfg(max_position_pct=100), 52.40, 51.80)
        # 1 % von 5.000 = 50 €, minus 2 € Gebühren = 48 €, / 0,60 € = 80 Stück
        self.assertEqual(r["stueck"], 80)
        self.assertEqual(r["begrenzt_durch"], "Risiko pro Trade")
        self.assertAlmostEqual(r["risiko_eur"], 80 * 0.60 + 2)
        self.assertLessEqual(r["risiko_eur"], 50.0)

    def test_position_cap_wins(self):
        r = dt.size(cfg(), 52.40, 51.80, target=54.00)
        self.assertEqual(r["stueck"], 23)          # 25 % von 5.000 = 1.250 € / 52,40
        self.assertEqual(r["begrenzt_durch"], "max. Positionsgröße")
        self.assertAlmostEqual(r["crv"], 1.60 / 0.60)
        self.assertAlmostEqual(r["ziel_2r"], 53.60)

    def test_cash_limits_too(self):
        r = dt.size(cfg(max_position_pct=100), 10.0, 9.0, cash=101)
        self.assertEqual(r["stueck"], 10)
        self.assertEqual(r["begrenzt_durch"], "verfügbares Geld")

    def test_no_trade_when_budget_too_small(self):
        r = dt.size(cfg(konto=300), 100.0, 90.0)   # 3 € Budget, 2 € Gebühren, 10 € Abstand
        self.assertEqual(r["stueck"], 0)
        self.assertEqual(r["risiko_eur"], 0)

    def test_long_only_and_sane_inputs(self):
        for entry, stop in ((50, 50), (50, 51), (0, -1)):
            with self.assertRaises(dt.DayError):
                dt.size(cfg(), entry, stop)
        with self.assertRaises(dt.DayError):
            dt.size(cfg(), 50, 49, target=49.5)


def row(datum, ergebnis, setup="Breakout", ticker="SAP"):
    return {"datum": datum, "ticker": ticker, "stueck": 10, "einstieg": 10, "ausstieg": 10,
            "setup": setup, "notiz": "", "gebuehren": 2.0, "ergebnis": ergebnis}


class DayStop(unittest.TestCase):
    def test_ok_day(self):
        st = dt.day_status(cfg(), [row("2026-11-24", 30), row("2026-11-24", -20)], "2026-11-24")
        self.assertFalse(st["stopp"])
        self.assertEqual(st["trades"], 2)
        self.assertAlmostEqual(st["rest_bis_limit"], 160)

    def test_daily_loss_limit(self):
        st = dt.day_status(cfg(), [row("2026-11-24", -100), row("2026-11-24", 10), row("2026-11-24", -60)], "2026-11-24")
        self.assertTrue(st["stopp"])
        self.assertIn("Tagesverlust", st["gruende"][0])

    def test_fixed_euro_limit_wins(self):
        st = dt.day_status(cfg(tagesverlust_eur=50), [row("2026-11-24", -50)], "2026-11-24")
        self.assertTrue(st["stopp"])

    def test_losing_streak_and_max_trades(self):
        rows = [row("2026-11-24", 5), row("2026-11-24", -1), row("2026-11-24", -1), row("2026-11-24", -1)]
        st = dt.day_status(cfg(), rows, "2026-11-24")
        self.assertTrue(st["stopp"])
        self.assertEqual(st["verluste_folge"], 3)
        rows = [row("2026-11-24", 1)] * 5
        self.assertTrue(dt.day_status(cfg(), rows, "2026-11-24")["stopp"])

    def test_yesterday_does_not_count(self):
        rows = [row("2026-11-23", -500)]
        self.assertFalse(dt.day_status(cfg(), rows, "2026-11-24")["stopp"])


class Stats(unittest.TestCase):
    def test_numbers(self):
        rows = [row("2026-11-20", 60), row("2026-11-20", -20, "Gap"), row("2026-11-21", 30), row("2026-11-21", -30, "Gap")]
        s = dt.stats(rows)
        self.assertEqual(s["trades"], 4)
        self.assertEqual(s["trefferquote"], 50.0)
        self.assertAlmostEqual(s["erwartung"], 10.0)
        self.assertAlmostEqual(s["gewinnfaktor"], 90 / 50)
        self.assertAlmostEqual(s["gebuehren"], 8.0)
        self.assertEqual(s["tage"], 2)
        self.assertEqual(s["setups"]["Gap"]["summe"], -50)
        self.assertEqual(s["setups"]["Breakout"]["gewinner"], 2)

    def test_empty(self):
        self.assertEqual(dt.stats([])["trades"], 0)


class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cfgp = os.path.join(self.dir, "daytrade.json")
        shutil.copy(EXAMPLE, self.cfgp)
        self.jp = os.path.join(self.dir, "journal.csv")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = dt.main(["--config", self.cfgp, "--journal", self.jp] + list(args))
        return code, out.getvalue(), err.getvalue()

    def test_full_day_ends_in_stop(self):
        d = "--datum"
        code, out, _ = self.run_cli("size", "--entry", "52,40", "--stop", "51,80", "--ziel", "54", d, "2026-11-24")
        self.assertEqual(code, 0)
        self.assertIn("23 Stück", out)
        self.assertIn("2,7 : 1", out)
        self.assertIn("keine Anlageberatung", out)
        for t, n, e, x in (("SAP", 20, 182.10, 180.10), ("BAS", 50, 45, 44.4)):
            code, out, _ = self.run_cli("add", "--ticker", t, "--shares", str(n), "--entry", str(e),
                                        "--exit", str(x), "--setup", "Breakout", d, "2026-11-24")
            self.assertEqual(code, 0)
        code, out, _ = self.run_cli("add", "--ticker", "ifx", "--shares", "40", "--entry", "35",
                                    "--exit", "34,6", d, "2026-11-24")
        self.assertEqual(code, 2)
        self.assertIn("STOPP", out)
        self.assertIn("Ergebnis -92,00 €", out)
        code, out, _ = self.run_cli("check", d, "2026-11-24")
        self.assertEqual(code, 2)
        code, out, _ = self.run_cli("size", "--entry", "10", "--stop", "9", d, "2026-11-24")
        self.assertEqual(code, 2)
        self.assertNotIn("Kauf:", out)
        code, out, _ = self.run_cli("check", d, "2026-11-25")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("stats")
        self.assertEqual(code, 0)
        self.assertIn("3 Trades an 1 Tag", out)
        self.assertIn("IFX", out)
        rows = dt.read_journal(self.jp)
        self.assertEqual([r["ergebnis"] for r in rows], [-42.0, -32.0, -18.0])

    def test_errors_are_german_and_exit_3(self):
        code, _, err = self.run_cli("size", "--entry", "50", "--stop", "51")
        self.assertEqual(code, 3)
        self.assertIn("Stopp muss unter dem Einstieg", err)

    def test_empty_journal(self):
        code, out, _ = self.run_cli("stats")
        self.assertEqual(code, 1)
        self.assertIn("Noch keine Trades", out)


if __name__ == "__main__":
    unittest.main()
