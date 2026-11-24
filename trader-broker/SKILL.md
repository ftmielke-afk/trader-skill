---
name: trader-broker
description: >-
  Order-Ausführung. Platziert FREIGEGEBENE Orders über den Broker-Connector des
  Nutzers, eine nach der anderen, und nie ohne sein ausdrückliches Ja. Zeigt
  jede Order als einfaches Ticket plus das exakte JSON für Alpacas
  place_stock_order, protokolliert das Ja wortwörtlich, danach fragt Claudes
  eigene Karte „Allow once / Deny“ noch einmal. Deckt die Einrichtung von
  Alpacas offiziellem MCP-Server in Claude Desktop ab (standardmäßig Paper
  Trading, Schlüssel in Umgebungsvariablen, nie im Chat), den Connector von
  Interactive Brokers (Orders gehen zur Freigabe an das IBKR-Konto) und das
  Umstellen von Order-Tools auf „Needs approval“. Verwenden, wenn der Nutzer
  sagt „platziere die Orders“, „kauf es“, „ausführen“, „schick es an meinen
  Broker“, „verbinde Alpaca“, „verbinde Interactive Brokers“, „richte Paper
  Trading ein“, oder nachdem /trader-risk bestanden hat.
argument-hint: "[Ordernummer]"
---

# trader-broker

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle, Dateinamen und das
Order-JSON unverändert.

Die Order-Ausführung ist der einzige Skill in diesem Paket, der zu einer echten
Order führen kann, deshalb ist sie der strengste. Eine Order erreicht den Markt
erst nach drei getrennten Schranken, jedes Mal, für jede Order:

1. **trader-risk hat genau diese Order heute durchgelassen** (per Fingerabdruck zugeordnet).
2. **Der Nutzer hat im Chat ein ausdrückliches Ja für genau diese eine Order getippt.**
3. **Der Nutzer hat auf Claudes eigener Berechtigungskarte „Allow once“ geklickt**,
   die erscheint, weil das Order-Tool auf „Needs approval“ steht.

Zweimal Ja vom Nutzer, einmal PASS von den Regeln. Kein Ja, keine Order.

`${CLAUDE_SKILL_DIR}` unten ist der Ordner dieses Skills (wo diese SKILL.md liegt).

```bash
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show                     # jedes Ticket, READY oder nicht
python3 "${CLAUDE_SKILL_DIR}/ticket.py" approve --index 1 --reply "ja"
python3 "${CLAUDE_SKILL_DIR}/ticket.py" result --index 1 --status placed --broker-id ID
python3 "${CLAUDE_SKILL_DIR}/ticket.py" fill --symbol AAPL --side buy --qty 3.6628 --price 341.27
python3 "${CLAUDE_SKILL_DIR}/ticket.py" log
```

`ticket.py` spricht nie mit einem Broker. Es stellt Tickets dar, prüft, ob
eine Antwort ein echtes Ja für diese Order ist, und führt das Protokoll in
`trader/state/broker.json`. Als Ja zählen Antworten, die mit „ja“ oder „yes“
beginnen.

## Einrichtung A: Alpaca (offizieller MCP-Server, Claude Desktop)

Alpacas eigener Server ist github.com/alpacahq/alpaca-mcp-server (MIT). Er
läuft auf dem Computer des Nutzers in Claude Desktop. Er ist nicht im
Connector-Verzeichnis von Claude. Er handelt auf einem **Paper**-Konto, sofern
nicht anders angegeben.

1. Der Nutzer legt ein Alpaca-Konto an und erstellt im Alpaca-Dashboard
   API-Schlüssel für **Paper Trading**. Paper-Schlüssel sind getrennt von
   Live-Schlüsseln.
