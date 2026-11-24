# Der Trader-Skill

11 Claude-Skills, die die Investoren kopieren, denen du vertraust, die Nachrichten und den Kongress beobachten, jeden Trade an dein Budget anpassen und nie eine Order ohne dein Ja platzieren.

Kostenlos, MIT-Lizenz, keine Anmeldung, kein API-Schlüssel. Die Tools sind
schlichtes Python und lesen öffentliche Daten: SEC EDGAR, den House Clerk,
Nachrichten-Feeds.

Ein Skill rekonstruiert das Portfolio des Investors, den du kopieren willst,
direkt aus seiner 13F-Meldung. Ein anderer überwacht Eilmeldungen zu jeder
Aktie, die du hältst. Einer verwaltet dein Budget: jeder Dollar eingeteilt,
ein Cash-Puffer bleibt stehen, keine Aktie über deiner Obergrenze. Und der
verrückteste ist der Pelosi-Skill: Er liest die Aktiengeschäfte, die
Kongressmitglieder offenlegen, in der Minute, in der die Meldung erscheint.

Und kein Trade geht durch, bevor du Ja sagst. Nichts in diesem Paket kann von
sich aus eine Order platzieren. Paper Trading (Handel mit Spielgeld) ist der
Standard.

## Installation

Füge das in Claude ein:

```
https://github.com/Jakeschincariol/trader-skill

install skill
```

Oder als Plugin in Claude Code:

```
/plugin marketplace add Jakeschincariol/trader-skill
/plugin install trader-skill@trader-skill
```

Claude Code stellt Plugin-Skills einen Namensraum voran, als Plugin
installiert heißen sie also `/trader-skill:trader-copycat` und so weiter.
Kopiere stattdessen die Ordner, wenn du schlicht `/trader-copycat` willst:

```bash
git clone https://github.com/Jakeschincariol/trader-skill.git
cp -r trader-skill/trader-* ~/.claude/skills/
```

Nur für ein Projekt statt global: Kopiere dieselben Ordner in das Verzeichnis
`.claude/skills/` deines Repos. Gar kein Claude Code? Füge eine einzelne
`SKILL.md` am Anfang eines Chats ein, dann läuft sie als Modus. Die
Python-Tools fehlen dann, aber die Methode funktioniert.

Die Tools brauchen Python 3.8 oder neuer. Nichts per pip zu installieren. Die
SEC verlangt, dass sich jedes Skript ausweist: Trage deinen Namen und deine
E-Mail in `trader/config.json` ein (`"sec_user_agent": "Dein Name du@example.com"`)
oder in die Umgebungsvariable `SEC_USER_AGENT`.

Die Python-Tools geben ihre Ergebnisse auf Englisch aus. Die Skills weisen
Claude an, dir alles auf Deutsch zu erklären.

## Die elf

| Befehl | Aufgabe | was er tut |
| --- | --- | --- |
| `/trader-copycat` | Reverse Engineer | Liest die 13F-HR eines Investors bei SEC EDGAR und baut sein Portfolio als Gewichtungen nach, die du kopieren kannst, samt allem, was seit dem letzten Quartal gekauft, aufgestockt, reduziert und verkauft wurde. |
| `/trader-news` | Nachrichten-Monitor | Beobachtet Schlagzeilen und SEC-Meldungen (8-Ks) zu jeder Aktie, die du hältst, und markiert, was sie betrifft. |
| `/trader-budget` | Budget-Manager | Teilt jede Position nach deinem Budget ein, hält einen Cash-Puffer und begrenzt jede einzelne Aktie. |
| `/trader-pelosi` | Pelosi-Tracker | Liest die Offenlegungen von Aktiengeschäften des Kongresses (House PTRs), sobald sie erscheinen, macht aus jedem PDF saubere Zeilen und meldet sich einmal pro neuer Meldung. |
| `/trader-analyst` | Quartalszahlen-Analyst | Holt die gemeldeten Zahlen jedes Unternehmens aus SEC XBRL (Umsatz, Nettogewinn, verwässertes EPS, Margen, Wachstum) und seine neueste Ergebnismitteilung. |
| `/trader-screener` | Aktien-Screener | Prüft Unternehmen gegen deine eigenen Regeln und ordnet, was besteht, in eine Rangliste. |
| `/trader-risk` | Risiko-Manager | Prüft jede vorgeschlagene Order gegen deine Limits und blockiert alles, was darüber liegt. |
| `/trader-broker` | Order-Ausführung | Macht aus einer freigegebenen Order genau das Ticket, das dein Broker-Connector erhält, und protokolliert dein Ja. Er platziert selbst nie etwas. |
| `/trader-tax` | Steuer-Optimierer | Verfolgt Kaufposten (Lots) mit Einstandskosten, Gewinne und Verluste, Kandidaten für Tax-Loss-Harvesting und Wash Sales. |
| `/trader-alerts` | Kursalarme | Meldet sich, wenn ein Kursziel, ein Stopp oder die Eröffnungsglocke erreicht ist, mit dem echten NYSE-Kalender. |
| `/trader-rebalance` | Rebalancer | Bringt das Portfolio auf seine Zielgewichte zurück, wenn es über deine Bandbreite hinaus abweicht. |

