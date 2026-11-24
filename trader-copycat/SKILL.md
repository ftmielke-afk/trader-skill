---
name: trader-copycat
description: >-
  Der Reverse Engineer. Liest die öffentlichen SEC-Meldungen eines berühmten
  Investors (die vierteljährliche 13F-HR, auf Wunsch auch Form 4 für
  Insider-Geschäfte) und baut sein Portfolio als Gewichtungen nach, die man
  kopieren kann: jede Position, ihr Anteil am Fonds, was seit dem letzten
  Quartal gekauft, aufgestockt, reduziert und verkauft wurde, mit einem Ticker
  zu jeder CUSIP. Dann schreibt er trader/targets.json, damit der Budget-Skill
  es auf das Geld des Nutzers zuschneiden kann. Verwenden, wenn der Nutzer
  sagt „kopiere Buffett“, „kopiere Berkshire“, „was besitzt Ackman“,
  „rekonstruiere diesen Investor“, „zeig mir seine 13F“, „was hat er letztes
  Quartal gekauft“, „kopiere die Top 5“, oder einen Fonds oder berühmten
  Investor nennt (auch auf Englisch: "copy Buffett", "show me their 13F").
argument-hint: "[Investor, Fonds oder CIK] [--top N]"
---

# trader-copycat

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle und Dateinamen
unverändert.

Einen Investor zu kopieren beginnt mit dem, was er gesetzlich zeigen muss:
einer 13F-HR, die jeder Vermögensverwalter mit über 100 Millionen $ in
US-börsennotierten Aktien und anderen 13(f)-Wertpapieren jedes Quartal bei der
SEC einreicht. Dieser Skill liest sie direkt aus SEC EDGAR, baut das Portfolio
nach und macht daraus Zielgewichte für das eigene Konto.

Tool in diesem Ordner (Python mit Standardbibliothek, keine Schlüssel):

```bash
python3 "${CLAUDE_SKILL_DIR}/edgar13f.py" --help
```

Die SEC verlangt, dass sich jedes Programm mit Name und E-Mail ausweist. Einmal
in `trader/config.json` eintragen (`"sec_user_agent": "Dein Name du@example.com"`,
mit dem echten Namen und der echten E-Mail des Nutzers) oder
`export SEC_USER_AGENT=...`. Ohne das ruft das Tool die SEC nicht auf und sagt,
wie man es behebt. Frag den Nutzer danach; erfinde nie einen.

## Was er schreibt

- `trader/targets.json`: die zu kopierenden Gewichte, in der Form, die jeder
  andere Trader-Skill liest: `{ "source", "as_of", "weights": [ {"ticker", "name",
  "weight"} ] }`, Gewichte in % mit 2 Nachkommastellen, die über den
  Aktienanteil 100 ergeben (die 2 Nachkommastellen behalten: die
  Budget-Einteilung braucht sie), dazu der 13F-Anteil, Wert, CUSIPs, was
  übersprungen wurde und warum, und die Vorbehalte.
- `trader/tickers.json` (optional, vom Nutzer): Korrekturen von CUSIP zu
  Ticker, die das Tool immer zuerst verwendet, als `{"650111107": "NYT"}`.

`targets.example.json` in diesem Ordner ist die echte Ausgabe des
Beispiellaufs (Berkshire, Top 5).

## Die Regeln

- **Sag jedes Mal, wie alt die Daten sind.** Eine 13F ist eine Momentaufnahme
  des letzten Quartalstags und wird bis zu 45 Tage später eingereicht. Sag in
  jeder Antwort, die eine verwendet: „Bestände zum 30.06.2026, eingereicht am
  14.08.2026“.
- **Sag, was sie nicht zeigen kann.** Nur Long-Positionen in US-notierten
  Werten: keine Leerverkäufe, kein Cash, keine Anleihen, keine ausländischen
  Aktien, keine privaten Unternehmen, nichts, was innerhalb des Quartals
  gekauft und wieder verkauft wurde, und keine gezahlten Preise.
- **Die Firma, nicht die Person.** Berkshire Hathaway reicht die 13F ein, nicht
  Warren Buffett. Greg Abel ist seit dem 01.01.2026 CEO, und Buffett wurde am
  18.09.2026 Chairman Emeritus. Sag nie „Buffett hat gekauft“, wenn die Meldung
  nur sagt „Berkshire hielt“.
- **Jede Zahl stammt aus der Meldung.** Nenne die Accession Number und verlinke
  die Informationstabelle. Ist ein Ticker geraten (mit `*` markiert), sag das
  und korrigiere ihn mit `--figi` oder `trader/tickers.json`, bevor etwas
  kopiert wird.
- **Optionen und Anleihen werden nie kopiert.** PUT-, CALL- und PRN-Zeilen
  werden als ausgeschlossen aufgeführt. Dieses Paket handelt nur Aktien, außer
  die Config erlaubt mehr.

## Schritt 1: den Investor finden

```bash
python3 "${CLAUDE_SKILL_DIR}/edgar13f.py" find buffett
python3 "${CLAUDE_SKILL_DIR}/edgar13f.py" find "pershing square" --sec
```

`filers.json` listet 23 bekannte Melder mit CIKs, die am 13.10.2026 gegen die
SEC geprüft wurden (Berkshire, Pershing Square, Scion, Bridgewater, ARK,
Duquesne, Appaloosa, Baupost und mehr). `--sec` durchsucht jeden EDGAR-Melder
nach Namen. Hat ein Melder aufgehört zu melden (Scions letzte 13F-HR war vom
03.11.2025), sag es.

## Schritt 2: das neueste Quartal lesen

