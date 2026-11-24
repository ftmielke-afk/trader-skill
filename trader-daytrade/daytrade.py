#!/usr/bin/env python3
"""Risiko-Rechner und Trade-Journal für Daytrading mit Aktien (trader-daytrade).

Nur Standardbibliothek, kein Netzwerk. Platziert nie eine Order: Bei Trade
Republic handelst du selbst in der App.

    size    Positionsgröße nach Stopp-Abstand und Risiko pro Trade
    check   Tagesstatus: Ergebnis heute, Trades heute, Tages-Stopp erreicht?
    add     einen abgeschlossenen Trade ins Journal schreiben
    stats   Auswertung des Journals (Trefferquote, Gewinnfaktor, Setups)

Beispiele:
    python3 daytrade.py size --entry 52.40 --stop 51.80
    python3 daytrade.py add --ticker SAP --shares 30 --entry 182.10 --exit 184.00 --setup Breakout
    python3 daytrade.py check
    python3 daytrade.py stats --since 2026-11-01
"""

import argparse
import csv
import datetime as dt
import json
import math
import os
import sys

DEFAULTS = {
    "konto": 5000.0,              # Kontogröße in Euro
    "risiko_pct": 1.0,            # Risiko pro Trade in % des Kontos
    "tagesverlust_pct": 3.0,      # Tages-Stopp in % des Kontos ...
    "tagesverlust_eur": None,     # ... oder fest in Euro (hat Vorrang)
    "max_trades_tag": 5,          # höchstens so viele Trades pro Tag
    "max_verluste_folge": 3,      # nach so vielen Verlusten in Folge Pause
    "max_position_pct": 25.0,     # höchstens so viel % des Kontos in einer Position
    "gebuehr": 1.0,               # Gebühr pro Order in Euro (Trade Republic: 1 €)
}
CONFIG = os.path.join("trader", "daytrade.json")
JOURNAL = os.path.join("trader", "daytrade-journal.csv")
FIELDS = ["datum", "ticker", "stueck", "einstieg", "ausstieg", "setup", "notiz", "gebuehren", "ergebnis"]
HINWEIS = "Rechenhilfe, keine Anlageberatung. Du entscheidest und handelst selbst."


class DayError(Exception):
    pass


# ---------------------------------------------------------------- Formate

def eur(x):
    """1234.5 -> '1.234,50 €'."""
    s = "{:,.2f}".format(abs(x)).replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if x < 0 else "") + s + " €"


def num(x, nd=2):
    return "{:.{}f}".format(x, nd).replace(".", ",")


def plural(n, one, many):
    return "%d %s" % (n, one if n == 1 else many)


def pct(x):
    return num(x, 1) + " %"


def parse_num(s):
    """Akzeptiert 52.40 und 52,40."""
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip().replace("€", "").replace(" ", "")
    if "," in s and "." in s:          # 1.234,56
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        raise DayError("keine Zahl: %r" % s)


def today():
    return dt.date.today().isoformat()


# ---------------------------------------------------------------- Dateien

def load_config(path, overrides=None):
    cfg = dict(DEFAULTS)
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for k, v in data.items():
            if k in cfg:
                cfg[k] = v
    for k, v in (overrides or {}).items():
        if v is not None:
            cfg[k] = v
    if cfg["konto"] is None or float(cfg["konto"]) <= 0:
        raise DayError("die Kontogröße fehlt oder ist nicht positiv (konto in %s oder --konto)" % CONFIG)
    return cfg


def day_limit(cfg):
    if cfg.get("tagesverlust_eur"):
        return float(cfg["tagesverlust_eur"])
    return float(cfg["konto"]) * float(cfg["tagesverlust_pct"]) / 100.0


def read_journal(path):
    if not path or not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                r["stueck"] = parse_num(r["stueck"])
                r["einstieg"] = parse_num(r["einstieg"])
                r["ausstieg"] = parse_num(r["ausstieg"])
                r["gebuehren"] = parse_num(r.get("gebuehren") or 0)
                r["ergebnis"] = parse_num(r["ergebnis"])
            except (KeyError, DayError) as e:
                raise DayError("Journal-Zeile kaputt (%s): %r" % (e, r))
            rows.append(r)
    return rows


def append_journal(path, row):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        out = dict(row)
        for k in ("einstieg", "ausstieg", "gebuehren", "ergebnis"):
            out[k] = "%.2f" % out[k] if k in ("gebuehren", "ergebnis") else ("%.4f" % out[k]).rstrip("0").rstrip(".")
        out["stueck"] = ("%.4f" % out["stueck"]).rstrip("0").rstrip(".")
        w.writerow(out)


# ---------------------------------------------------------------- Rechnen

