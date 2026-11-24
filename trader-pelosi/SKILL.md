---
name: trader-pelosi
description: >-
  Der Pelosi-Tracker. Beobachtet die Aktiengeschäfte, die Kongressmitglieder
  nach dem STOCK Act offenlegen müssen: liest die öffentlichen Periodic
  Transaction Reports (PTRs) des House Clerk, sobald sie erscheinen, meldet
  sich einmal pro neuer Meldung und macht aus jedem PDF saubere Zeilen (wer,
  Eigentümer, Aktie, Ticker, Kauf oder Verkauf, Basispreis und Verfall bei
  Optionen, Handelsdatum, Betragsspanne, wie viele Tage die Offenlegung
  gedauert hat). Markiert Trades in Aktien, die der Nutzer hält. Für Berichte
  des Senats gibt es einen dokumentierten manuellen Weg. Verwenden, wenn der
  Nutzer sagt „was kauft Pelosi“, „verfolge Nancy Pelosi“,
  „Kongress-Trades“, „Aktiengeschäfte von Politikern“, „hat ein
  Abgeordneter X gekauft“, „sag mir Bescheid, wenn Pelosi meldet“ oder
  „starte den Pelosi-Skill“.
argument-hint: "[Name des Mitglieds] [--read]"
---

# trader-pelosi

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle, Dateinamen und
Wertpapierbezeichnungen aus den Meldungen unverändert.

Kongressmitglieder müssen ihre Geschäfte melden, die ihres Ehepartners und die
ihrer unterhaltsberechtigten Kinder. Der House Clerk stellt jeden Bericht als
PDF online und listet alle in einer Indexdatei pro Jahr. Dieser Skill liest
diesen Index, bemerkt den Moment, in dem ein neuer Bericht erscheint, und
liest den Bericht für den Nutzer.

Er ist schnell. Er ist nicht früh. Ein PTR ist innerhalb von 30 Tagen fällig,
nachdem das Mitglied von dem Geschäft erfahren hat, und nie später als 45 Tage
danach. Bis ihn jemand lesen kann, ist der Trade also Tage oder Wochen alt.
Hier gibt es keine Insiderinformationen: nur öffentliche Meldungen, schnell
gelesen. Sag das jedes Mal.

Tool in diesem Ordner (Python mit Standardbibliothek; `pdftotext` aus poppler
ist optional, um die PDFs lokal zu lesen):

```bash
python3 "${CLAUDE_SKILL_DIR}/ptr.py" --help
```

## Was er liest und schreibt

- Liest `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/<YEAR>FD.zip`
  (ein `<Member>` pro Meldung: Name, Wahlbezirk, FilingType, FilingDate, DocID)
  und jeden PTR unter `.../public_disc/ptr-pdfs/<YEAR>/<DocID>.pdf`.
- Schreibt `trader/state/pelosi.json` (die schon gezeigten DocIDs, damit jeder
  PTR nur einmal gemeldet wird) und legt heruntergeladene PDFs in
  `trader/state/ptr-pdfs/` ab.
- Liest `trader/portfolio.json` (falls vorhanden), um Trades in eigenen
  Beständen zu markieren.

## Die Regeln

- **Zitiere die Meldung, nicht einen Tracker.** Jede Zeile stammt aus dem
  PTR-PDF auf der Seite des Clerk, mit DocID und Link. Tracker von Drittanbietern
  sind zum Stöbern in Ordnung, können aber danebenliegen (Capitol Trades zeigte
  Pelosis Handelsdaten einen Tag früher als ihre PTRs). Der PTR gilt.
- **Beträge sind Spannen.** „1.000.001 $ - 5.000.000 $“, nie „3 Millionen $“.
- **Der Eigentümer zählt.** SP ist der Ehepartner, JT gemeinsam, DC ein
  unterhaltsberechtigtes Kind, leer das Mitglied selbst. Pelosis Trades 2026
  sind alle SP: Paul Pelosi.
- **Nenne die Verzögerung.** Jede Zeile zeigt, wie viele Tage zwischen Trade
  und Meldung lagen; über 45 wird als verspätet markiert.
- **Optionen sind Optionen.** Ein gekaufter Call mit Basispreis und Verfall ist
  kein Aktienkauf. Das Tool liest Kontrakte, Basispreis und Verfall aus der
  Beschreibung und markiert Ausübungen.

## Schritt 1: was gemeldet wurde

```bash
python3 "${CLAUDE_SKILL_DIR}/ptr.py" index --member pelosi
python3 "${CLAUDE_SKILL_DIR}/ptr.py" index --since 2026-10-01        # alle Mitglieder
python3 "${CLAUDE_SKILL_DIR}/ptr.py" index --member "Josh Gottheimer" --year 2025
```

`--member` nimmt einen Nachnamen, „Vorname Nachname“ oder „Nachname, Vorname“
und lässt sich wiederholen. `--type ''` listet jeden Meldungstyp
(Jahresberichte sind Typ O).

## Schritt 2: auf neue achten