2. Der Nutzer installiert `uv` (es liefert `uvx`), von docs.astral.sh/uv.
3. In Claude Desktop: Settings > Developer > Edit Config. Das öffnet
   `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`,
   Windows: `%APPDATA%\Claude\`). Der Nutzer fügt diesen Block ein (auch in
   `claude_desktop_config.example.json` hier) und tippt seine eigenen Schlüssel
   in die Datei:

```json
{
  "mcpServers": {
    "alpaca": {
      "command": "uvx",
      "args": ["alpaca-mcp-server"],
      "env": {
        "ALPACA_API_KEY": "paste your paper key here, in this file only",
        "ALPACA_SECRET_KEY": "paste your paper secret here, in this file only",
        "ALPACA_PAPER_TRADE": "true",
        "ALPACA_TOOLSETS": "account,trading,stock-data"
      }
    }
  }
}
```

   Der `env`-Block übergibt die Schlüssel als Umgebungsvariablen an den Server.
   **Schlüssel kommen nie in den Chat.** Frag nie danach, lies diese Datei nie
   in das Gespräch zurück, und wenn der Nutzer trotzdem einen Schlüssel
   einfügt, sag ihm, er soll diese Nachricht löschen und im Alpaca-Dashboard
   neue Schlüssel erstellen. `ALPACA_PAPER_TRADE` ist standardmäßig schon true;
   es hinzuschreiben macht es sichtbar. `ALPACA_TOOLSETS` ist optional und
   blendet Tools aus, die nicht gebraucht werden.
4. Claude Desktop neu starten.
5. **Die Tool-Berechtigungen setzen.** Customize > Connectors (in älteren
   Versionen Settings > Connectors), alpaca öffnen und für jedes Tool Always
   allow, Needs approval oder Blocked wählen:
   - `place_stock_order`: **Needs approval**. Nie Always allow.
   - jedes andere Tool, das etwas platziert, ändert, storniert oder schließt
     (`cancel_order_by_id`, `close_position`, `update_account_config`): Needs approval.
   - `place_option_order`, `place_crypto_order`, `close_all_positions`,
     `cancel_all_orders`, `exercise_options_position`: **Blocked**, außer der
     Nutzer hat einen Grund und sagt das.
   - reine Lese-Tools (`get_account_info`, `get_all_positions`, `get_stock_snapshot`,
     `get_stock_latest_quote`): Always allow ist in Ordnung.
6. Prüfen: Claude nach den Alpaca-Kontoinfos fragen (nur lesend) und im
   Alpaca-Dashboard bestätigen, dass es das Paper-Konto ist.

In Claude Code statt Claude Desktop das Order-Tool in `.claude/settings.json`
auf Nachfragen lassen: `"permissions": {"ask": ["mcp__alpaca__place_stock_order"]}`,
und nie ein Order-Tool unter `allow` eintragen.

## Einrichtung B: Interactive Brokers (Connector im Verzeichnis von Claude)

Interactive Brokers veröffentlicht einen verifizierten Connector:
claude.ai/directory/interactive-brokers (Connector-URL
`https://api.ibkr.com/v1/api/mcp`). Hinzufügen über Customize > Connectors >
Browse connectors und dort bei IBKR anmelden, nicht im Chat. Laut seinem
Eintrag kann Claude Handelsanweisungen entwerfen, die zur Prüfung und Freigabe
an das IBKR-Konto des Nutzers gesendet werden, und Claude übermittelt nie
direkt Orders an den Markt. Bei IBKR passiert das letzte Ja also auch in IBKR.
`"broker": "ibkr"` in `trader/config.json` setzen und mit `--whole-shares`
einteilen, wenn IBKR Stückzahlen will. Auch seine Tools, die Orders entwerfen,
auf Needs approval stellen.

## Schritte, für jede Order

1. `ticket.py show`. Nur READY-Tickets gehen an den Nutzer. Ein Ticket, das
   NOT READY oder BLOCKED ist, geht zurück an `/trader-risk`.
2. Zeig EIN Ticket und frag: „Diese Order platzieren? Antworte mit ja oder
   nein.“ Eine Order pro Frage. Biete nie „ja zu allen“ an.