def floor_shares(x):
    """Ganze Stück abrunden, ohne an Gleitkomma-Resten (79,9999...) zu scheitern."""
    return math.floor(round(x, 6))


def size(cfg, entry, stop, target=None, cash=None):
    """Stückzahl für einen Long-Trade. Gibt ein dict zurück."""
    if entry <= 0 or stop <= 0:
        raise DayError("Einstieg und Stopp müssen positiv sein")
    if stop >= entry:
        raise DayError("der Stopp muss unter dem Einstieg liegen (Trade Republic: nur Long, keine Leerverkäufe)")
    konto = float(cfg["konto"])
    fees = 2 * float(cfg["gebuehr"])
    budget = konto * float(cfg["risiko_pct"]) / 100.0
    per_share = entry - stop
    by_risk = floor_shares(max(budget - fees, 0) / per_share)
    by_pos = floor_shares(konto * float(cfg["max_position_pct"]) / 100.0 / entry)
    avail = konto if cash is None else cash
    by_cash = floor_shares(max(avail - float(cfg["gebuehr"]), 0) / entry)
    shares = max(min(by_risk, by_pos, by_cash), 0)
    if shares == by_risk:
        limit = "Risiko pro Trade"
    elif shares == by_pos:
        limit = "max. Positionsgröße"
    else:
        limit = "verfügbares Geld"
    risk = round(shares * per_share + fees, 2)
    out = {
        "stueck": shares, "begrenzt_durch": limit, "einstieg": entry, "stopp": stop,
        "positionswert": round(shares * entry, 2), "risiko_eur": risk if shares else 0.0,
        "risiko_pct": (risk / konto * 100.0) if shares else 0.0, "risiko_budget": budget,
        "stopp_abstand_pct": per_share / entry * 100.0, "gebuehren": fees,
        "ziel_2r": entry + 2 * per_share,
    }
    if target is not None:
        if target <= entry:
            raise DayError("das Kursziel muss über dem Einstieg liegen")
        gain = round(shares * (target - entry) - fees, 2)
        out["ziel"] = target
        out["gewinn_bei_ziel"] = gain
        out["crv"] = (target - entry) / per_share
    return out


def trade_result(shares, entry, exit_, fee):
    fees = 2 * fee
    return round((exit_ - entry) * shares - fees, 2), fees


def day_status(cfg, rows, date):
    todays = [r for r in rows if r["datum"] == date]
    pnl = sum(r["ergebnis"] for r in todays)
    streak = 0
    for r in reversed(todays):
        if r["ergebnis"] < 0:
            streak += 1
        else:
            break
    limit = day_limit(cfg)
    reasons = []
    if pnl <= -limit:
        reasons.append("Tagesverlust %s erreicht das Limit von %s" % (eur(pnl), eur(-limit)))
    if len(todays) >= int(cfg["max_trades_tag"]):
        reasons.append("%d von %d Trades für heute gemacht" % (len(todays), int(cfg["max_trades_tag"])))
    if streak >= int(cfg["max_verluste_folge"]):
        reasons.append("%d Verluste in Folge" % streak)
    return {
        "datum": date, "trades": len(todays), "ergebnis": pnl, "limit": limit,
        "rest_bis_limit": limit + pnl, "verluste_folge": streak,
        "stopp": bool(reasons), "gruende": reasons,
        "trades_uebrig": max(int(cfg["max_trades_tag"]) - len(todays), 0),
    }


