---
name: trader-tax
description: >-
  Steuer-Optimierer. Verfolgt die Kaufposten (Lots) mit Einstandskosten für
  jede Position (FIFO, höchste Kosten zuerst oder bestimmte Lots), zeigt nicht
  realisierte Gewinne und Verluste pro Lot mit kurz- oder langfristig,
  berechnet vor dem Verkauf, was ein Verkauf realisieren würde, findet
  Kandidaten für Tax-Loss-Harvesting über einer Verlustschwelle, prüft die
  Wash-Sale-Regel (30 Tage davor und danach, GOOG und GOOGL als eine Familie)
  und schreibt Harvest-Verkäufe nur als Vorschläge. Keine Steuerberatung.
  Verwenden, wenn der Nutzer sagt „was sind meine Gewinne“, „Einstandskosten“,
  „Steuer-Lots“, „Verluste steuerlich nutzen“, „was würde mich ein Verkauf an
  Steuern kosten“, „kurz- oder langfristig“, „Wash Sale“, oder bevor
  irgendetwas verkauft wird.
argument-hint: "[Ticker]"
---

# trader-tax

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle und Dateinamen
unverändert.

Der Steuer-Optimierer rechnet mit den Lots des Nutzers, damit niemand blind
verkauft. Er entscheidet nie, was für die Steuern des Nutzers richtig ist.
**Das ist keine Steuerberatung**: Eine Steuerfachperson entscheidet, was für
ihn gilt. Sag das einmal, früh, in jeder Antwort, die diesen Skill nutzt.

**Wichtig für Nutzer in Deutschland:** Die Regeln unten sind US-Bundesrecht
(Haltedauer, Wash Sale). In Deutschland gelten andere Regeln, etwa die
Abgeltungsteuer ohne Unterscheidung nach Haltedauer, der
Sparer-Pauschbetrag und eigene Verlustverrechnungstöpfe für Aktien. Sag das,
wenn der Nutzer in Deutschland steuerpflichtig ist, und verweise auf eine
Steuerberaterin oder einen Steuerberater. Die Rechnung mit Lots und
Einstandskosten bleibt trotzdem nützlich.

`${CLAUDE_SKILL_DIR}` unten ist der Ordner dieses Skills (wo diese SKILL.md liegt).

```bash
python3 "${CLAUDE_SKILL_DIR}/lots.py" report --lots              # jedes Lot, Gewinn oder Verlust, Frist
python3 "${CLAUDE_SKILL_DIR}/lots.py" sell KO 2 --price 90.11    # was ein Verkauf realisieren würde (FIFO)
python3 "${CLAUDE_SKILL_DIR}/lots.py" sell KO 2 --method specific --lots KO-2
python3 "${CLAUDE_SKILL_DIR}/lots.py" harvest --min-loss 100     # Kandidaten, mit Wash-Sale-Prüfung
python3 "${CLAUDE_SKILL_DIR}/lots.py" harvest --min-loss 100 --write
python3 "${CLAUDE_SKILL_DIR}/lots.py" wash KO                    # wäre ein Kauf von KO heute ein Wash Sale?
```

## Was er liest und schreibt

| Datei | Inhalt |
| --- | --- |
| `trader/portfolio.json` | Positionen mit Lots: `{"id", "date", "shares", "cost"}` (cost = gesamte Einstandskosten); Form: `portfolio.example.json` hier |
| `trader/prices.json` | aktuelle Preise (trader-alerts: `alerts.py quote --holdings --write`) |
| `trader/orders.json` | geplante Käufe zählen für Wash Sales; `harvest --write` ersetzt die Datei durch Verkaufsvorschläge |
| `trader/state/tax.json` | die realisierten Verkäufe, die er mit `sell --record` protokolliert |

Lots stammen aus den Ausführungen, die trader-broker festhält (`ticket.py fill`),
oder aus dem Depotauszug des Nutzers. Hat eine Position Aktien, aber keine
Lots, frag nach Kaufdaten und Kosten. Erfinde nie Einstandskosten.

## Die Regeln, die er anwendet (US-Bundesrecht, nur Rechnung)

- **Frist**: langfristig, wenn mehr als ein Jahr nach dem Kaufdatum verkauft,
  sonst kurzfristig. `report --lots` zeigt das Datum, an dem jedes Lot
  langfristig wird.
