---
name: trader-screener
description: >-
  Der Aktien-Screener. Prüft eine Liste von Unternehmen gegen die eigenen
  Regeln des Nutzers (Umsatzwachstum, Margen, EPS, KGV, Gewinnrendite, Sektor,
  alles in der Kennzahlendatei), sagt genau, welche Regel jedes Unternehmen
  besteht oder verfehlt und um wie viel, und ordnet die bestandenen in eine
  Shortlist. Liest die Kennzahlen, die /trader-analyst aus SEC-Meldungen
  schreibt, oder jede CSV. Verwenden, wenn der Nutzer sagt „screene nach
  Aktien“, „finde Unternehmen, die“, „filtere meine Watchlist“, „welche davon
  erfüllen meine Regeln“, „Kandidaten auswählen“, „ordne diese Aktien“ oder
  „wachsende Unternehmen unter dem 30-fachen Gewinn“.
argument-hint: "[Kennzahlendatei] [--rules rules.json]"
---

# trader-screener

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle, Dateinamen und
Kennzahl-Namen wie `revenue_growth_yoy` unverändert.

Ein Screen macht aus „ich will profitable Unternehmen, die noch wachsen und
nicht zu teuer sind“ Regeln, die ein Computer prüfen kann, und legt seine
Arbeit offen: Jedes Bestehen und jedes Scheitern kommt mit der Zahl und dem
Schwellenwert.

Tool in diesem Ordner (Python mit Standardbibliothek, kein Netzwerk):

```bash
python3 "${CLAUDE_SKILL_DIR}/screen.py" --help
```

## Was er liest und schreibt

- Kennzahlen: `trader/metrics.json` von `/trader-analyst` (`facts.py --metrics`)
  oder jede JSON-Liste oder CSV mit einer Spalte `ticker`. Zahlen in der CSV
  dürfen `$`, `%` und Kommas enthalten.
- Preise (optional): `trader/prices.json` (`{"prices": {"AAPL": 341.27}}`,
  beliebige Quelle; `/trader-alerts` schreibt sie). Mit Preisen ergänzt er
  `price`, `pe` (KGV: Preis / EPS der letzten zwölf Monate, nur bei positivem
  EPS) und `earnings_yield` (Gewinnrendite).
- Regeln: eine JSON-Datei, als Ausgangspunkt `rules.example.json` in diesem Ordner.
- Schreibt mit `--out` die Datei `trader/shortlist.json`: wer bestanden hat,
  die Punktzahl und warum, wer gescheitert ist und warum.

## Die Regeldatei

```json
{"name": "Growing, profitable, not priced for perfection",
 "rules": [{"metric": "revenue_growth_yoy", "op": ">=", "value": 10},
           {"metric": "operating_margin", "op": ">=", "value": 25},
           {"metric": "pe", "op": "<=", "value": 35}],
 "rank":  [{"metric": "revenue_growth_yoy", "order": "desc", "weight": 2},
           {"metric": "pe", "order": "asc", "weight": 1}],
 "missing": "fail"}
```

Operatoren: `>`, `>=`, `<`, `<=`, `==`, `!=`, `between` ([unten, oben]), `in`
und `not in` (eine Liste, für auszuschließende Ticker oder Sektoren).
`"missing": "fail"` lässt ein Unternehmen scheitern, dem eine Kennzahl fehlt,
die eine Regel braucht (Banken haben in den SEC-Fakten keine operative Marge);
`"skip"` ignoriert diese Regel für das Unternehmen und sagt das. Das Ranking
bewertet jedes bestandene Unternehmen pro Ranking-Kennzahl von 0 bis 1 und
bildet den gewichteten Durchschnitt. Der Name der Regeldatei darf auch deutsch
sein.

## Schritte

1. Mach aus den Worten des Nutzers Regeln. Frag nach, wenn ein Schwellenwert
   vage ist („günstig“ heißt welches KGV?). Schreib sie in `trader/rules.json`.
2. Hol Kennzahlen für die Kandidaten: Lass `/trader-analyst` mit
   `--metrics trader/metrics.json` darüber laufen (dessen `facts.py AAPL AXP
   GOOGL KO BAC --metrics trader/metrics.json`) oder nimm die eigene CSV des
   Nutzers. Preise aus `trader/prices.json`, wenn das KGV zählt.
3. Führ den Screen aus:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/screen.py" trader/metrics.json --rules trader/rules.json \
     --prices trader/prices.json --out trader/shortlist.json
   ```

   Exit-Code 1 heißt: nichts hat bestanden. Sag das und zeig die knappsten
   Verfehlungen.
4. Berichte die Shortlist mit den Gründen, die Verfehlungen mit den Zahlen,
   die gescheitert sind, und die Stichtage der Zahlen (das letzte Quartalsende
   pro Unternehmen, das Datum der Preise). Schlag `/trader-analyst` für die
   obersten Namen vor, bevor irgendetwas anderes passiert.

## Beispiel: die fünf aus dem Beispiellauf

Kennzahlen von der SEC für AAPL, AXP, GOOGL, KO und BAC, Schlusskurse vom
13.10.2026 und `rules.example.json`:

```
Growing, profitable, not priced for perfection: 2 of 5 companies pass.
 1. PASS GOOGL  Alphabet Inc.  score 0.75   (growth 24.2, P/E 17.8)
 2. PASS KO     COCA COLA CO   score 0.25   (growth 12.1, P/E 28.3)
    FAIL AAPL   pe 39.2, needs <= 35
    FAIL BAC    operating_margin is missing
    FAIL AXP    revenue_growth_yoy 8.6, needs >= 10; operating_margin is missing
```

Auf Deutsch: 2 von 5 bestehen. Alphabet (Wachstum 24,2 %, KGV 17,8) vor
Coca-Cola (Wachstum 12,1 %, KGV 28,3). Apple scheitert am KGV von 39,2 (Grenze
35), Bank of America an der fehlenden operativen Marge, American Express am
Wachstum von 8,6 % (Grenze 10) und der fehlenden operativen Marge.

Dann die Vorbehalte, die ein sorgfältiger Analyst ergänzt: In Alphabets
neuestem Quartal liegt der Nettogewinn über dem operativen Ergebnis (Gewinne
außerhalb des Geschäfts), und die Zahlen von Coca-Cola enden mit dem Quartal
zum 03.04.2026, weil die SEC-Fakten dem neuesten 10-Q hinterherhinken.

## Was er nie tut

- Nennt ein bestandenes Unternehmen nie einen Kauf. Ein Screen ist ein Filter
  auf gemeldete Zahlen, keine Empfehlung.
- Füllt nie eine fehlende Zahl auf und rät nie eine Kennzahl: fehlend heißt fehlend.
- Schickt nie von sich aus etwas an `/trader-budget` oder in einen Order-Weg.

## Sicherheit

Bildung und Werkzeuge, keine Anlageberatung. Dieser Skill filtert nur Zahlen.
Nichts platziert eine Order außer `/trader-broker`, nachdem `/trader-risk` sie
durchgelassen hat und der Nutzer ein ausdrückliches Ja für genau diese Order
getippt hat.
