---
name: trader-rebalance
description: >-
  Rebalancer. Bringt das Portfolio auf seine Zielgewichte zurück, wenn es
  abweicht: bewertet jeden Bestand zu aktuellen Kursen, berechnet die
  Abweichung jeder Aktie von ihrem Ziel in Prozentpunkten, handelt nur die
  Aktien außerhalb einer Bandbreite (Standard 5 Punkte), hält den Cash-Puffer
  und die Obergrenze pro Aktie, überspringt winzige Trades, listet Verkäufe
  vor Käufen und schreibt die Trades als Vorschläge in trader/orders.json.
  Verwenden, wenn der Nutzer sagt „rebalancen“, „mein Portfolio ist
  verrutscht“, „bring es zurück auf die Ziele“, „ich habe Geld nachgelegt“,
  „die neue 13F hat die Gewichte geändert“, „bin ich übergewichtet“, oder nach
  Zeitplan (monatlich oder vierteljährlich), nachdem /trader-copycat die Ziele
  aktualisiert hat.
argument-hint: "[Bandbreite in Punkten]"
---

# trader-rebalance

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle und Dateinamen
unverändert.

Der Rebalancer sorgt dafür, dass das Portfolio dem Plan entspricht. Kurse
bewegen sich, neues Geld kommt hinzu, und eine neue 13F ändert die Gewichte;
dieser Skill findet die Aktien, die zu weit abgewichen sind, und schlägt die
Trades vor, die sie zurückbringen. Er schreibt nur Vorschläge: trader-risk
prüft sie, und trader-broker fragt den Nutzer für jede einzelne nach ja oder
nein.

`${CLAUDE_SKILL_DIR}` unten ist der Ordner dieses Skills (wo diese SKILL.md liegt).

```bash
python3 "${CLAUDE_SKILL_DIR}/rebalance.py"                    # die Abweichungstabelle, schreibt keine Dateien
python3 "${CLAUDE_SKILL_DIR}/rebalance.py" --band 5 --write   # Vorschläge -> trader/orders.json
python3 "${CLAUDE_SKILL_DIR}/rebalance.py" --sell-untracked   # auch Bestände verkaufen, die nicht in den Zielen sind
python3 "${CLAUDE_SKILL_DIR}/rebalance.py" --json
```

## Was er liest und schreibt

| Datei | Inhalt |
| --- | --- |
| `trader/portfolio.json` | Cash und Positionen (Stückzahlen); gleiche Form wie `portfolio.example.json` von trader-tax |
| `trader/prices.json` | ein Kurs für jeden Bestand und jedes Ziel (trader-alerts schreibt sie) |
| `trader/targets.json` | die Zielgewichte (trader-copycat schreibt sie) |
| `trader/config.json` | Cash-Puffer, Obergrenze, Mindest- und Höchstorder, `rebalance_band_pct` |
| `trader/orders.json` | die Vorschläge, die er mit `--write` schreibt, Verkäufe zuerst |

## Wie er entscheidet

- **Kontowert** = Cash + jeder Bestand zu seinem Kurs.
- **Ziele**: die Gewichte, hochgerechnet auf den Aktienanteil (Konto minus
  Cash-Puffer), keine Aktie über `max_position_pct` des Kontos. Der Überschuss
  wird verteilt, genau wie bei trader-budget, damit eine gedeckelte Aktie
  nicht jeden Monat über die Obergrenze zurückgekauft wird.
- **Abweichung** = aktueller Prozentanteil am Konto minus Zielanteil.
- **Bandbreite**: Nur Aktien, die MEHR als die Bandbreite abweichen, werden
  gehandelt (Standard 5 Punkte). Ein Trade bringt die Aktie ganz auf ihr Ziel
  zurück. Eine kleine Bandbreite heißt mehr Trades, eine große weniger.
- **Verkäufe zuerst**, dann Käufe. Käufe verwenden nur Cash über dem Puffer;
  reicht es nicht, werden alle Käufe im gleichen Verhältnis verkleinert.