## So benutzt du es

Alles landet in einem Ordner `trader/` in deinem Projekt, und jeder Skill liest,
was der vorige geschrieben hat:

```
copycat -> budget -> risk -> broker            (einen Investor kopieren)
news / pelosi / alerts                          (beobachten, nach Zeitplan)
analyst -> screener -> budget -> risk -> broker (selbst auswählen)
rebalance / tax -> risk -> broker               (pflegen)
```

Ein Beispiel: Berkshire Hathaway mit 5.000 $ kopieren.

1. **`/trader-copycat`** „kopiere Berkshires Top 5“. Er findet Berkshire
   Hathaway (CIK 1067983), lädt die neueste 13F-HR herunter (Q2 2026,
   eingereicht am 14.08.2026) und liest jede Zeile: Apple 22,04 % des
   gemeldeten Portfolios, American Express 17,14 %, Alphabet 12,62 % (beide
   Aktiengattungen), Coca-Cola 10,86 %, Bank of America 9,20 %. Seit dem
   letzten Quartal: D.R. Horton neu, Constellation Brands komplett verkauft.
   Er schreibt `trader/targets.json` mit den auf 100 % hochgerechneten Top 5:
   30,67 / 23,85 / 17,56 / 15,11 / 12,80 %.
2. **`/trader-budget`** mit 5.000 $ Budget, 10 % Cash-Puffer und 25 %
   Obergrenze: Apple 1.250 $ (gedeckelt), American Express 1.119 $, Alphabet
   823 $, Coca-Cola 708 $, Bank of America 600 $, 500 $ Cash, 0 $ ungenutzt.
   Er schreibt `trader/orders.json` als Vorschläge.
3. **`/trader-risk`** prüft alle fünf gegen deine Limits: gesperrte Ticker,
   Ordergröße, Positionsgröße nach der Ausführung, den Cash-Puffer, keine
   Optionen und kein Margin. PASS oder BLOCK, mit Begründung.
4. **`/trader-broker`** zeigt dir jedes Ticket: „Kaufe AAPL für 1.250 $,
   Market-Order, gültig heute“. Du tippst ja für genau diese Order. Claude
   ruft deinen Broker-Connector auf (Alpacas MCP-Server, standardmäßig
   Paper-Konto), und Claudes eigene Karte „Einmal erlauben / Ablehnen“ fragt
   dich noch einmal.
5. Nach Zeitplan: **`/trader-news`** markiert Schlagzeilen zu deinen Aktien,
   **`/trader-pelosi`** meldet sich, wenn eine neue Offenlegung erscheint, und
   **`/trader-alerts`** schlägt bei deinen Kursmarken an.
6. Jedes Quartal: **`/trader-copycat`** vergleicht die neue 13F mit der
   letzten, und **`/trader-rebalance`** schlägt die Trades vor, um wieder
   gleichzuziehen.

## Die Tools

Alles Python mit der Standardbibliothek. Die Daten-Tools lesen öffentliche
Endpunkte und sind dabei höflich (die Regel der SEC: dich ausweisen, höchstens
10 Anfragen pro Sekunde).

```bash
python3 trader-copycat/edgar13f.py find buffett                        # CIK eines Melders
python3 trader-copycat/edgar13f.py filings 1067983                     # seine 13F-HR-Meldungen
python3 trader-copycat/edgar13f.py --help                              # holdings, diff, copy
python3 trader-news/news.py --tickers AAPL AXP GOOGL KO BAC --hours 24 # Schlagzeilen + 8-Ks
python3 trader-pelosi/ptr.py index --member pelosi                     # ihre PTRs dieses Jahr
python3 trader-pelosi/ptr.py --help                                    # new, fetch, parse
python3 trader-analyst/facts.py AAPL                                   # Quartale, Wachstum, EPS
python3 trader-screener/screen.py trader/metrics.json --rules trader/rules.json
python3 trader-budget/size.py --budget 5000 --write                    # -> trader/orders.json
python3 trader-risk/check.py                                           # PASS / BLOCK je Order
python3 trader-broker/ticket.py show                                   # die Tickets, READY oder nicht
python3 trader-tax/lots.py harvest --min-loss 100                      # mit Wash-Sale-Prüfung
python3 trader-alerts/alerts.py clock                                  # NYSE offen oder geschlossen
python3 trader-rebalance/rebalance.py --band 5                         # die Abweichungstabelle
```