def stats(rows):
    if not rows:
        return {"trades": 0}
    wins = [r["ergebnis"] for r in rows if r["ergebnis"] > 0]
    losses = [r["ergebnis"] for r in rows if r["ergebnis"] <= 0]
    total = sum(r["ergebnis"] for r in rows)
    fees = sum(r["gebuehren"] for r in rows)
    gross = total + fees
    out = {
        "trades": len(rows), "gewinner": len(wins), "verlierer": len(losses),
        "trefferquote": len(wins) / len(rows) * 100.0,
        "summe": total, "brutto": gross, "gebuehren": fees,
        "schnitt_gewinn": sum(wins) / len(wins) if wins else 0.0,
        "schnitt_verlust": sum(losses) / len(losses) if losses else 0.0,
        "erwartung": total / len(rows),
        "gewinnfaktor": (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else None,
        "bester": max(rows, key=lambda r: r["ergebnis"]),
        "schlechtester": min(rows, key=lambda r: r["ergebnis"]),
        "gebuehren_anteil": (fees / gross * 100.0) if gross > 0 else None,
        "tage": len({r["datum"] for r in rows}),
    }
    setups = {}
    for r in rows:
        s = setups.setdefault(r.get("setup") or "(ohne)", {"trades": 0, "gewinner": 0, "summe": 0.0})
        s["trades"] += 1
        s["gewinner"] += 1 if r["ergebnis"] > 0 else 0
        s["summe"] += r["ergebnis"]
    out["setups"] = setups
    return out


# ---------------------------------------------------------------- Befehle

def cmd_size(a, cfg):
    st = day_status(cfg, read_journal(a.journal), a.datum or today())
    if st["stopp"]:
        print("STOPP für heute: " + "; ".join(st["gruende"]) + ".")
        print("Kein neuer Trade. Morgen geht es weiter. " + HINWEIS)
        return 2
    r = size(cfg, parse_num(a.entry), parse_num(a.stop),
             parse_num(a.ziel) if a.ziel else None, parse_num(a.cash) if a.cash else None)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r["stueck"] else 1
    if not r["stueck"]:
        print("Kein Trade möglich: Bei einem Stopp-Abstand von %s (%s) und einem Risiko-Budget von %s "
              "reicht es nicht für 1 Stück (Gebühren %s eingerechnet)."
              % (eur(r["einstieg"] - r["stopp"]), pct(r["stopp_abstand_pct"]), eur(r["risiko_budget"]), eur(r["gebuehren"])))
        print("Engerer Stopp, günstigere Aktie oder diesen Trade auslassen. " + HINWEIS)
        return 1
    print("Kauf: %d Stück zu %s, Stopp %s (Abstand %s)" % (r["stueck"], eur(r["einstieg"]), eur(r["stopp"]), pct(r["stopp_abstand_pct"])))
    print("  Positionswert   %s" % eur(r["positionswert"]))
    print("  Risiko bei Stopp %s = %s des Kontos (Budget %s, inkl. %s Gebühren)"
          % (eur(r["risiko_eur"]), pct(r["risiko_pct"]), eur(r["risiko_budget"]), eur(r["gebuehren"])))
    print("  begrenzt durch  %s" % r["begrenzt_durch"])
    print("  Ziel bei 2R     %s" % eur(r["ziel_2r"]))
    if "ziel" in r:
        print("  dein Ziel %s: Chance/Risiko %s : 1, Gewinn bei Ziel %s"
              % (eur(r["ziel"]), num(r["crv"], 1), eur(r["gewinn_bei_ziel"])))
        if r["crv"] < 1.5:
            print("  Hinweis: Chance/Risiko unter 1,5 : 1. Dann muss deutlich mehr als jeder zweite Trade aufgehen.")
    print("Heute: %d von %d Trades, Ergebnis %s, noch %s bis zum Tages-Stopp."
          % (st["trades"], int(cfg["max_trades_tag"]), eur(st["ergebnis"]), eur(st["rest_bis_limit"])))
    print("Den Stopp sofort mit der Order in der Trade-Republic-App setzen. " + HINWEIS)
    return 0


def cmd_add(a, cfg):
    shares = parse_num(a.shares)
    entry, exit_ = parse_num(a.entry), parse_num(a.exit)
    if shares <= 0 or entry <= 0 or exit_ <= 0:
        raise DayError("Stück, Einstieg und Ausstieg müssen positiv sein")
    fee = parse_num(a.gebuehr) if a.gebuehr is not None else float(cfg["gebuehr"])
    pnl, fees = trade_result(shares, entry, exit_, fee)
    row = {"datum": a.datum or today(), "ticker": a.ticker.upper(), "stueck": shares, "einstieg": entry,
           "ausstieg": exit_, "setup": a.setup or "", "notiz": a.notiz or "", "gebuehren": fees, "ergebnis": pnl}
    append_journal(a.journal, row)
    print("Eingetragen: %s %s Stück %s -> %s, Ergebnis %s (nach %s Gebühren)."
          % (row["ticker"], num(shares, 0) if shares == int(shares) else num(shares, 4),
             eur(entry), eur(exit_), eur(pnl), eur(fees)))
    st = day_status(cfg, read_journal(a.journal), row["datum"])
    print("Heute: %s, Ergebnis %s." % (plural(st["trades"], "Trade", "Trades"), eur(st["ergebnis"])))
    if st["stopp"]:
        print("STOPP für heute: " + "; ".join(st["gruende"]) + ". Keine weiteren Trades.")
        return 2
    return 0


def cmd_check(a, cfg):
    st = day_status(cfg, read_journal(a.journal), a.datum or today())
    if a.json:
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 2 if st["stopp"] else 0
    print("Tagesstatus %s: %s, Ergebnis %s, Tages-Stopp bei %s."
          % (st["datum"], plural(st["trades"], "Trade", "Trades"), eur(st["ergebnis"]), eur(-st["limit"])))
    if st["stopp"]:
        print("STOPP: " + "; ".join(st["gruende"]) + ". Für heute keine neuen Trades.")
        return 2
    print("OK: noch %d Trades und %s Verlustspielraum. Verluste in Folge: %d von %d."
          % (st["trades_uebrig"], eur(st["rest_bis_limit"]), st["verluste_folge"], int(cfg["max_verluste_folge"])))
    return 0


def cmd_stats(a, cfg):
    rows = read_journal(a.journal)
    if a.since:
        rows = [r for r in rows if r["datum"] >= a.since]
    if a.setup:
        rows = [r for r in rows if (r.get("setup") or "").lower() == a.setup.lower()]
    s = stats(rows)
    if a.json:
        s2 = dict(s)
        for k in ("bester", "schlechtester"):
            if k in s2:
                s2[k] = {kk: vv for kk, vv in s2[k].items()}
        print(json.dumps(s2, ensure_ascii=False, indent=2))
        return 0 if s["trades"] else 1
    if not s["trades"]:
        print("Noch keine Trades im Journal (%s)." % a.journal)
        return 1
    print("Auswertung: %s an %s" % (plural(s["trades"], "Trade", "Trades"), plural(s["tage"], "Tag", "Tagen")))
    print("  Trefferquote     %s (%d Gewinner, %d Verlierer)" % (pct(s["trefferquote"]), s["gewinner"], s["verlierer"]))
    print("  Ergebnis netto   %s (brutto %s, Gebühren %s)" % (eur(s["summe"]), eur(s["brutto"]), eur(s["gebuehren"])))
    print("  Schnitt Gewinn   %s, Schnitt Verlust %s" % (eur(s["schnitt_gewinn"]), eur(s["schnitt_verlust"])))
    print("  Erwartung/Trade  %s" % eur(s["erwartung"]))
    print("  Gewinnfaktor     %s" % (num(s["gewinnfaktor"]) if s["gewinnfaktor"] is not None else "-"))
    if s["gebuehren_anteil"] is not None:
        print("  Gebühren fressen %s des Bruttogewinns" % pct(s["gebuehren_anteil"]))
    b, w = s["bester"], s["schlechtester"]
    print("  bester Trade     %s %s am %s" % (b["ticker"], eur(b["ergebnis"]), b["datum"]))
    print("  schlechtester    %s %s am %s" % (w["ticker"], eur(w["ergebnis"]), w["datum"]))
    print("Nach Setup:")
    for name, v in sorted(s["setups"].items(), key=lambda kv: -kv[1]["summe"]):
        print("  %-16s %s, Treffer %s, Summe %s"
              % (name, plural(v["trades"], "Trade", "Trades"), pct(v["gewinner"] / v["trades"] * 100.0), eur(v["summe"])))
    if s["trades"] < 30:
        print("Hinweis: Unter 30 Trades sind diese Zahlen noch stark vom Zufall geprägt.")
    print("Ergebnisse vor Steuern; Trade Republic führt die Abgeltungsteuer selbst ab. " + HINWEIS)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Risiko-Rechner und Trade-Journal für Daytrading (trader-daytrade). Platziert nie Orders.")
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--journal", default=JOURNAL)
    ap.add_argument("--konto", help="Kontogröße in Euro (überschreibt die Config)")
    ap.add_argument("--risiko-pct", help="Risiko pro Trade in Prozent")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("size", help="Positionsgröße nach Stopp-Abstand")
    p.add_argument("--entry", required=True, help="geplanter Einstieg")
    p.add_argument("--stop", required=True, help="Stopp-Kurs")
    p.add_argument("--ziel", help="Kursziel, für Chance/Risiko")
    p.add_argument("--cash", help="verfügbares Geld, falls weniger als das Konto")
    p.add_argument("--datum")

    p = sub.add_parser("add", help="abgeschlossenen Trade eintragen")
    p.add_argument("--ticker", required=True)
    p.add_argument("--shares", required=True, help="Stückzahl")
    p.add_argument("--entry", required=True)
    p.add_argument("--exit", required=True)
    p.add_argument("--setup", help="z. B. Breakout, Pullback, Gap")
    p.add_argument("--notiz")
    p.add_argument("--gebuehr", help="Gebühr pro Order, falls abweichend")
    p.add_argument("--datum", help="JJJJ-MM-TT, Standard heute")

    p = sub.add_parser("check", help="Tagesstatus und Tages-Stopp")
    p.add_argument("--datum")

    p = sub.add_parser("stats", help="Auswertung des Journals")
    p.add_argument("--since", help="ab Datum JJJJ-MM-TT")
    p.add_argument("--setup")

    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        over = {"konto": parse_num(a.konto) if a.konto else None,
                "risiko_pct": parse_num(a.risiko_pct) if a.risiko_pct else None}
        cfg = load_config(a.config, over)
        return {"size": cmd_size, "add": cmd_add, "check": cmd_check, "stats": cmd_stats}[a.cmd](a, cfg)
    except DayError as e:
        print("Fehler: %s" % e, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
