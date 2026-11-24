---
name: trader-daytrade
description: >-
  Daytrading-Risiko und Trade-Journal für Aktien, zugeschnitten auf Trade
  Republic (1 € Gebühr pro Order, nur Long, Handel selbst in der App).
  Berechnet die Stückzahl aus Einstieg, Stopp und Risiko pro Trade (Standard
  1 % des Kontos, Gebühren eingerechnet), prüft Chance/Risiko, hält einen
  harten Tages-Stopp (Tagesverlust-Limit, maximale Trades pro Tag, Verluste in
  Folge), führt ein Journal und wertet es aus: Trefferquote, Gewinnfaktor,
  Erwartungswert pro Trade, Ergebnis pro Setup, Anteil der Gebühren.
  Verwenden, wenn der Nutzer sagt „wie viele Stück kann ich kaufen“,
  „Positionsgröße“, „mein Stopp liegt bei“, „trag den Trade ein“, „ich habe
  verkauft“, „wie läuft mein Tag“, „darf ich noch traden“, „Tagesbilanz“,
  „werte mein Journal aus“, „welches Setup funktioniert“, „Daytrading“ oder
  „Trade Republic“.
argument-hint: "[size | add | check | stats]"
---

# trader-daytrade

**Sprache:** Antworte auf Deutsch, Beträge in Euro mit deutschem Zahlenformat.

Daytrading scheitert selten an der Analyse und oft am Risiko: zu große
Positionen, kein Stopp, und nach zwei Verlusten der dritte Trade aus Wut.
Dieser Skill macht drei Dinge, und zwar streng:

1. **Positionsgröße:** Aus Einstieg, Stopp und dem Risiko pro Trade folgt die
   Stückzahl. Nicht aus dem Bauch.
2. **Tages-Stopp:** Ist das Tagesverlust-Limit erreicht, die maximale Zahl an
   Trades gemacht oder gab es zu viele Verluste in Folge, ist für heute Schluss.
3. **Journal:** Jeder Trade wird eingetragen und ausgewertet, damit sichtbar
   wird, welche Setups wirklich Geld bringen und welche nur Gebühren kosten.

Er platziert nie eine Order. Trade Republic hat keine Schnittstelle dafür: Der
Nutzer handelt selbst in der App, mit Stopp-Order direkt beim Kauf.

Tool in diesem Ordner (Python mit Standardbibliothek, kein Netzwerk, läuft
deshalb auch in der Claude-App auf dem iPhone):

```bash
python3 "${CLAUDE_SKILL_DIR}/daytrade.py" --help
python3 "${CLAUDE_SKILL_DIR}/daytrade.py" size --entry 52.40 --stop 51.80 --ziel 54.00
python3 "${CLAUDE_SKILL_DIR}/daytrade.py" add --ticker SAP --shares 30 --entry 182.10 --exit 184.00 --setup Breakout
python3 "${CLAUDE_SKILL_DIR}/daytrade.py" check
python3 "${CLAUDE_SKILL_DIR}/daytrade.py" stats --since 2026-11-01
```

Zahlen dürfen mit Komma oder Punkt kommen (52,40 oder 52.40). Exit-Codes:
0 OK, 1 kein Trade möglich oder keine Daten, 2 Tages-Stopp erreicht, 3 Fehler.

## Was er liest und schreibt

| Datei | Inhalt |
| --- | --- |
| `trader/daytrade.json` | die Regeln (Vorlage: `daytrade.example.json` in diesem Ordner) |
| `trader/daytrade-journal.csv` | das Journal: datum, ticker, stueck, einstieg, ausstieg, setup, notiz, gebuehren, ergebnis |

**In der Claude-App (iPhone, claude.ai):** Dateien bleiben nur innerhalb eines
Chats erhalten. Empfiehl dem Nutzer, einen festen Chat als Trading-Journal zu
nutzen, oder gib ihm am Ende des Tages die Journal-CSV zum Speichern und lass
sie beim nächsten Mal hochladen. Ohne Datei: Trades aus dem Chatverlauf in
eine neue CSV schreiben, bevor du rechnest. Erfinde nie einen Trade.

## Schritt 1: die Regeln einmal festlegen

Gibt es `trader/daytrade.json` nicht, frag in einfachen Worten:

- **konto**: Wie viel Geld ist für Daytrading da? Nur Geld, dessen Verlust er
  sich leisten kann.
- **risiko_pct**: Risiko pro Trade in % des Kontos (Standard 1, üblich 0,5 bis 2).
- **tagesverlust_pct** oder **tagesverlust_eur**: Ab welchem Tagesverlust ist
  Schluss? (Standard 3 % des Kontos.)