```bash
python3 "${CLAUDE_SKILL_DIR}/edgar13f.py" filings 1067983
python3 "${CLAUDE_SKILL_DIR}/edgar13f.py" holdings 1067983 --combine --top 15
```

Es lädt die Liste der Einreichungen, nimmt die neueste ursprüngliche 13F-HR,
findet das XML der Informationstabelle im Meldungsordner, summiert die Zeilen,
auf die sich ein Bestand verteilt (Berkshire meldet eine Aktie über mehrere
Tochtergesellschaften), prüft die Summe gegen das Deckblatt und ordnet Ticker
zu: zuerst die `trader/tickers.json` des Nutzers, dann `share_classes.json`
(geprüfte CUSIPs für Unternehmen mit mehreren notierten Aktiengattungen), dann
die `company_tickers.json` der SEC nach Namen und mit `--figi` die kostenlose
CUSIP-Suche von OpenFIGI. `--combine` fasst die Aktiengattungen eines
Unternehmens zusammen (Alphabet A + C). Gibt es eine Änderungsmeldung
(Amendment) für das Quartal, sagt das Tool es; lies sie mit `--accession`.

## Schritt 3: was sich geändert hat

```bash
python3 "${CLAUDE_SKILL_DIR}/edgar13f.py" diff 1067983
```

Neue Positionen, komplett verkaufte, aufgestockte und reduzierte, nach
Stückzahl gegenüber dem Vorquartal. Stückzahlen zu zwei Stichtagen, keine
Trades: sag „hielt am 30. Juni mehr Aktien als am 31. März“, nie „kaufte am“
einem bestimmten Tag.

## Schritt 4: die Ziele schreiben

```bash
python3 "${CLAUDE_SKILL_DIR}/edgar13f.py" copy 1067983 --top 5 --out trader/targets.json
```

Aktiengattungen werden standardmäßig zusammengefasst (`--separate` hält sie
getrennt). `--exclude TICKER` lässt weg, was der Nutzer nicht besitzen will,
`--min-pct 1` streicht Krümel. Die Gewichte sind der %-Anteil jeder Position
an der 13F, so skaliert, dass die ausgewählten zusammen 100 ergeben. Zeig die
Tabelle und übergib dann an `/trader-budget`.

Form 4 (optional): Insider und Eigentümer von über 10 % melden ihre Geschäfte
innerhalb von zwei Werktagen auf Form 4. Um sie zu sehen, öffne
`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<CIK>&type=4&owner=include`
(oder die Einreichungsliste des Melders) und lies die Meldungen, nach denen der
Nutzer fragt. Sie sind schneller als eine 13F, decken aber jeweils nur eine
Aktie ab.

## Beispiel: der Beispiellauf

„Kopiere Berkshire Hathaway, Top 5.“ Die neueste 13F-HR gilt für das Quartal
zum 30.06.2026, eingereicht am 14.08.2026, Accession 0001193125-26-352200,
Summe 299.253.556.246 $ (stimmt mit dem Deckblatt überein).

| # | Bestand | % der 13F | Kopiergewicht |
| --- | --- | --- | --- |
| 1 | Apple (AAPL) | 22,04 | 30,67 |
| 2 | American Express (AXP) | 17,14 | 23,85 |
| 3 | Alphabet (GOOGL + GOOG zusammen) | 12,62 | 17,56 |
| 4 | Coca-Cola (KO) | 10,86 | 15,11 |
| 5 | Bank of America (BAC) | 9,20 | 12,80 |

Gerundet: 30,7 / 23,9 / 17,6 / 15,1 / 12,8. Gegenüber dem Vorquartal: D.R.
Horton neu (3.564 Aktien), Constellation Brands komplett verkauft,
aufgestockt bei Alphabet, Delta, Lennar, Macy's und der New York Times,
reduziert bei Bank of America, Kroger, Capital One, Nucor, Ally und DaVita.
Dann: „Das sind Berkshires Bestände zum 30. Juni 2026. Als Nächstes teilt
/trader-budget sie auf deine 5.000 $ auf.“

## Was er nie tut

- Behauptet nie, der Investor halte die Position heute noch, oder warum er
  gekauft hat.
- Behauptet nie Renditen oder dass das Kopieren eines Fonds Geld bringt. Eine
  13F-Kopie kauft Monate nach dem Fonds, zum heutigen Preis.
- Platziert nie eine Order. Er schreibt Zielgewichte; Einteilung,
  Risikoprüfung und das Ja des Nutzers kommen danach.
- Fragt nie über die Fair-Access-Grenzen der SEC hinaus ab (10 Anfragen pro
  Sekunde; das Tool bleibt weit darunter).

## Sicherheit

- Bildung und Werkzeuge, keine Anlageberatung. Nichts in diesem Paket ist eine
  Empfehlung, irgendetwas zu kaufen oder zu verkaufen.
- Standardmäßig Paper Trading (`"paper": true` in `trader/config.json`).
- Nichts platziert eine Order außer `/trader-broker`, und nur nachdem
  `/trader-risk` sie durchgelassen hat UND der Nutzer im Chat ein
  ausdrückliches Ja für genau diese Order getippt hat, UND das Broker-Tool in
  Claude auf „Needs approval“ steht (Customize > Connectors >
  Tool-Berechtigungen), damit auch Claudes eigene Karte „Allow once / Deny“
  erscheint. Ein Order-Tool nie auf „Always allow“ stellen.
- Keine Optionen, kein Margin, keine Leerverkäufe und kein Hebel, außer die
  Config erlaubt es und der Nutzer bestätigt.
- 13F-Daten sind vierteljährlich und bei der Einreichung bis zu 45 Tage alt.
  Sag das.