- Trades unter `min_order_usd` werden übersprungen. Ein Trade über
  `max_order_usd` wird auf das Maximum gekürzt, mit dem Hinweis, nach der
  Ausführung erneut zu laufen.
- **Nicht verfolgte** Bestände (nicht in den Zielen) bleiben unberührt und
  werden aufgelistet, außer der Nutzer will sie mit `--sell-untracked`
  verkaufen.

## Schritte

1. Kurse aktualisieren: trader-alerts `alerts.py quote --holdings --write`.
2. `rebalance.py` ausführen und die Abweichungstabelle in einfachen Worten
   zeigen: welche Aktien über oder unter dem Ziel liegen, um wie viele Punkte,
   und was er handeln würde.
3. Vor jedem Verkauf trader-tax ausführen (`lots.py sell TICKER SHARES`) und
   zeigen, was der Verkauf realisieren würde. Einen Gewinner zu verkaufen kann
   Steuern auslösen.
4. Will der Nutzer die Trades: `rebalance.py --write`, dann `/trader-risk`,
   dann `/trader-broker`, ein Ja pro Order.

## Beispiel: das Portfolio aus dem Beispiellauf

Das am 13.10.2026 gekaufte Kopie-Portfolio (AAPL 1.250 $ gedeckelt, AXP
1.119 $, GOOGL 823 $, KO 708 $, BAC 600 $, 500 $ Cash), bewertet zu den
Schlusskursen dieses Tages, liegt auf seinen Zielen: Jede Abweichung ist unter
0,1 Punkten, also sagt `rebalance.py` „Nothing is outside the band“ (nichts
liegt außerhalb der Bandbreite) und endet mit Exit-Code 1. Legt der Nutzer
2.000 $ Cash nach, ist das Konto 7.000 $ wert und die Obergrenze steigt auf
1.750 $. AAPL liegt jetzt 7,1 Punkte unter seinem Ziel und AXP 6,4, beide
außerhalb der Bandbreite von 5 Punkten, also schlägt er vor, AAPL für 499 $
und AXP für 446 $ zu kaufen. GOOGL, KO und BAC liegen auch unter dem Ziel,
aber innerhalb der Bandbreite, also warten sie. Legt er stattdessen 5.000 $
nach, liegen alle fünf außerhalb: fünf Käufe, die den Puffer von 1.000 $ in
Cash lassen.

## Was er nie tut

Er platziert nie eine Order, handelt nie innerhalb der Bandbreite, um kleinen
Unterschieden hinterherzulaufen, verkauft nie Bestände außerhalb der Ziele,
außer auf Wunsch, und sagt nie, ein Rebalancing werde die Rendite verbessern.

## Sicherheit

- Bildung und Werkzeuge, keine Anlageberatung. Ein Rebalancing folgt den eigenen Zielen des Nutzers, keiner Prognose.
- Standardmäßig Paper Trading (`"paper": true`). Live zu gehen ist allein die Entscheidung des Nutzers, in seiner eigenen Config.
- Nichts in diesem Paket platziert eine Order außer trader-broker, und nur wenn alle drei Bedingungen
  erfüllt sind: trader-risk hat genau diese Order heute durchgelassen, der Nutzer hat im Chat ein
  ausdrückliches Ja für genau diese eine Order getippt, und der Nutzer hat auf Claudes eigener Karte
  „Allow once“ geklickt, weil das Order-Tool auf „Needs approval“ steht (Customize > Connectors >
  Tool-Berechtigungen). Ein Order-Tool nie auf „Always allow“ stellen.
- Keine Optionen, kein Margin, keine Leerverkäufe und kein Hebel, außer die Config erlaubt es und der Nutzer bestätigt.
- Broker-Schlüssel liegen in Umgebungsvariablen oder der Claude-Desktop-Config, niemals im Chat.
