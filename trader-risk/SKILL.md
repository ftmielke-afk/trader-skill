---
name: trader-risk
description: >-
  Risiko-Manager. Prüft jede vorgeschlagene Order gegen die Limits des
  Nutzers, bevor sie den Broker erreichen kann, und blockiert alles, was
  darüber liegt: gesperrte Ticker, maximale Ordergröße, Mindestorder, maximaler
  Positionsanteil nach der Ausführung, der Cash-Puffer, Margin, Leerverkäufe,
  Optionen und Krypto (aus, außer erlaubt), fehlerhafte Orders, Duplikate und
  ein Tageslimit für Orders. Gibt für jede Order PASS oder BLOCK mit Begründung
  aus und speichert die Urteile, damit trader-broker nur eine Order zeigt, die
  bestanden hat. Verwenden, wenn der Nutzer sagt „prüf meine Orders“, „ist das
  sicher“, „Risikoprüfung“, „verstößt das gegen meine Regeln“, „kann ich das
  platzieren“, und immer vor /trader-broker.
argument-hint: "[Pfad zu orders.json]"
---

# trader-risk

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle, Dateinamen und die
Urteile PASS und BLOCK unverändert.

Der Risiko-Manager ist die Schranke zwischen einem Vorschlag und dem Broker.
Jede Order, die trader-budget, trader-rebalance oder trader-tax schreibt, muss
durch ihn hindurch. Ein BLOCK ist für diese Order endgültig: Sie geht nicht
zum Nutzer für ein Ja und nicht zum Broker.

`${CLAUDE_SKILL_DIR}` unten ist der Ordner dieses Skills (wo diese SKILL.md liegt).

```bash
python3 "${CLAUDE_SKILL_DIR}/check.py"             # trader/-Dateien; schreibt trader/state/risk.json
python3 "${CLAUDE_SKILL_DIR}/check.py" --json
python3 "${CLAUDE_SKILL_DIR}/check.py" --no-write  # ansehen, ohne zu speichern
```

## Was er liest und schreibt

| Datei | Inhalt |
| --- | --- |
| `trader/orders.json` | die vorgeschlagenen Orders |
| `trader/config.json` | die Limits (trader-budget liefert `config.example.json` mit) |
| `trader/portfolio.json` | Cash und Bestände; fehlt sie, gilt ein frisches Konto mit dem Budget als Guthaben |
| `trader/prices.json` | nötig, um Orders nach Stückzahl einzuschätzen und Bestände zu bewerten |
| `trader/state/broker.json` | was heute platziert wurde, für Duplikate und das Tageslimit |
| `trader/state/risk.json` | die Urteile, die er schreibt, mit einem Fingerabdruck jeder exakten Order |

## Die Prüfungen

Orders werden in der Reihenfolge der Datei geprüft, als wäre jede bestandene
Order schon ausgeführt. So wird ein Paket erwischt, das Order für Order in
Ordnung ist, zusammen aber eine Regel verletzt.

| Prüfung | blockiert, wenn |
| --- | --- |
| format | kein Symbol, side weder buy noch sell, qty und notional beide oder keines, eine notional-Order, die nicht market + day ist (Alpacas Regel), eine Limit-Order ohne Limitpreis |
| asset | ein Optionssymbol, während `allow_options` false ist; Krypto oder alles, was kein Ticker einer US-Aktie oder eines ETF ist |
| blocked | der Ticker steht auf der Liste `blocked` |
| size | unter `min_order_usd` oder über `max_order_usd` |
| position | die Aktie läge nach der Ausführung über `max_position_pct` des Kontos |
| cash | der Kauf ließe weniger als den Cash-Puffer übrig oder bräuchte Margin (`allow_margin` false) |
| short | ein Verkauf von mehr, als man hält (`allow_short` false) |
| duplicate | dasselbe Symbol und dieselbe Richtung zweimal in einem Paket, oder heute schon platziert |
| daily limit | mehr als `max_orders_per_day` heute platziert |

Warnungen blockieren nicht, aber sag sie dem Nutzer: ein LIVE-Konto, eine
Zahl, die als Zahl statt als String gesendet wird, eine erweiterte
(Bracket-)Order.

## Schritte

1. Sorg dafür, dass `trader/prices.json` aktuell ist, wenn eine Order eine
   Stückzahl ist oder ein Bestand bewertet werden muss (trader-alerts:
   `alerts.py quote --holdings --write`).
2. Führ `check.py` aus. Exit-Code 0 heißt: jede Order hat bestanden, 1 heißt:
   mindestens eine wurde blockiert.
3. Sag dem Nutzer das Ergebnis in einfachen Worten, Order für Order. Bei einem
   BLOCK nenn den Grund und die Abhilfe (ein kleinerer Betrag, eine andere
   Aktie oder eine Regel, die der Nutzer ändern könnte). Ändere nie selbst ein
   Limit.
4. Ändern sich die Orders in irgendeiner Weise, prüfe erneut. trader-broker
   ordnet jede Order per Fingerabdruck ihrem Urteil zu, eine bearbeitete Order
   ist also erst bereit, wenn sie erneut besteht, und ein Urteil von gestern
   zählt heute nicht.

## Beispiel: der Beispiellauf

Die fünf Käufe von trader-budget (AAPL 1.250 $, AXP 1.119 $, GOOGL 823 $, KO
708 $, BAC 600 $) auf einem frischen Paper-Konto mit 5.000 $ und der
Beispiel-Config:

```
PASS  #1 buy AAPL $1,250
PASS  #2 buy AXP $1,119
PASS  #3 buy GOOGL $823
PASS  #4 buy KO $708
PASS  #5 buy BAC $600
5 passed, 0 blocked. Cash after the passed orders: $500 (paper account).
```

Auf Deutsch: alle fünf bestanden, keine blockiert, danach 500 $ Cash auf dem
Paper-Konto. AAPL landet genau auf der Obergrenze von 25 % (1.250 $ von
5.000 $), was erlaubt ist. Eine sechste Order, weitere 100 $ AAPL, wird aus
drei Gründen blockiert: Sie würde den Cash-Puffer von 500 $ angreifen, AAPL
über seine 25 % bringen und AAPL im selben Paket wiederholen.

## Was er nie tut

Er platziert nie eine Order, bearbeitet nie eine Order, damit sie besteht,
lockert nie ein Limit und behandelt ein PASS nie als das Ja des Nutzers. Ein
PASS heißt nur, dass die Order dem Nutzer gezeigt werden darf.

## Sicherheit

- Bildung und Werkzeuge, keine Anlageberatung. Ein PASS ist eine Regelprüfung, keine Empfehlung.
- Standardmäßig Paper Trading (`"paper": true`). Live zu gehen ist allein die Entscheidung des Nutzers, in seiner eigenen Config.
- Nichts in diesem Paket platziert eine Order außer trader-broker, und nur wenn alle drei Bedingungen
  erfüllt sind: trader-risk hat genau diese Order heute durchgelassen, der Nutzer hat im Chat ein
  ausdrückliches Ja für genau diese eine Order getippt, und der Nutzer hat auf Claudes eigener Karte
  „Allow once“ geklickt, weil das Order-Tool auf „Needs approval“ steht (Customize > Connectors >
  Tool-Berechtigungen). Ein Order-Tool nie auf „Always allow“ stellen.
- Keine Optionen, kein Margin, keine Leerverkäufe und kein Hebel, außer die Config erlaubt es und der Nutzer bestätigt.
- Broker-Schlüssel liegen in Umgebungsvariablen oder der Claude-Desktop-Config, niemals im Chat.