- **Lot-Methoden**: `fifo` (älteste zuerst, was die meisten Broker
  standardmäßig tun), `hifo` (höchste Kosten zuerst) und `specific` (benannte
  Lots). Die an den Broker gesendete Order enthält keine Lot-IDs: Um bestimmte
  Lots zu verkaufen, muss der Nutzer sie in der Lot-Einstellung des Brokers
  selbst wählen, sonst nutzt der Broker seine Standardmethode.
- **Wash Sale**: Ein Verlust wird insoweit nicht anerkannt, wie dieselbe oder
  eine im Wesentlichen identische Aktie innerhalb von 30 Tagen vor oder nach
  dem Verkauf gekauft wird. Das Tool prüft die anderen noch gehaltenen Lots,
  geplante Käufe in `trader/orders.json` und die Verlustverkäufe, die es
  protokolliert hat. Es sieht kein IRA, kein Konto des Ehepartners und keinen
  anderen Broker, und die zählen auch. Sag das.

## Schritte

1. Preise aktualisieren, dann `lots.py report --lots`. Zeig Gewinne und
   Verluste je Aktie und welche Lots kurz- oder langfristig sind.
2. Vor jedem Verkauf (Rebalancing, ein Stopp, eine Meinungsänderung) `lots.py
   sell` mit der geplanten Stückzahl und Methode ausführen und zeigen, was er
   realisieren würde.
3. Für Harvesting: `lots.py harvest --min-loss 100` (und `--min-pct`, wenn der
   Nutzer eine Prozentschwelle will). Für jeden Kandidaten den geschätzten
   Verlust zeigen, aufgeteilt in kurz- und langfristig, jeden
   Wash-Sale-Konflikt und den ersten Tag, an dem er zurückgekauft werden
   könnte. Kandidaten mit Konflikt werden nicht vorgeschlagen.
4. Nur wenn der Nutzer Vorschläge will: `harvest --write`, dann `/trader-risk`,
   dann `/trader-broker`, ein Ja pro Order.
5. Nach einer Ausführung aktualisiert `lots.py sell ... --record` die Lots und
   protokolliert das realisierte Ergebnis für das Jahr.

## Beispiel: das Portfolio aus dem Beispiellauf

Das am 13.10.2026 gekaufte Kopie-Portfolio (AAPL 1.250 $, AXP 1.119 $, GOOGL
823 $, KO 708 $, BAC 600 $) hat ein Lot pro Aktie, alle kurzfristig bis zum
14.10.2027. Fällt BAC später unter seine Einstandskosten von 600 $, listet
`harvest --min-loss 25` das Lot BAC-1 mit seinem Verlust und „BAC nicht vor“
einem Datum 31 Tage nach dem Verkauf „wieder kaufen“. Hat der Nutzer
außerdem einen BAC-Kauf in `trader/orders.json` geplant, markiert er einen
Wash Sale, statt den Verkauf vorzuschlagen.

## Was er nie tut

Er reicht nie etwas ein, nennt nie einen Steuersatz oder eine Steuerschuld,
sagt dem Nutzer nie, was er schuldet, platziert nie eine Order und schlägt nie
ein Harvesting vor, von dem er sehen kann, dass es ein Wash Sale wäre.

## Sicherheit

- Keine Steuerberatung, und Bildung und Werkzeuge, keine Anlageberatung. Frag eine Steuerfachperson.
- Standardmäßig Paper Trading (`"paper": true`). Live zu gehen ist allein die Entscheidung des Nutzers, in seiner eigenen Config.
- Nichts in diesem Paket platziert eine Order außer trader-broker, und nur wenn alle drei Bedingungen
  erfüllt sind: trader-risk hat genau diese Order heute durchgelassen, der Nutzer hat im Chat ein
  ausdrückliches Ja für genau diese eine Order getippt, und der Nutzer hat auf Claudes eigener Karte
  „Allow once“ geklickt, weil das Order-Tool auf „Needs approval“ steht (Customize > Connectors >
  Tool-Berechtigungen). Ein Order-Tool nie auf „Always allow“ stellen.
- Keine Optionen, kein Margin, keine Leerverkäufe und kein Hebel, außer die Config erlaubt es und der Nutzer bestätigt.
- Broker-Schlüssel liegen in Umgebungsvariablen oder der Claude-Desktop-Config, niemals im Chat.