```bash
python3 -m unittest discover -s tests -v
```

Die Tests laufen offline auf kleinen Ausschnitten echter Meldungen: Berkshires
Informationstabellen für Q1 und Q2 2026, der Index 2026 des House Clerk, echter
PTR-Text, echte XBRL-Fakten und Feeds.

## Kleingedrucktes

**Keine Anlageberatung.** Das ist Software, die öffentliche Daten liest und
rechnet. Sie kennt deine Situation nicht, sie kann nicht in die Zukunft sehen,
und wer einen Investor kopiert, kopiert nicht seine Ergebnisse. Du kannst Geld
verlieren. Entscheide selbst und sprich mit einer zugelassenen Fachperson, wenn
du Beratung brauchst.

**Kein Trade geht durch, bevor du Ja sagst.** Nur `/trader-broker` kann zu einer
Order führen, und nur nachdem `/trader-risk` genau diese Order durchgelassen hat
und du im Chat ja dafür getippt hast. Stelle dein Broker-Tool in Claude auf
„Needs approval“ (Customize, Connectors, Tool-Berechtigungen), niemals auf
„Always allow“, damit Claudes eigene Karte „Einmal erlauben / Ablehnen“ eine
zweite Kontrolle ist. Keine Optionen, kein Margin, keine Leerverkäufe und kein
Hebel, außer du schaltest sie ein.

**Erst mit Spielgeld.** `"paper": true` ist der Standard in
`config.example.json`, und Alpacas MCP-Server nutzt standardmäßig sein
Paper-Konto. Schlüssel liegen in Umgebungsvariablen, niemals im Chat.

**13F-Daten sind alt und unvollständig.** Fonds melden 45 Tage nach jedem
Quartalsende, und eine 13F listet Long-Positionen in US-börsennotierten Aktien
und einigen verwandten Wertpapieren: keine Leerverkäufe, kein Cash, keine im
Ausland notierten Aktien. Du siehst, was sie gehalten haben, nicht was sie heute halten.

**Die Trades des Kongresses sind öffentlich, keine Insiderinformationen.**
Mitglieder müssen Geschäfte über 1.000 $ innerhalb von 45 Tagen offenlegen (der
STOCK Act). Der Pelosi-Skill liest diese öffentlichen Meldungen in der Minute,
in der sie erscheinen, mit den Beträgen als die Spannen, in denen sie gemeldet
werden. Er hat keinen Zugang zu irgendetwas, das nicht öffentlich ist.

**Die Daten stammen aus kostenlosen öffentlichen Quellen.** SEC EDGAR, der
House Clerk, Nachrichten-RSS und der Chart-Endpunkt von Yahoo Finance
(inoffiziell, er kann sich ändern). Prüfe alles Wichtige bei deinem Broker
nach, bevor du danach handelst.

**Steuern.** `/trader-tax` rechnet mit Kaufposten und Wash-Sale-Fristen nach
US-Bundesrecht. Das ist keine Steuerberatung, und deutsches Steuerrecht bildet
es nicht ab.

## Dateien

```
trader-copycat/    SKILL.md, edgar13f.py, filers.json, share_classes.json, targets.example.json
trader-news/       SKILL.md, news.py
trader-budget/     SKILL.md, size.py, config.example.json, targets.example.json
trader-pelosi/     SKILL.md, ptr.py
trader-analyst/    SKILL.md, facts.py, metrics.example.json
trader-screener/   SKILL.md, screen.py, rules.example.json
trader-risk/       SKILL.md, check.py
trader-broker/     SKILL.md, ticket.py, claude_desktop_config.example.json
trader-tax/        SKILL.md, lots.py, portfolio.example.json
trader-alerts/     SKILL.md, alerts.py, alerts.example.json
trader-rebalance/  SKILL.md, rebalance.py
tests/             unittest-Suite + Offline-Fixtures
```

MIT. Erstellt von [Jake Schincariol](https://opusjake.ai).
