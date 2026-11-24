---
name: trader-budget
description: >-
  Budget-Manager. Teilt jede Position nach dem Budget des Nutzers ein, bevor
  irgendetwas gekauft wird: hält einen Cash-Puffer, begrenzt jede einzelne
  Aktie (der Überschuss wird auf die anderen verteilt), streicht Anteile unter
  der Mindestorder, rundet so, dass jeder Dollar verwendet wird, unterstützt
  Bruchstücke oder ganze Aktien und schreibt die vorgeschlagenen Kauforders in
  trader/orders.json, genau im Format von Alpacas place_stock_order (notional
  als String). Nichts wird platziert. Verwenden, wenn der Nutzer sagt „ich habe
  5.000 $“, „teil meine Trades ein“, „wie viel soll ich von jeder kaufen“,
  „verwalte mein Budget“, „teil mein Geld auf“, „behalte 10 % Cash“, „keine
  Aktie über 25 %“, „leg meine Regeln fest“, oder nachdem /trader-copycat
  Ziele geschrieben hat.
argument-hint: "[Budget in Dollar]"
---

# trader-budget

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle und Dateinamen
unverändert.

Der Budget-Manager macht aus „kopiere dieses Portfolio“ ein „kaufe genau so
viel von jeder“, innerhalb von Regeln, die der Nutzer einmal festlegt. Er
schreibt nur Vorschläge. trader-risk prüft sie, und trader-broker fragt den
Nutzer für jede einzelne nach ja oder nein.

`${CLAUDE_SKILL_DIR}` unten ist der Ordner dieses Skills (wo diese SKILL.md liegt).

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py"                       # trader/targets.json + trader/config.json
python3 "${CLAUDE_SKILL_DIR}/size.py" --budget 5000 --write # trader/orders.json schreiben
python3 "${CLAUDE_SKILL_DIR}/size.py" --whole-shares --prices trader/prices.json
python3 "${CLAUDE_SKILL_DIR}/size.py" --weights AAPL=22.04,AXP=17.14,GOOGL=12.62 --json
```

## Was er liest und schreibt

| Datei | Inhalt |
| --- | --- |
| `trader/config.json` | die Regeln (Vorlage: `config.example.json` in diesem Ordner) |
| `trader/targets.json` | die zu kopierenden Gewichte, geschrieben von trader-copycat (hier `targets.example.json`) |
| `trader/prices.json` | nur für ganze Aktien oder Stückzahlen (trader-alerts schreibt sie) |
| `trader/orders.json` | die vorgeschlagenen Kauforders, die er mit `--write` schreibt |

## Schritt 1: die Regeln einmal festlegen

Gibt es `trader/config.json` noch nicht, kopiere `config.example.json` nach
`trader/config.json` und frag den Nutzer in einfachen Worten nach jedem Wert:

- **budget**: um wie viel Geld es geht. Nur Geld, dessen Verlust er sich leisten kann.
- **cash_buffer_pct**: wie viel in Cash bleibt (Standard 10).
- **max_position_pct**: der Höchstanteil einer einzelnen Aktie in Prozent des Budgets (Standard 25).
- **max_order_usd** und **min_order_usd**: die größte und kleinste Einzelorder (2000 und 5).
- **fractional**: true, wenn der Broker Bruchstücke von Aktien kauft (Alpaca tut das); false für ganze Aktien.
- **blocked**: Ticker, die er nie besitzen will.
- **paper** auf true lassen, bis er gesehen hat, wie es auf einem Paper-Konto funktioniert.

## Schritt 2: einteilen

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py" --write
```