```bash
python3 "${CLAUDE_SKILL_DIR}/ptr.py" new --member pelosi --read
```

Zeigt nur PTRs, die bei der letzten Prüfung noch nicht gesehen wurden (der
erste Lauf zeigt die letzten 45 Tage), lädt und liest sie mit `--read` und
vermerkt sie in der Zustandsdatei. Exit-Code 1 heißt: nichts Neues. Im Januar
prüft er auch den Index des Vorjahres. Der Clerk baut die Indexdatei etwa
einmal am Tag neu (die am 13.10.2026 gelesene Kopie trug den Zeitstempel 09:00
desselben Morgens), stündliche Prüfungen an Werktagen reichen also völlig:
mit `/loop 1h` oder einer geplanten Aufgabe.

## Schritt 3: einen Bericht lesen

```bash
python3 "${CLAUDE_SKILL_DIR}/ptr.py" fetch 20035143
python3 "${CLAUDE_SKILL_DIR}/ptr.py" parse ptr.txt --filed 2026-08-21 --json
```

`fetch` speichert das PDF und gibt, wenn `pdftotext` installiert ist, die
Zeilen aus. Ist es nicht installiert, öffne das gespeicherte PDF und lies es
direkt: Du kannst PDFs lesen. `parse` macht aus `pdftotext -layout`-Text
Zeilen. Prüfe die Zeilenzahl gegen das PDF, wenn ein Bericht über mehrere
Seiten geht.

## Beispiel: die Meldung aus dem Beispiellauf

```
NEW Periodic Transaction Report: Hon. Nancy Pelosi (CA11) filed 2026-08-21, doc 20035143
  - spouse purchase, Bloom Energy Corporation Class A Common Stock (BE): 100 call
    options, $100 strike, expires 2027-06-17, $1,000,001 - $5,000,000, traded
    2026-07-24, disclosed 28 days later
```

Auf Deutsch: Kauf durch den Ehepartner, 100 Call-Optionen auf Bloom Energy
(BE), Basispreis 100 $, Verfall 17.06.2027, 1.000.001 $ - 5.000.000 $,
gehandelt am 24.07.2026, 28 Tage später offengelegt.

Derselbe PTR zeigt außerdem 10.000 und 5.000 BE-Aktien, einen zweiten Block
von 100 BE-Calls am 28.07., Intel-Aktien und 50 Intel-Calls (Basispreis 50 $,
17.06.2027) und eine private Immobilien-LLC ohne Ticker. Ihre anderen PTRs
2026: 20033725 (23.01.), 20034836 (23.06., Calls auf Intel und Uber) und
20035553 (02.10., eine Immobilien-LLC). Dann: „Das ist eine öffentliche
Offenlegung, eingereicht 28 Tage nach dem Trade. Sie sagt, was Paul Pelosi im
Juli gekauft hat, nicht was irgendjemand als Nächstes kaufen wird.“

Will der Nutzer darauf handeln, geht es den langen Weg: nur Aktien (die Config
hat `allow_options: false`), eingeteilt von `/trader-budget`, geprüft von
`/trader-risk`, platziert von `/trader-broker` erst nach seinem Ja.

## Der Senat: der manuelle Weg

Berichte des Senats liegen unter `https://efdsearch.senate.gov`. Vor der Suche
verlangt die Seite, per Häkchen den rechtlichen Einschränkungen zur Nutzung
der Berichte zuzustimmen. Diese Zustimmung muss die Person selbst geben, daher
klickt dieser Skill sie nicht und automatisiert sie nicht. Der Weg:

1. Der Nutzer öffnet `https://efdsearch.senate.gov/search/` in seinem Browser
   und stimmt selbst zu.
2. Er wählt den Berichtstyp „Periodic Transactions“, gibt den Nachnamen des
   Senators ein, setzt den Zeitraum und sucht.
3. Er öffnet den Bericht: Elektronische Meldungen zeigen eine Tabelle der
   Transaktionen, Papiermeldungen sind eingescannte Bilder.
4. Er fügt die Tabelle (oder einen Screenshot oder die gespeicherte Seite) in
   den Chat ein, und du schreibst sie in derselben Form wie die Zeilen des
   Repräsentantenhauses auf, mit dem Link zum Bericht und demselben Hinweis
   auf die 45 Tage.

## Was er nie tut

- Sagt oder unterstellt nie, ein Mitglied habe Insiderinformationen oder wer
  einen Politiker kopiere, schlage den Markt. Keine Renditeversprechen.
- Stellt nie eine Spanne als genauen Dollarbetrag dar oder das Datum eines
  Trackers als Handelsdatum.
- Platziert nie eine Order und kopiert nie Optionsgeschäfte.
- Automatisiert nie die Zustimmung beim Senat oder irgendeine Anmeldung.

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
- Trades von Kongressmitgliedern sind ÖFFENTLICHE Offenlegungen, eingereicht
  bis zu 45 Tage nach dem Trade (STOCK Act). Dieser Skill liest sie schnell;
  er hat keine Insiderinformationen und sagt das auch.