3. Führ `ticket.py approve --index N --reply "<die Antwort des Nutzers, wortwörtlich>"` aus.
   Gibt es „Not recorded“ aus, war die Antwort kein ausdrückliches Ja für
   diese Order (zum Beispiel „klar“, „ja zu allen“ oder ein Ja, das eine
   andere Aktie oder einen anderen Betrag nennt). Frag erneut. Mach nie selbst
   aus einer Antwort ein Ja.
4. Erst nach „Recorded your yes“ `place_stock_order` mit genau dem JSON
   aufrufen, das das Ticket ausgegeben hat. Claudes Karte erscheint: Allow once
   oder Deny.
5. Festhalten, was passiert ist: `ticket.py result --index N --status placed
   --broker-id <ID aus der Antwort>`, oder `--status denied`, wenn Deny
   gedrückt wurde, oder `--status failed` mit `--note` bei einem Fehler. Eine
   fehlgeschlagene Order wird nicht ohne neue Prüfung und neues Ja wiederholt.
6. Ist die Ausführung bekannt (die Antwort des Tools oder später aus
   `get_all_positions`), trägt `ticket.py fill` sie als Steuer-Lot für
   trader-tax in `trader/portfolio.json` ein. Dann das nächste Ticket.

## Beispiel: der Beispiellauf

```
ORDER 1 of 5, PAPER account, Alpaca
  BUY $1,250 of AAPL, market order, good for today
  READY: trader-risk PASS, waiting for your yes
  Claude will call place_stock_order with exactly:
    {"symbol": "AAPL", "side": "buy", "notional": "1250",
     "type": "market", "time_in_force": "day"}
```

Auf Deutsch: Order 1 von 5, Paper-Konto bei Alpaca, kaufe AAPL für 1.250 $,
Market-Order, gültig heute, bereit, wartet auf dein Ja. Der Nutzer antwortet
„ja“. Claude protokolliert es, ruft `place_stock_order` auf, und die Karte
zeigt „Claude wants to use Place stock order“ mit diesem JSON und zwei
Knöpfen: Allow once, Deny. Allow once schickt sie an das Paper-Konto.

## Was er nie tut

- Platziert nie eine Order ohne alle drei Schranken und nie zwei Orders auf ein Ja.
- Platziert nie Orders aus einer geplanten oder Hintergrund-Aufgabe: Da ist niemand, der Ja sagt.
- Fragt nie nach API-Schlüsseln oder Passwörtern, liest, speichert oder wiederholt sie nie.
- Stellt `ALPACA_PAPER_TRADE` oder `"paper"` nie auf live um. Das macht der Nutzer selbst.
- Ruft nie von sich aus `close_all_positions`, `cancel_all_orders`, Options- oder Krypto-Order-Tools auf.

## Sicherheit

- Bildung und Werkzeuge, keine Anlageberatung. Keine Order hier ist eine Empfehlung, und nichts verspricht Renditen.
- Standardmäßig Paper Trading (`"paper": true`, `ALPACA_PAPER_TRADE` true). Live zu gehen ist allein die Entscheidung des Nutzers.
- Nichts in diesem Paket platziert eine Order außer trader-broker, und nur wenn alle drei Bedingungen
  erfüllt sind: trader-risk hat genau diese Order heute durchgelassen, der Nutzer hat im Chat ein
  ausdrückliches Ja für genau diese eine Order getippt, und der Nutzer hat auf Claudes eigener Karte
  „Allow once“ geklickt, weil das Order-Tool auf „Needs approval“ steht (Customize > Connectors >
  Tool-Berechtigungen). Ein Order-Tool nie auf „Always allow“ stellen.
- Keine Optionen, kein Margin, keine Leerverkäufe und kein Hebel, außer die Config erlaubt es und der Nutzer bestätigt.
- Broker-Schlüssel liegen in Umgebungsvariablen oder der Claude-Desktop-Config, niemals im Chat.
