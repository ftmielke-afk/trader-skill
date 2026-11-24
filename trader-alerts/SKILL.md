---
name: trader-alerts
description: >-
  Kursalarme. Meldet sich, wenn ein Kursziel, ein Stopp oder die
  Eröffnungsglocke erreicht ist: Regeln für über / unter / Stopp,
  Prozentbewegungen gegenüber dem Vortagesschluss und die Eröffnungsglocke der
  NYSE, jede nur einmal, damit kein Spam entsteht. Kennt die Handelszeiten der
  NYSE mit den Feiertagen 2026 und 2027 und den verkürzten Handelstagen bis
  13:00 Uhr, holt kostenlose verzögerte Kurse (Yahoo Chart JSON, Stooq CSV)
  Ticker für Ticker und schreibt trader/prices.json für die anderen Skills.
  Verwenden, wenn der Nutzer sagt „sag mir Bescheid, wenn“, „melde dich, wenn
  AAPL X erreicht“, „setz einen Stopp“, „Kursziel“, „beobachte meine Aktien“,
  „ist die Börse offen“, „wann öffnet die Börse“, „hol mir Kurse“, oder um
  Preise vor Einteilung, Risiko oder Steuer zu aktualisieren.
argument-hint: "[Ticker] [Preis]"
---

# trader-alerts

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle und Dateinamen
unverändert. Uhrzeiten der NYSE nennst du in New Yorker Zeit und, wenn es
hilft, zusätzlich in deutscher Zeit (meist 15:30 bis 22:00 Uhr MEZ/MESZ).

Kursalarme beobachten die Zahlen, damit der Nutzer es nicht muss. Ein Alarm
ist eine Information, nie eine Order: Wenn ein Stopp anschlägt, wird nichts
verkauft. Will der Nutzer handeln, läuft der normale Weg (Einteilung, Risiko,
sein Ja).

`${CLAUDE_SKILL_DIR}` unten ist der Ordner dieses Skills (wo diese SKILL.md liegt).

```bash
python3 "${CLAUDE_SKILL_DIR}/alerts.py" clock                         # NYSE offen oder zu, nächste Öffnung
python3 "${CLAUDE_SKILL_DIR}/alerts.py" quote AAPL KO --write         # -> trader/prices.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" quote --holdings --write      # Ticker aus Portfolio + Zielen
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol AAPL --above 350
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol BAC --stop 50 --note "mein Stopp"
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol KO --pct 3
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --opening-bell
python3 "${CLAUDE_SKILL_DIR}/alerts.py" check                         # Exit 0 = etwas hat angeschlagen
python3 "${CLAUDE_SKILL_DIR}/alerts.py" list
python3 "${CLAUDE_SKILL_DIR}/alerts.py" reset aapl-above-350
```

## Was er liest und schreibt

| Datei | Inhalt |
| --- | --- |
| `trader/alerts.json` | die Regeln (`alerts.example.json` in diesem Ordner) |
| `trader/state/alerts.json` | welche Regeln wann angeschlagen haben, damit jede nur einmal anschlägt |
| `trader/prices.json` | die neuesten Kurse, eingepflegt, für trader-budget, trader-risk, trader-tax und trader-rebalance |

## Regeltypen

| Typ | schlägt an, wenn | schlägt erneut an |
| --- | --- | --- |
| `above` | Kurs bei oder über `price` | nach `reset`, oder von selbst bei `"rearm": true`, wenn der Kurs wieder gefallen ist |
| `below` / `stop` | Kurs bei oder unter `price` | genauso |
| `pct_move` | um `pct` Prozent vom Vortagesschluss (oder `ref`) bewegt, optional `direction` up oder down | höchstens einmal am Tag |
| `opening_bell` | die NYSE ist offen | einmal pro Handelstag |

## Kurse

- `yahoo` (Standard): `query1.finance.yahoo.com/v8/finance/chart/<TICKER>`,
  ein inoffizieller kostenloser JSON-Endpunkt, eine Anfrage pro Ticker, im
  Abstand von einer halben Sekunde.
- `stooq`: `stooq.com/q/l/?s=aapl.us&f=sd2t2ohlcv&h&e=csv`, Stooqs kostenlose
  CSV. Sie antwortete beim Schreiben (13.10.2026) mit 404; der Parser bleibt
  für den Fall, dass sie zurückkommt. Mit `--source stooq` ausprobieren.
