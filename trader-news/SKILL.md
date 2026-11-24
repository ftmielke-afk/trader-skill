---
name: trader-news
description: >-
  Der Nachrichten-Monitor. Beobachtet Eilmeldungen vom Markt und SEC-Meldungen
  zu den Aktien, die der Nutzer hält (oder gleich kopieren will): Schlagzeilen
  von Yahoo Finance pro Ticker und die 8-K-Meldungen jedes Unternehmens bei SEC
  EDGAR (Quartalszahlen, CEO-Wechsel, Übernahmen, Bilanzkorrekturen,
  Insolvenz). Zeigt nur, was seit der letzten Prüfung neu ist, das Neueste
  zuerst, markiert, was die Positionen betrifft und warum es zählt, und
  wiederholt nie einen Eintrag. Verwenden, wenn der Nutzer sagt „gibt es News
  zu meinen Aktien“, „was ist los bei Apple“, „überwache die Nachrichten“,
  „beobachte mein Portfolio“, „ist etwas passiert“, „prüf die 8-Ks“ oder
  „Morgenbriefing“ (auch auf Englisch: "any news on my stocks").
argument-hint: "[Ticker]"
---

# trader-news

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle und Dateinamen
unverändert. Zitate aus englischen Quellen übersetzt du und nennst die Quelle.

Eine Position kann sich in einer Minute ändern: verfehlte Quartalszahlen, ein
CEO, der geht, eine Klage, eine Bilanzkorrektur. Dieser Skill liest für jede
Aktie die zwei Feeds, die so etwas zuerst bringen, und meldet nur, was neu ist.

Tool in diesem Ordner (Python mit Standardbibliothek, keine Schlüssel):

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py" --help
```

## Was er liest und schreibt

- Die Ticker: `--tickers`, sonst die Positionen in `trader/portfolio.json`,
  sonst die Gewichte in `trader/targets.json` (so funktioniert er direkt nach
  `/trader-copycat`).
- Schlagzeilen: der öffentliche Schlagzeilen-RSS von Yahoo Finance, ein Feed
  pro Ticker
  (`https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US`).
- Meldungen: der Atom-Feed von SEC EDGAR pro Unternehmen, standardmäßig 8-K
  (`--forms 8-K,10-Q` für mehr). Braucht den SEC-User-Agent aus
  `trader/config.json` (`sec_user_agent`) oder `SEC_USER_AGENT`. Ohne ihn
  werden Meldungen mit einem Hinweis übersprungen, Schlagzeilen laufen weiter.
- Schreibt `trader/state/news.json`: was schon gezeigt wurde (30 Tage
  aufbewahrt) und die CIK je Ticker, damit jeder Eintrag nur einmal erscheint.

## Die Regeln

- **Schlagzeilen sind Hinweise, keine Fakten.** Bevor du dem Nutzer sagst,
  dass etwas passiert ist, öffne den Artikel oder die Meldung und lies sie.
  Nenne die Quelle und verlinke sie. Fasse nie einen Artikel hinter einer
  Bezahlschranke zusammen, den du nicht lesen konntest: Sag, dass er hinter
  einer Bezahlschranke liegt.
- **Meldungen schlagen Schlagzeilen.** Widersprechen sich ein 8-K und eine
  Schlagzeile, gilt das 8-K: Das hat das Unternehmen der SEC mitgeteilt.
- **Sag, was es betrifft.** Jeder Eintrag listet die betroffenen Ticker (der
  Feed, aus dem er kam, plus jeder deiner Ticker oder Firmennamen, der darin
  vorkommt) und Tags (earnings, analyst, legal, deal, capital, people, risk).
  Mit `!` markierte Meldungen enthalten einen wichtigen 8-K-Punkt:
  Quartalsergebnisse (2.02), Wechsel in der Führung (5.02), eine
  Wertminderung (2.06), eine Delisting-Mitteilung (3.01), frühere
  Abschlüsse nicht mehr verlässlich (4.02), Insolvenz (1.03) oder ein
  Cybervorfall (1.05).
- **Keine Prognosen.** Berichte, was veröffentlicht wurde. Sag nie, was die
  Aktie als Nächstes tun wird.

## Schritte

1. Prüfung ausführen:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/news.py"
   python3 "${CLAUDE_SKILL_DIR}/news.py" --tickers AAPL AXP GOOGL KO BAC --hours 24
   ```

   Exit-Code 1 heißt: nichts Neues. `--all` zeigt schon gesehene Einträge,
   `--json` gibt alles maschinenlesbar aus, `--dry-run` lässt den Zustand
   unverändert.
2. Lies die wichtigen Einträge: jede `!`-Meldung, jeden Eintrag mit dem Tag
   earnings, legal oder risk, und alles zu den größten Positionen zuerst.
3. Schreib ein kurzes Briefing: pro Ticker, was passiert ist, Quelle und Link,
   und eine Zeile, warum es für dieses Portfolio zählt (sein Gewicht, aus
   `trader/targets.json` oder `trader/portfolio.json`).
4. Könnte eine Meldung den Plan ändern (eine Bilanzkorrektur nach 8-K 4.02,
   eine Delisting-Mitteilung), sag es und schlag `/trader-analyst` für die
   Zahlen vor oder `/trader-risk`, um offene Orders neu zu prüfen. Handle nie
   allein auf eine Schlagzeile hin.

Für einen Zeitplan: `/loop 30m /trader-news` während der Handelszeiten oder
eine geplante Aufgabe jeden Morgen.

## Beispiel: das Portfolio aus dem Beispiellauf

Der Nutzer hat Berkshires Top 5 kopiert (AAPL, AXP, GOOGL, KO, BAC). Am
Dienstag, 13.10.2026, zeigt die Prüfung zuerst Apple-Schlagzeilen („Apple
Introduces HomeView Smart Home Hub, Other Gadgets“, „Judge orders OpenAI to
turn over hiring records in Apple trade secrets case“, Tag legal), Artikel zur
Coca-Cola-Dividende und von der SEC: Apples 8-K vom 30.07.2026 (Punkt 2.02,
Quartalsergebnisse) und das von Coca-Cola vom 28.07.2026 (2.02). Briefing:
„Apple (deine größte Position, 30,7 %) hat einen Smart-Home-Hub für 299 $
vorgestellt; dazu ein Gerichtsbeschluss im Geschäftsgeheimnis-Verfahren gegen
OpenAI. Diese Woche keine neuen Meldungen deiner fünf Unternehmen.“ Hat ein
Ticker keine Nachrichten, sag das, statt das Briefing aufzublähen.

## Was er nie tut

- Erfindet oder schmückt nie eine Geschichte, ein Zitat oder eine Zahl aus.
- Handelt nie auf Nachrichten hin und sagt dem Nutzer nie, wegen einer
  Schlagzeile zu kaufen oder zu verkaufen.
- Überlastet nie einen Server: eine Anfrage pro Feed und Ticker, eine Pause
  zwischen SEC-Aufrufen, und die Grenze der SEC von 10 Anfragen pro Sekunde
  bleibt weit entfernt.

## Sicherheit

Bildung und Werkzeuge, keine Anlageberatung. Dieser Skill liest und berichtet
nur. Nichts platziert eine Order außer `/trader-broker`, nachdem
`/trader-risk` sie durchgelassen hat und der Nutzer ein ausdrückliches Ja für
genau diese Order getippt hat.