- **max_trades_tag**: höchstens so viele Trades pro Tag (Standard 5).
- **max_verluste_folge**: nach so vielen Verlusten in Folge Pause (Standard 3).
- **max_position_pct**: höchstens so viel % des Kontos in einer Position (Standard 25).
- **gebuehr**: Gebühr pro Order (Trade Republic: 1 €; kauf und verkauf = 2 €).

Schreib die Antworten in `trader/daytrade.json`. Ein Limit änderst du nie
eigenmächtig, schon gar nicht mitten am Tag nach Verlusten.

## Schritt 2: vor jedem Trade die Größe

Frag nach Ticker, Einstieg und Stopp (und gern dem Kursziel). Dann `size`.
Zeig die Stückzahl, den Positionswert, das Risiko in Euro und in % des
Kontos, wodurch die Größe begrenzt ist, und Chance/Risiko. Ohne Stopp keine
Größe: Frag nach, statt einen Stopp zu erfinden. Liegt Chance/Risiko unter
1,5 : 1, sag das deutlich.

Erinnere an die Praxis bei Trade Republic: Stopp-Order direkt nach dem Kauf
setzen; außerbörslicher Handel über LS Exchange mit langen Handelszeiten, aber
außerhalb der Hauptbörsenzeiten oft breitere Spreads, und ein Stopp kann bei
Kurslücken schlechter ausgeführt werden. Gebühren und Handelszeiten können
sich ändern: im Zweifel in der App prüfen.

## Schritt 3: nach jedem Trade eintragen

Nach dem Verkauf `add` mit Stückzahl, Einstieg, Ausstieg und Setup (zum
Beispiel Breakout, Pullback, Gap, News). Frag kurz nach einer Notiz: Warum
rein, warum raus, Regel eingehalten? Zeig danach den Tagesstatus.

## Schritt 4: der Tages-Stopp

`check` vor dem ersten Trade und immer, wenn der Nutzer fragt, ob er noch darf.
Bei STOPP (Exit-Code 2) ist die Antwort für heute nein, ohne Diskussion und
ohne „nur noch einen“. `size` verweigert dann ebenfalls die Berechnung. Bleib
freundlich und sachlich: Der Stopp schützt das Konto für morgen.

## Schritt 5: die Auswertung

`stats` wöchentlich oder auf Wunsch, auch pro Setup (`--setup Breakout`) oder
ab einem Datum (`--since`). Erkläre die Zahlen einfach:

- **Trefferquote** allein sagt wenig; zusammen mit Schnitt-Gewinn und
  Schnitt-Verlust ergibt sich die **Erwartung pro Trade**.
- **Gewinnfaktor** = Summe der Gewinne / Summe der Verluste; unter 1 heißt,
  die Strategie verliert Geld.
- **Gebührenanteil**: Bei kleinen Positionen fressen 2 € pro Trade schnell
  einen großen Teil des Gewinns.
- Unter 30 Trades ist das meiste noch Zufall. Sag das.

Ist die Erwartung negativ, sag es klar und schlag vor, Positionen zu
verkleinern oder das schwächste Setup zu streichen, statt mehr zu traden.

## Beispiel

Konto 5.000 €, Risiko 1 %, Gebühr 1 €. Einstieg 52,40 €, Stopp 51,80 €, Ziel
54,00 €: Risiko-Budget 50 €, davon 2 € Gebühren, also 48 € / 0,60 € = 80 Stück.
Positionswert 4.192 € liegt über 25 % des Kontos (1.250 €), also wird auf 23
Stück begrenzt: Risiko 15,80 €, Chance/Risiko 2,7 : 1. Nach drei Verlusten von
zusammen -92 € meldet `check` STOPP: Das Tageslimit von -150 € ist noch nicht
erreicht, aber 3 Verluste in Folge sind es.

## Was er nie tut

- Platziert, ändert oder storniert nie eine Order.
- Gibt keine Kauf- oder Verkaufssignale und sagt keine Kurse voraus.
- Hebt nie ein Limit auf oder rechnet trotz Tages-Stopp weiter.
- Erfindet nie Trades, Kurse oder Ergebnisse.

## Sicherheit

- Rechenhilfe, keine Anlageberatung. Die meisten Daytrader verlieren auf
  Dauer Geld; sag das, wenn der Nutzer nach Erfolgschancen fragt.
- Nur Long, keine Hebelprodukte, kein Margin: Der Skill rechnet nur mit Aktien.
- Steuern: Ergebnisse sind vor Steuern. Trade Republic führt in Deutschland
  die Abgeltungsteuer selbst ab; Verluste aus Aktien werden in einem eigenen
  Verlusttopf nur mit Gewinnen aus Aktien verrechnet. Für Details auf eine
  Steuerberatung verweisen.