Die Rechnung, der Reihe nach: Der Cash-Puffer wird zuerst abgezogen; die
Gewichte werden über die verbleibenden Aktien auf 100 hochgerechnet; jede Aktie
über der Obergrenze wird auf die Obergrenze gesetzt und ihr Überschuss nach
Gewicht auf die anderen verteilt, wiederholt, bis keine mehr darüber liegt; ein
Anteil unter der Mindestorder wird gestrichen und sein Gewicht verteilt; die
Beträge werden auf ganze Dollar gerundet, und der Rundungsdollar geht an die
größte nicht gedeckelte Aktie, damit nichts versehentlich ungenutzt bleibt.
Geld, das sich wirklich nicht investieren lässt (jede Aktie an ihrer
Obergrenze, oder ganze Aktien, die nicht aufgehen), wird als „ungenutzt“
ausgewiesen.

## Schritt 3: dem Nutzer zeigen

Zeig die Tabelle: Ticker, Gewicht, Dollar, welche Aktie die Obergrenze
erreicht hat, den Cash-Puffer und was ungenutzt bleibt. Sag, woher die Gewichte
stammen und wie alt sie sind (eine 13F ist bei der Einreichung bis zu 45 Tage
alt). Übergib dann an `/trader-risk`.

## Beispiel: der Beispiellauf

Berkshire Hathaways 13F für Q2 2026 (eingereicht am 14.08.2026), Top fünf:
Apple 22,04 %, American Express 17,14 %, Alphabet 12,62 %, Coca-Cola 10,86 %,
Bank of America 9,20 %. Über diese fünf hochgerechnet: 30,67 / 23,85 / 17,56 /
15,11 / 12,80. Ein Budget von 5.000 $, 10 % Cash-Puffer und 25 % Obergrenze:

| Aktie | Dollar | |
| --- | --- | --- |
| AAPL | 1.250 $ | auf 25 % gedeckelt |
| AXP | 1.119 $ | |
| GOOGL | 823 $ | |
| KO | 708 $ | |
| BAC | 600 $ | |
| Cash-Puffer | 500 $ | |
| ungenutzt | 0 $ | |

Die erste Order, die er schreibt, ist
`{"symbol": "AAPL", "side": "buy", "notional": "1250", "type": "market", "time_in_force": "day"}`.
Behalte die Gewichte mit zwei oder mehr Nachkommastellen: Bereits auf eine
Stelle gerundete Gewichte (30,7 / 23,9 / ...) können einen Anteil um einen
Dollar verschieben.

## Regeln

- Nur Vorschläge. Dieser Skill ruft nie ein Broker-Tool auf.
- Teile nie Geld ein, von dem der Nutzer nicht gesagt hat, dass es dafür ist. Frag nach dem Budget.
- Jede Zahl stammt aus der Config, den Zielen oder den Preisen. Nichts wird geraten.
- Keine Hochrechnungen: Sag nie, was die Positionen wert sein oder einbringen werden.
- Ganze Aktien brauchen echte Preise aus `trader/prices.json`; erfinde nie einen Preis.

## Was er nie tut

Er platziert, genehmigt oder plant nie eine Order, erhöht nie eigenmächtig ein
Limit und teilt nie Optionen, Margin- oder Short-Positionen ein.

## Sicherheit

- Bildung und Werkzeuge, keine Anlageberatung. Nichts hier sagt Kurse voraus oder verspricht Renditen.
- Standardmäßig Paper Trading (`"paper": true`). Live zu gehen ist allein die Entscheidung des Nutzers, in seiner eigenen Config.
- Nichts in diesem Paket platziert eine Order außer trader-broker, und nur wenn alle drei Bedingungen
  erfüllt sind: trader-risk hat genau diese Order heute durchgelassen, der Nutzer hat im Chat ein
  ausdrückliches Ja für genau diese eine Order getippt, und der Nutzer hat auf Claudes eigener Karte
  „Allow once“ geklickt, weil das Order-Tool auf „Needs approval“ steht (Customize > Connectors >
  Tool-Berechtigungen). Ein Order-Tool nie auf „Always allow“ stellen.
- Keine Optionen, kein Margin, keine Leerverkäufe und kein Hebel, außer die Config erlaubt es und der Nutzer bestätigt.
- Broker-Schlüssel liegen in Umgebungsvariablen oder der Claude-Desktop-Config, niemals im Chat.
