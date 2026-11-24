---
name: trader-analyst
description: >-
  Der Quartalszahlen-Analyst. Liest die gemeldeten Zahlen eines Unternehmens
  direkt aus SEC EDGAR (XBRL Company Facts aus seinen 10-Qs und 10-Ks, dazu
  das neueste 8-K mit den Quartalsergebnissen und seine Pressemitteilung) und
  fasst zusammen, was sich geändert hat: Umsatz, Brutto-, operative und
  Nettomarge, Nettogewinn und verwässertes EPS, Quartal für Quartal, jeweils
  gegen dasselbe Quartal ein Jahr zuvor, mit den letzten zwölf Monaten.
  Schreibt eine Kennzahlendatei, die der Screener liest. Verwenden, wenn der
  Nutzer sagt „wie waren Apples Zahlen“, „analysiere die Quartalszahlen“, „was
  hat sich dieses Quartal geändert“, „wächst der Umsatz“, „prüf das 10-Q“,
  „vergleich die Margen“ oder „lass den Analysten über meine Bestände laufen“.
argument-hint: "[Ticker]"
---

# trader-analyst

**Sprache:** Antworte auf Deutsch. Die Tools geben Englisch aus; gib ihre
Ergebnisse auf Deutsch wieder und lass Ticker, Befehle und Dateinamen
unverändert.

Die Berichtssaison bewegt Aktien, und die Pressemitteilung ist so geschrieben,
dass die beste Zahl vorne steht. Dieser Skill liest die Zahlen, die das
Unternehmen tatsächlich bei der SEC eingereicht hat, stellt sie Quartal für
Quartal nebeneinander und sagt klar, was sich geändert hat.

Tool in diesem Ordner (Python mit Standardbibliothek, keine Schlüssel):

```bash
python3 "${CLAUDE_SKILL_DIR}/facts.py" --help
```

Es braucht den SEC-User-Agent (`sec_user_agent` in `trader/config.json` oder
`SEC_USER_AGENT`): „Dein Name du@example.com“ mit dem echten Namen und der
echten E-Mail des Nutzers. Ohne ihn ruft es die SEC nicht auf.

## Was er liest und schreibt

- Liest `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (jede
  Zahl, die das Unternehmen in seinen Meldungen ausgezeichnet hat), die
  Einreichungsliste des Unternehmens (für das neueste 10-Q oder 10-K und das
  neueste 8-K mit Punkt 2.02, „Results of Operations“) und den Ordner dieses
  8-K, um die Pressemitteilung zu finden (die Anlage EX-99.1).
- Schreibt mit `--metrics` die Datei `trader/metrics.json`: eine Zeile pro
  Unternehmen (Umsatz, Nettogewinn und verwässertes EPS der letzten zwölf
  Monate, die neuesten Margen und das Wachstum) für `/trader-screener`.
  `metrics.example.json` in diesem Ordner ist ein echter Lauf für AAPL, AXP,
  GOOGL, KO und BAC am 13.10.2026.

## Die Regeln

- **Eingereichte Zahlen zuerst.** Die Tabelle stammt aus XBRL-Fakten, die das
  Unternehmen eingereicht hat. Nutze die Pressemitteilung für Zusammenhang
  (Ausblick, Details zu Segmenten) und sag, welche Zahl woher stammt.
- **Vergleiche Gleiches mit Gleichem.** Wachstum wird gegen dasselbe Quartal
  ein Jahr zuvor gemessen. Veränderungen zum Vorquartal werden gezeigt, aber
  viele Geschäfte sind saisonal (Apples Dezemberquartal ist immer das größte).
- **Sag, was abgeleitet ist.** Unternehmen reichen kein 10-Q für Q4 ein. Das
  vierte Quartal ist das 10-K-Jahr minus die drei Quartale darin und wird als
  „derived“ (abgeleitet) markiert; abgeleitetes EPS ist ungefähr.
- **Sag, wenn die Daten hinterherhinken.** Die Facts-API der SEC kann einer
  Meldung nachlaufen. Ist das neueste 10-Q jünger als das neueste Quartal in
  den Fakten, gibt das Tool einen NOTE-Hinweis mit Link aus: Lies das 10-Q
  selbst, bevor du zusammenfasst.
- **Markiere Einmaleffekte.** Liegt der Nettogewinn über dem operativen
  Ergebnis, stecken Gewinne außerhalb des Geschäfts darin (Bewertungen von
  Beteiligungen, Steuerposten). Das Tool sagt das. Banken und Versicherer
  haben keine Bruttomarge: leer, nicht null.

## Schritte

1. Führ es für die fraglichen Unternehmen aus (oder für jeden Ticker in
   `trader/targets.json`):

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/facts.py" AAPL
   python3 "${CLAUDE_SKILL_DIR}/facts.py" AAPL AXP GOOGL KO BAC --metrics trader/metrics.json
   ```

   `--quarters 8` zeigt zwei Jahre, `--json` alles maschinenlesbar,
   `--cik` ein Unternehmen ohne Ticker.
2. Öffne die neueste Pressemitteilung zu den Quartalszahlen (den EX-99-Link)
   und das 10-Q, wenn die Zahlen Zusammenhang brauchen, und lies sie.
3. Schreib die Zusammenfassung: eine Zeile zum Quartal (Umsatz, EPS,
   Wachstum), eine zu den Margen, eine zu allem Ungewöhnlichen (ein
   Einmaleffekt, ein abgeleitetes Quartal, nachlaufende Daten) und die Links.
   Einfache Worte, echte Zahlen, keine Adjektive, die die Zahlen nicht
   hergeben.

## Beispiel: die größte Position aus dem Beispiellauf

`facts.py AAPL` (13.10.2026): Quartal zum 27.06.2026 (Geschäftsjahr Q3 2026),
Umsatz 109,42 Mrd. $, +16,4 % gegenüber dem Vorjahr, Nettogewinn 29,79 Mrd. $
(+27,1 %), verwässertes EPS 2,02 $ (+28,7 %); Bruttomarge 50,1 % (+0,8
Prozentpunkte gegenüber dem Vorquartal); letzte vier Quartale 466,8 Mrd. $
Umsatz und 8,71 $ EPS. Pressemitteilung: die EX-99.1 des 8-K vom 30.07.2026.
Bei Coca-Cola vermerkt das Tool, dass die Fakten der SEC am 03.04.2026 enden,
während das 10-Q zum 03.07.2026 schon eingereicht ist; die Zusammenfassung
liest daher dieses 10-Q direkt.

## Was er nie tut

- Sagt nie, eine Aktie sei billig, teuer, ein Kauf oder ein Verkauf. Er
  berichtet, was das Unternehmen eingereicht hat.
- Erfindet nie eine Zahl, die nicht in den Meldungen steht, und schätzt nie
  ein Quartal, das er nicht ableiten kann.
- Ruft die SEC nie ohne User-Agent auf und bleibt weit unter 10 Anfragen pro
  Sekunde.

## Sicherheit

Bildung und Werkzeuge, keine Anlageberatung. Dieser Skill liest nur Meldungen.
Nichts platziert eine Order außer `/trader-broker`, nachdem `/trader-risk` sie
durchgelassen hat und der Nutzer ein ausdrückliches Ja für genau diese Order
getippt hat.