- Kostenlose Kurse sind verzögert. Sie reichen für Alarme und zum Prüfen von
  Größen, nicht zum Timen einer Order. Der Kurs des Brokers ist der, zu dem
  ausgeführt wird.
- Sind beide ausgefallen, Kurse aus dem Broker-Connector lesen (Alpaca
  `get_stock_snapshot`, IBKR `get_price_snapshot`) und in `trader/prices.json`
  schreiben als `{"as_of": "...", "prices": {"AAPL": 341.27}}`.

## Die NYSE-Uhr

Reguläre Sitzung 9:30 bis 16:00 Uhr New Yorker Zeit, geschlossen an
Wochenenden und an diesen Feiertagen, laut nyse.com/markets/hours-calendars
(gelesen am 13.10.2026):

- 2026: 1. Jan., 19. Jan., 16. Feb., 3. Apr. (Karfreitag), 25. Mai, 19. Juni,
  3. Juli (Independence Day, nachgeholt), 7. Sep., 26. Nov., 25. Dez. Früher
  Schluss um 13:00 Uhr am 27. Nov. und 24. Dez.
- 2027: 1. Jan., 18. Jan., 15. Feb., 26. März (Karfreitag), 31. Mai, 18. Juni
  (Juneteenth, nachgeholt), 5. Juli (Independence Day, nachgeholt), 6. Sep.,
  25. Nov., 24. Dez. (Weihnachten, nachgeholt). Früher Schluss um 13:00 Uhr am
  26. Nov.

Die Sommerzeit berechnet das Tool selbst, es braucht also keine
Zeitzonendateien. Für jedes andere Jahr sagt es, dass die Feiertagsliste
unbekannt ist.

## Schritte

1. Frag, was beobachtet werden soll, in den Worten des Nutzers („sag mir
   Bescheid, wenn Apple unter 320 $ fällt“), und füge die Regel hinzu.
   Bestätige sie: Ticker, Typ, Marke.
2. Führ `check` jetzt aus und, wenn der Nutzer will, nach Zeitplan (eine
   geplante Aufgabe in Claude oder cron, alle 15 Minuten während der
   Handelszeiten reicht völlig). Jeder Lauf holt nur die Ticker aus den Regeln
   und lässt jeden Alarm einmal anschlagen.
3. Sag dem Nutzer in je einer Zeile, was angeschlagen hat. Will er handeln,
   schick ihn zur Einteilung und zu `/trader-risk`. Handle nie für ihn.

## Beispiel: das Portfolio aus dem Beispiellauf

Nachdem das Kopie-Portfolio gekauft ist: `add --opening-bell`, `add --symbol
AAPL --above 350` und `add --symbol BAC --stop 50`. Am 13.10.2026 schloss AAPL
bei 341,27 $ und BAC bei 53,96 $, also gibt `check` an diesem Abend „Nothing
hit“ aus (nichts erreicht) und endet mit Exit-Code 1. Um 9:30 Uhr am nächsten
Morgen schlägt die Eröffnungsglocke einmal an.

## Was er nie tut

Er platziert, storniert oder ändert nie eine Order, behauptet nie, ein Kurs
sei in Echtzeit, und sagt nie voraus, wohin ein Kurs geht.

## Sicherheit

- Bildung und Werkzeuge, keine Anlageberatung. Ein Alarm ist eine Tatsache über einen Kurs, kein Handelssignal.
- Standardmäßig Paper Trading (`"paper": true`). Live zu gehen ist allein die Entscheidung des Nutzers, in seiner eigenen Config.
- Nichts in diesem Paket platziert eine Order außer trader-broker, und nur wenn alle drei Bedingungen
  erfüllt sind: trader-risk hat genau diese Order heute durchgelassen, der Nutzer hat im Chat ein
  ausdrückliches Ja für genau diese eine Order getippt, und der Nutzer hat auf Claudes eigener Karte
  „Allow once“ geklickt, weil das Order-Tool auf „Needs approval“ steht (Customize > Connectors >
  Tool-Berechtigungen). Ein Order-Tool nie auf „Always allow“ stellen.
- Keine Optionen, kein Margin, keine Leerverkäufe und kein Hebel, außer die Config erlaubt es und der Nutzer bestätigt.
- Broker-Schlüssel liegen in Umgebungsvariablen oder der Claude-Desktop-Config, niemals im Chat.
