# Industriova 0.3 – P11-F1 / P11-F2 / P11-G: Economy Rebalance

Stand: 2026-10-23T18:48:13.604626+00:00. **Produktiv implementiert, vollständig regressionsgeprüft und als neue Windows-Testversion gebaut.** Kein weiterer Schattenpreis-Entwurf. Der vorausgehende uncommittete Arbeitsstand wurde als vollständige Quellenkopie mit Versions-/SHA256-Manifest gesichert; Ausgangs-HEAD: `0e4a9e0c7f80d74916bfeeae39a150374e2d8ebd`. Die 1.004 Ausgangsdateien liegen unter `artifacts/phase11fg/starting-snapshot`. Bestehende fremde Änderungen wurden nicht zurückgesetzt oder pauschal committed.

## 1. Ergebnis und Arbeitsabschnitte

* **F1:** globale MK-Kostenfunktion einschließlich Floor und Paybackterm ersetzt; MK1–99, +25 % der MK1-Leistung pro Schritt, Rarity und Research bleiben erhalten.
* **F2:** XP folgt akzeptierten Produktionsereignissen und einer einheitlichen Sekundenreihenfolge für große Zeitschritte. Persistente Ereigniszähler, Save/Load und UTC-Tagesgrenzen geprüft. Die Unlock-Prüfung wurde ohne Regeländerung auf eine gemeinsame Ressourcenprojektion pro Durchlauf umgestellt, damit Catchup nicht 353 Katalogzuordnungen je Kandidat neu aufbaut.
* **G:** exakt 178 N1-Rezepte und 353 C2-Preise produktiv; explizite Wirtschaftsmigration, neue Test-Save-Ablage und separat benannter Windows-Build.

Die gesicherten Arbeitsabschnitte `F1-mk-costs`, `F2-xp-events` sowie die abschließende G-Quellenkopie und `work-sections.json` machen die Dateigruppen nachvollziehbar. F2 erhielt bei der integrierten Mehrinput-Regression die notwendige Ergänzung der Sekundenreihenfolge. Es werden keine drei sauberen Git-Commits auf dem schon zuvor uncommitteten Projekt behauptet.

**Abschluss:** 2.758 bestandene Tests in 102 Modulen, null offene Fehler; 16/16 historische Migrationen und 5/5 persönliche Backup-Kopien; 30 Ketten-/MK-/Researchzustände, elf finanzierte Budgetfirmen, 18 Zeitauflösungsvergleiche und acht echte Neustarts. Die 41 Ketten-/Budgetzustände liefern im letzten Stundenfenster jeweils die vollständigen Ressourcenraten und den erwarteten Cashflow, ohne Pause-Controller. Die 18 Schrittweitenläufe sind drei Firmen in sechs Auflösungen, keine 18 unabhängigen Branchen.

## 2. Exakte globale MK-Formel

Für vorhandenes MK `m` von 1 bis 98 und Familie `d`:

```text
Leistungsfaktor(MK) = 1 + 0.25 * (MK - 1)
Kapitalfloor(d,m) = 0.25 * CommonKartenpreis(d) * (1 + 0.025 * (m - 1))
Wertterm(d,m) = 0.25 * 0.5 * V(d) * T(m + 1)
Upgradequote(d,m) = ceil(100 * max(Kapitalfloor, Wertterm)) / 100
```

`V(d)` bleibt das vorhandene maximale Nettowertpotenzial der **gesamten** Familie pro Sekunde, nun aus N1/C2: Maschinen verwenden die höchste direkte C2-Wertschöpfung ihrer Rezepte minus das bestehende Kohleäquivalent für Leistung, mindestens 0,01. Energie verwendet MW × Kohlepreis × 0,01; Freight Kapazität/Fahrtzeit, ebenfalls mindestens 0,01. Das Energieäquivalent ist ein Quote-Proxy und keine neue Stromrechnung. Der Freight-Proxy entspricht kontinuierlich verfügbarer Ware zu $1 pro Einheit. Diese isolierten Werte sind **keine gemessenen Energie-/Freighterlöse**; realisierbarer Mehrcash und Supportinvestitionen stehen im vollständigen Firmenvergleich.

`T(k)` interpoliert zwischen den folgenden gemeinsamen Ankern geometrisch:

| nächstes MK | 2 | 10 | 30 | 60 | 90 | 99 |
| --- | --- | --- | --- | --- | --- | --- |
| Sekunden | 180 | 600 | 3600 | 14400 | 43200 | 86400 |

Zwischen `(lo,a)` und `(hi,b)` gilt `T(k)=a*(b/a)^((k-lo)/(hi-lo))`. Die Kurve ist an allen Übergängen stetig. Der Wertterm trägt den globalen Faktor 0,5, weil eine vollständig angepasste Firma zusätzlich Primärproduktion, Energie und Freight aufwerten muss. Es gibt keine Produkt-Ausnahmeliste. Rarity/Research verbilligen die Quote nicht beim Umkonfigurieren. Alle 1.470 Quotes sind positiv, endlich und strikt steigend; MK99 besitzt keine weitere Quote. Numerisch ungültige Quotes werden abgewiesen.

Die alte Kurve `B*m^1.7` plus `0.25*V*900*((m+1)/2)^2.3` wurde vollständig neu kalibriert. Der Floor steigt jetzt linear statt als Potenz. Eine glatte Vergleichskurve `180*(k/2)^(ln(480)/ln(49.5))` trifft dieselben Endpunkte, fordert bei MK10 aber bereits rund 2.297 statt 600 Sekunden, bei MK30 rund 13.065 statt 3.600. Sie verschiebt zu viel Belastung ins frühe/mittlere Spiel. Beide Kandidaten einschließlich Quotes und kumulierter Investitionen sind in `mk-quotes.csv` enthalten.

### Kumulierte Karteninvestitionen

Nur Upgrades, ohne initialen Kartenkauf oder Gebäude. Beide Spalten benutzen dieselbe N1/C2-Wirtschaft, damit der Kurveneffekt isoliert bleibt.

| Familie | alte Summe MK1→99 unter C2 | neue Summe MK1→99 |
| --- | --- | --- |
| machine.extractor | $105,172,806.12 | $402,961.21 |
| machine.processor | $105,714,882.51 | $404,952.10 |
| machine.fabricator | $30,881,537.71 | $118,073.40 |
| machine.assembler | $101,919,989.28 | $390,391.34 |
| energy.solar_array | $16,075,998.43 | $42,355.85 |
| energy.wind_turbine | $32,151,996.36 | $74,529.85 |
| energy.coal_power_plant | $46,441,772.29 | $126,895.90 |
| energy.gas_power_plant | $109,279,679.35 | $377,886.67 |
| energy.nuclear_power_plant | $535,866,598.19 | $1,073,497.69 |
| freight.truck | $36,176,044.94 | $138,678.39 |
| freight.train | $180,711,544.37 | $692,479.53 |
| freight.ship | $3,614,441,583.89 | $13,853,351.45 |
| freight.aircraft | $1,204,813,861.58 | $4,617,784.10 |
| machine.drilling | $105,172,806.12 | $402,961.21 |
| machine.agriculture | $105,172,806.12 | $402,961.21 |

### Ganze Firmen und marginale Amortisation

Alle 98 Übergänge wurden für zwölf volle Ketten berechnet, einschließlich vollständiger gleichzeitiger Vorproduktion, aller Energie-/Freightkarten, echter Gebäudekurven und bezahlter Lagerpuffer. Uniformes MK erhält die Produktionsverhältnisse; zusätzlich notwendige Lagerstufen werden bezahlt. Kein isoliertes Upgrade wird trotz nachgelagertem Engpass als voll wirksam ausgegeben.

| Ziel-MK | beobachtete Spanne voller Ketten |
| --- | --- |
| 2–10 | 4.2–12.8 Minuten |
| 11–30 | 7.1–62.1 Minuten |
| 31–60 | 35.5–248.4 Minuten |
| 61–90 | 140.7–745.2 Minuten |
| 91–99 | 439.3–1490.4 Minuten |

Die Designkorridore sind Orientierung: einzelne Ketten erreichen einen Bereich früher; Rohstoffdirektverkauf liegt bei MK99 mit 24,84 Stunden geringfügig über 24 Stunden. Lager-/Infrastruktursprünge bleiben sichtbar. Bei MK98→99:

| Kette | alt: Tage | neu: Stunden | zusätzliches Kapital | zusätzlich $/min |
| --- | --- | --- | --- | --- |
| iron_ore | 172.21 | 24.84 | $44,712.00 | $30.00 |
| iron | 112.51 | 16.27 | $58,572.00 | $60.00 |
| copper | 112.51 | 16.27 | $58,572.00 | $60.00 |
| flour | 126.22 | 18.27 | $65,772.00 | $60.00 |
| lumber | 126.22 | 18.27 | $65,772.00 | $60.00 |
| steel | 113.88 | 16.49 | $356,256.00 | $360.00 |
| bitumen | 112.51 | 16.27 | $58,572.00 | $60.00 |
| silicon | 118.45 | 17.16 | $370,656.00 | $360.00 |
| biodiesel | 98.24 | 14.21 | $187,632.02 | $220.00 |
| industrial_equipment | 102.74 | 23.17 | $2,336,022.16 | $1,680.00 |
| microchip | 99.89 | 14.44 | $1,524,960.12 | $1,760.00 |
| ai_server | 93.85 | 13.56 | $1,854,576.16 | $2,280.00 |

`mk-chain-payback.csv` enthält 2.352 Alt-/Neu-Zeilen mit tatsächlicher Quote, kumuliertem Firmenkapital, zusätzlichem Durchsatz/Cash und Tagesrendite. `mk-cumulative-progression.csv` setzt zusätzlich das gesamte MK99-Kapital ins Verhältnis zum nachhaltigen MK99-Erlös. Ein solcher Kapitalquotient ist ausdrücklich keine durchgespielte Genesis→MK99-Karriere. Company-Level, RP, echte Lieferverzögerungen, alternative Expansion und zufällige Rarity-Historien werden dadurch nicht erfunden.

## 3. XP-Korrektur und Zeitverarbeitung

Früher wurde die produktive Zeit eines akzeptierten Sechs-Sekunden-Batches auf die Dauer des aktuellen Aufrufs begrenzt. Deshalb vergab dt1 nur eine, dt6 bis zu sechs produktive Sekunden. Außerdem verschoben große Materialpässe bei Mehrinputketten die Abschlussphasen. Nur die erste Formel zu ändern reichte deshalb für AI Server nicht.

Jetzt werden echte akzeptierte Abschlüsse zeitlich zugeordnet. Alle Maschinen teilen die Vereinigung der Ein-Sekunden-Abschlussintervalle. Je Intervall zählt höchstens eine Continuity-Sekunde. `last_productive_bucket` und `productive_event_seconds` werden gespeichert. Rejected Output, fehlende Inputs, fehlender Strom und Pausen erzeugen keine produktiven Ereignisse. Ein Pause/Resume ohne verstrichene Zeit kann kein Ereignis erneut vergüten.

Größere Zeitabschnitte laufen in der normalen Sekundenreihenfolge ab. Virtuelle UTC-Zeitpunkte werden pro Unterschritt weitergegeben; damit werden Tagesgrenzen auch bei Catchup richtig zugeordnet. Verfügbare Inputs, Fuel, Freight-Abfahrten und Ankünfte werden dabei in derselben Reihenfolge wie bei dt1 verarbeitet. Die normale dt1-XP-Geschwindigkeit bleibt erhalten; insbesondere wird keine pauschale sechsfach schnellere Continuity eingeführt. Efficiency, First Production, Mastery, Level und RP-Regeln bleiben bestehen.

| Firma | dt 1/2/3/6/30/60: XP jeweils | produktive Ereignissekunden | Liefererlös nach 2 h |
| --- | --- | --- | --- |
| flour | 2,340.00 | 1,200.00 | $27,600.00 |
| steel | 2,840.00 | 1,200.00 | $165,600.00 |
| ai_server | 3,300.00 | 3,595.00 | $1,048,800.00 |

Für diese drei vollständigen Firmen sind nach zwei Stunden **Produktion, Verbrauch, Bestände, Lieferungen, Cash, produktive Ereignissekunden, alle XP-Kategorien, Company-Level und Unlock-IDs identisch**. In jedem Lauf wurde nach 3.600 Sekunden gespeichert/geladen. Zusätzlich prüfen 27 gezielte XP-Tests dt300, einen ganzen dt7200-Catchup, Research-Speed, Ausfallzustände, UTC-Mitternacht und kleine 0,25-s-Intervalle einer versorgten Maschine. Die belegte Mehrinputmatrix ist 1/2/3/6/30/60 Sekunden; keine ungetestete universelle Aussage zu beliebigen Eingriffs-/Subsekundenfolgen.

Wichtige getrennte Folgen: Ein dt300-Aufruf zählt nun 300 Sekundenpässe statt eines künstlichen Großpasses. Laufende Produktion und Freight können innerhalb dieser 300 Sekunden mehrfach arbeiten; alte Tests zu einer einzigen Abfahrt oder einem einzigen History-Eintrag wurden an die bestehende dt1-Referenz angepasst. Zeit zwischen externen Spielerkommandos bleibt relevant. Catchup-Aufwand wächst mit Dauer und realer Maschinenzahl; es wird keine konstante Laufzeit für beliebig große Offlineintervalle behauptet. Die reine Unlock-Projektion wurde dafür effizienter, ohne Schwellen zu ändern.

## 4. Exaktes N1 und C2

Produktive Datenquelle: `src/production_zero/data/game_definitions.json`. 353 Produkte, 304 Folgeprodukte, 708 identische Zutatenkanten; 49 unveränderte Primärrezepte, 126 unveränderte Folgeprodukte, exakt 178 normierte Folgeprodukte. Alle Zutatenidentitäten, Zykluszeiten, Rezeptleistungen und Ausbeuten `Input/Output` bleiben erhalten. Flour: **12 Wheat → 12 Flour / 6 s**. Keine N2/N3-Regeln, keine zusätzlichen Handkorrekturen. Maschinen-Kaufbasiswerte bleiben erhalten; konkrete Rezeptmengen stehen in den Produktionsoptionen.

Die einzige aktive Preisrekursion steht in `core/fixed_prices.py`:

```text
Primary = 1
p(output) = sum(a_i * p(input_i)) / q + L_stage * t / (60 * q)
L_Processing=120; L_Fabrication=40; L_Assembly=120; Energieaufschlag=0
```

Topologisch berechnet, ohne Zwischenrundung, alte Mindestanker oder doppelte Vorarbeitszählung. Fehlende/zyklische Inputs, doppelte Produzenten und ungültige Mengen werden abgewiesen. Alle 353 Preise stimmen mit P11-E innerhalb 1e-12 überein; größter absoluter Floatunterschied: 5.68e-14. Der Regressionstest ersetzt alle informativen Katalogpreise testweise durch 1e99 und erhält unverändertes C2: alte Anker sind nicht aktiv. `resource_definitions.json` enthält ebenfalls konsistente C2-Referenzwerte. Der Kompatibilitätsname `LEGACY_BASE_MARKET_PRICES` enthält damit keine aktive alte Preisliste.

Iron/Copper $4, Steel $6,75, Flour/Lumber $2, Bitumen $3, Silicon $4,50, Industrial Equipment $32,4166667, Biodiesel $21,3333333, Microchip $84, AI Server $158,8666667. UI rundet nur die Anzeige; Freight rechnet mit präzisen eingefrorenen Stückpreisen.

Markt, Freight, Umsatz-/Bestandsanzeigen, MK-Quotes, Research-Verkauf, Contracts, Consortium und Tooltips verwenden die zentrale Preisquelle. `price-consumers.txt` dokumentiert die geprüften Lesepfade; 706 Produkt-/Researchzustände prüfen die Resolver zusätzlich. Lifetime und Mastery bleiben Mengenzähler; Efficiency-XP bleibt rekursive Maschinenarbeit und wird nicht fälschlich durch C2-Dollar ersetzt.

## 5. Migration und Bestandsschutz

Die explizite `economy_version=2` ist unabhängig vom unveränderten Zustands-/Infrastrukturschema 9. Alte Payloads ohne Wirtschaftsmarkierung werden deterministisch einmal umgestellt; eine höhere unbekannte Wirtschaftsversion wird abgewiesen. Wiederholtes Laden/Speichern ist idempotent. SQLite legt vor der wirtschaftlichen Umstellung eines v9-Saves eine konsistente `.pre-economy-n1-c2.sqlite`-Sicherung an. Ältere Schema-Backups bleiben bestehen.

Erhalten werden Cash, Warenmengen, Karten/Erwerbs-/Upgradeinvestitionen, MK/Rarity, Research, Company, Lifetime/Unlocks, Historien, Hallen-/Liniengeometrien, beliebig viele Factory Halls, aktiver Contractfortschritt sowie alle eingefrorenen Preise und Belohnungen. Marktdisplay-Snapshots werden auf C2 gestellt; noch nicht angenommene Angebote und abgeleitete Kapazitäts-/Mitgliedspreis-Snapshots werden erneuert. Angenommene Consortium-Verpflichtungen besitzen ihre eigenen unveränderten eingefrorenen Mitgliedspreise. Entfernte Kapazitätssnapshots benötigen nach dem Versionswechsel wieder eine frische Beobachtung.

**Laufende Batches:** Die geprüfte Engine verbraucht Inputs erst beim Abschluss. Vorhandener Zeitfortschritt wird beibehalten, der nächste Abschluss benutzt atomar die neuen N1-Mengen. Es gibt keine vorab gebundenen Inputs zu erstatten. Zwei vorhandene Wheat bleiben zwei Wheat; eine alte fast fertige Flour-Charge wartet unter N1 auf zwölf Wheat, statt Inputs zu erfinden oder zu löschen. Der neue Regressionstest prüft genau diesen Fall. Unterversorgte alte Layouts dürfen korrekt `missing_input` zeigen; ihre Karten und Güter werden nicht entfernt.

16 historische Datenbankslots wurden ausschließlich aus archivierten Kopien normalisiert. Die vollständigen erhaltenen Felder werden per kanonischem SHA256 gegen den gesicherten alten Quellstand geprüft; aktive Contracts, CPG-Werte, Marktzeit und angenommene Consortium-Contracts gesondert. Dann folgen Save/Load und Idempotenz. Alle 16 bestanden. Zusätzlich bestanden fünf persönliche **Backup-Kopien**. Der zweite Durchlauf arbeitet speicherschonend pro Datei, ohne Milliardenzeichen-Historien aller Saves gleichzeitig im RAM zu halten.

Die fünf persönlichen Originale wurden nur gehasht, niemals als Datenbank geöffnet oder migriert. **4255 geschützte Dateien unverändert**, darunter die fünf Originale, alle 4.083 bestehenden Builddateien und die erfassten älteren Berichte/Analysen. Frühere Ergebnisse wurden nicht überschrieben. Neue Versionen laden standardmäßig nur `%LOCALAPPDATA%/Industriova/playtests/economy-rebalance-test/saves/company.sqlite`.

## 6. Reale Ketten, Freight, Energie und Storage

Alle gleichzeitig aktiven Verbraucher werden rückwärts nach Ressource summiert; erst danach werden Vorproduktionskarten aufgerundet. Input-/Outputchargen, Energie, Kartenplätze, Fahrzeuge und Lagerpuffer sind vollständig bezahlt. Überschussrouten entsprechen exakt dem nachhaltigen Überschuss; benötigte Inputs werden nicht mitverkauft. Nach einem festen Hochlauf werden die Routen einmal aktiviert. Keine laufende automatische Laststeuerung und keine Maschinenpausen.

| Kette MK1 | aktive Produktionskarten | MW | gemessene $/min |
| --- | --- | --- | --- |
| iron | 2 | 14.00 | $240.00 |
| copper | 2 | 14.00 | $240.00 |
| flour | 2 | 11.00 | $240.00 |
| lumber | 2 | 11.00 | $240.00 |
| steel | 12 | 96.00 | $1,440.00 |
| bitumen | 2 | 14.00 | $240.00 |
| silicon | 12 | 88.00 | $1,440.00 |
| biodiesel | 8 | 59.00 | $880.00 |
| industrial_equipment | 64 | 516.00 | $6,720.00 |
| microchip | 64 | 532.00 | $7,040.00 |
| ai_server | 84 | 712.00 | $9,120.00 |

Weitere reale Läufe: Iron, Flour, Steel und AI Server bei MK50/75/90/99; drei Speed-Researchfirmen. Für letztere gilt Produktions-MK22 × 1,08 = Freight-MK24; die zusätzlichen Freight-Upgrades sind bezahlt. Dieser gewählte ganzzahlige Vergleich verhindert, dass übergroße Zwischenproduktfrachten den notwendigen Inputpuffer leeren. Research ist als vorverdienter Zustand erklärt. 14.850 separate MK-/Rarity-/Researchfälle prüfen alle 15 Familien und MK1–99 mechanisch; sie sind keine 14.850 gespielten Karrieren.

Alle 30 Kettenzustände liefern in Stunde zwei bei **jeder** Ressource exakt ihre finanzierte Vollrate. Kleinste gemessene Cashquote: 0.999999999999985. Keine `missing_input`-/`storage_full`-/`no_power`-Zustände im stabilen letzten Fenster. Eine zunächst zu kleine hoch-MK-Lagerhülle wurde durch tatsächliche bezahlte Lagerstufen korrigiert; die ursprüngliche Diagnose bleibt als `engine-validation-initial-buffer.csv` erhalten.

Factory, Resources, Energy, Freight und Storage behalten ihre vorhandenen Kostenkurven und lokalen Geometrien. Keine neue globale Ausbaugrenze. Storagepuffer der Vergleichsfirmen decken konservativ reale Chargen/Cargo und sieben Minuten Verkaufsmenge; diese vorfinanzierte Startpolitik ist eine Auditannahme, keine neue Lagerpflicht im Spiel. Bei großen voluminösen Firmen kann sie viel Kapital binden. Die Rangliste beweist deshalb keine optimale Lager-/Dispatchstrategie.

Fuel unverändert: Coal 60/min, Gas 60/min, Nuclear Fuel Assembly 10/min bei MK1. C2-Opportunitätswerte: $60, $60 und $336/min. Das sind entgangene Verkaufswerte, keine zusätzliche Cashabbuchung. Release-Balancing leitet dieselben Brennstoffmengen ab; keine kostenlose Sonderversorgung.

Neue persönliche Vertragsquotes wurden über die tatsächlichen Angebots-/Kapazitäts-/Rewardfunktionen geprüft: 15 Beispiele, Boni 0/20/40 %. Dazu 12 echte Consortium-Preview-/Annahmesnapshots mit Pool 15/25 %. Der Pool wird nicht jedem Mitglied vollständig ausgezahlt. Gefrorene alte Angebote sind durch Migrations- und bestehende Vertragsregressionen geschützt; die gemeinsame persönliche Contractbelegung bleibt erhalten. Kein Vertragsgeld wurde zum gemessenen Markt-Cash der Ketten addiert.

## 7. Neustart, Budgets und Branchen

Acht echte Starts mit $1.250, ursprünglichen acht Karten, Anfangswaren, vorhandener Infrastruktur, tatsächlich bezahlten Kaufkommandos, verdienten Lifetime-Unlocks und realen Freightankünften. Laufzeit jeweils vier Stunden, dt1, kein ausgegebenes RP, kein MK-Upgrade und kein Pause-Controller. Anfangswaren werden nicht als Lifetimeproduktion gezählt. Jeder Messpunkt erfüllt `Cash=1250+Liefererlös−Käufe`.

| Pfad | Cash nach 4 h | bezahlte Käufe | letzte $/min | finale Stufe ab Sekunde |
| --- | --- | --- | --- | --- |
| iron_ore | $29,725.00 | $205.00 | $120.00 | 0 |
| wheat | $29,301.00 | $545.00 | $120.00 | 0 |
| crude_oil | $29,301.00 | $545.00 | $120.00 | 0 |
| iron | $58,117.00 | $205.00 | $240.00 | 60 |
| flour | $57,693.00 | $545.00 | $240.00 | 60 |
| bitumen | $57,693.00 | $545.00 | $240.00 | 60 |
| iron_components | $66,896.00 | $710.00 | $280.00 | 120 |
| copper_wire | $66,876.00 | $710.00 | $280.00 | 120 |

Die erste volle Processing-Stufe wird bei Sekunde 60 nach tatsächlichen 120 Rohstoffeinheiten freigeschaltet; die ersten beiden Fabricationpfade werden bei Sekunde 120 wirklich gekauft/installiert. Diese begrenzte Ausbaupolitik ist keine optimale Karriere.

Die höheren Firmen sind deklarierte, vorfinanzierte Zustände mit zuvor verdienten Voraussetzungen, ohne kostenlose Behauptung eines Genesis-Level25-Starts. Die sechs niedrigeren Kohorten starten tatsächlich auf Level1/5 und verdienen im Lauf weitere Level; die fünf höheren starten auf 25. Alle Supportkarten und kumulierten MK-Quotes werden vom Budget abgezogen. Unterstellte Common-Qualität ist ein Vergleichszustand; zufällige Rarity-Aufwertungen und eine optimale Kartenbeschaffung werden nicht gratis eingerechnet.

| Kapital | Startlevel | Produkt | MK | Investition | reale $/min | Factory-Karten |
| --- | --- | --- | --- | --- | --- | --- |
| $1,250.00 | 1 | iron | 2 | $1,126.25 | $600.00 | 2 |
| $10,000.00 | 5 | steel | 5 | $8,282.96 | $2,160.00 | 4 |
| $50,000.00 | 5 | biodiesel | 10 | $45,502.28 | $9,100.00 | 14 |
| $100,000.00 | 5 | packaged_nutrition | 10 | $99,359.37 | $16,380.00 | 24 |
| $500,000.00 | 5 | packaged_meals | 10 | $453,581.26 | $59,410.00 | 99 |
| $1,000,000.00 | 5 | electrical_cable | 25 | $960,533.42 | $91,840.00 | 84 |
| $10,000,000.00 | 25 | bioplastic | 25 | $9,865,090.76 | $356,160.00 | 288 |
| $100,000,000.00 | 25 | industrial_tires | 75 | $98,795,008.41 | $1,347,840.00 | 384 |
| $1,000,000,000.00 | 25 | grid_storage_system | 90 | $902,447,581.34 | $4,374,720.00 | 1088 |
| $10,000,000,000.00 | 25 | grid_storage_system | 99 | $9,027,525,056.52 | $9,596,160.00 | 2176 |
| $1,000,000,000,000.00 | 25 | commercial_aircraft | 99 | $157,309,690,615.99 | $19,404,480.00 | 3960 |

Alle elf Firmen wurden zwei Stunden tatsächlich simuliert, einschließlich der Firma mit 7.024 Produktionskarten. Die Budgetsuche verwendet 33 Level-/Budgetkohorten mit 345 Domaingewinnerzeilen. Sie vergleicht vollständige Versorgung, Ganzkarten, Solar/Wind und die vorhandenen gemischten Freighttemplates einschließlich MK75/90/99. Bei Level25:

| Budget bei Level 25 | finanzierbare Domains | Domains ≥80 % des besten Musters | best/schwach |
| --- | --- | --- | --- |
| $1,250.00 | 8 | 2 | 4.00 |
| $10,000.00 | 11 | 3 | 1.82 |
| $50,000.00 | 14 | 11 | 1.52 |
| $100,000.00 | 15 | 11 | 1.41 |
| $500,000.00 | 15 | 15 | 1.20 |
| $1,000,000.00 | 15 | 14 | 1.89 |
| $10,000,000.00 | 15 | 13 | 3.31 |
| $100,000,000.00 | 15 | 7 | 6.27 |
| $1,000,000,000.00 | 15 | 8 | 10.17 |
| $10,000,000,000.00 | 15 | 7 | 13.44 |
| $1,000,000,000,000.00 | 15 | 6 | 11.28 |

Mehrere Branchen sind insbesondere im mittleren Spiel konkurrenzfähig. Im sehr hohen Kapitalbereich bleiben erhebliche Abstände. Daraus wird weder universelle Branchenfairness noch ein dominantes globales Optimum behauptet: einheitliche MK, endliches Kandidatenraster, konservative Lager-/Startpolitik, begrenzte Flottenkombinationen und technische Suchgrenzen beeinflussen die Rangliste. **4.096 Factory-/Resourceskarten und 512 Fahrzeuge pro Familie sind Auditgrenzen, keine Spielcaps.** Die größten Muster liegen nahe diesem Rand. Gemischte Firmen, andere Lagerpolitiken und nicht uniforme MK können andere Ergebnisse liefern. C2 wird deshalb nicht nachträglich durch individuelle Produktpreise verändert.

## 8. Vollständige Tests und Windows-Build

**2.758 bestanden, 102 Module, null offene Fehler.** Ausgehend von 1.998 bisherigen Tests kamen 707 Katalog-, 21 MK-, 27 Zeit-/XP- und fünf Migrationstests hinzu. Die komplette Suite lief modular in isolierten Qt-Prozessen. Das nach Erwartungskorrekturen abschließend erneut vollständig ausgeführte Factory-UI-Modul bestand mit 217 Tests. `regression/final-results.json` enthält die zusammengeführten letzten Modulergebnisse, die vorherigen Läufe bleiben nachvollziehbar.

Alle ursprünglichen Testfunktionen sind erhalten; keine Assertionanzahl eines geänderten alten Testmoduls wurde reduziert. `test-preservation-proof.json` und `reviewed-source-test-diff.patch` dokumentieren dies. Geänderte Erwartungen betreffen ausdrücklich N1-Mengen, C2-Verkaufserlöse/Anzeigen, den neuen Savepfad und das korrekte Sekunden-/History-/Versandverhalten statt alter Großtickartefakte. Die Ship/Aircraft-Rundungsprüfung verwendet weiter exakt zwei Cent, jetzt dezimal statt an einer binären Floatgrenze zu scheitern. Keine Tests übersprungen oder als Erfolg umbenannt.

Neue Pipeline: `scripts/build_windows_economy_test.ps1` und `Industriova_Economy_Rebalance_Test.spec`, auf der vorhandenen PyInstaller/PySide6-Pipeline. PyInstaller 6.22.2, PySide6 6.11.1. Eigenes Arbeits-/Cache-/Ausgabeverzeichnis; die bisherige ICU-DLL-Korrektur bleibt enthalten. Erfolgreich gebaut und **zweimal als echte eingefrorene Windows-EXE gestartet**, einmal frisch, einmal mit ihrem isolierten gespeicherten Teststand.

**Build:** `dist/economy-rebalance-test/Industriova_0.3_Economy_Rebalance_Test/Industriova_0.3_Economy_Rebalance_Test.exe`\
**EXE-SHA256:** `e4e7cbd6dbd7e00df2bf6ed258652b4b9f82b3109259b8f8d0c337f2c164b94c`

Der EXE-Smoke prüft: $1.250/acht Karten beim frischen Start, echtes erstes Iron-Processing mit 180 produzierten Einheiten und $288 Liefererlös im Prüfablauf, danach separat synthetisch finanzierten Hallenkauf bis Halle11 ohne Änderung von Halle1, N1-Flour-Anzeige, Iron-/Flour-Preise, echten MK-Dialog mit $68,75, Save/Load und 354 vorhandene Ressourcen-/Research-PNGs. Die synthetische Hallenfinanzierung ist kein Early-Game-Einkommensbeweis. Die vollständigen Rasterprüfungen gehören zusätzlich zur Testsuite. Keine Startup-Exception. Screenshots und beide Launchprotokolle liegen unter `artifacts/phase11fg/exe-smoke-l5comafg`.

Der optionale Smokehook läuft ausschließlich bei ausdrücklich gesetzter Testumgebung und prüft, dass sein Savepfad innerhalb dieses Testordners liegt. Er ist beim normalen Start inaktiv. Zusätzlich bestand ein **uninstrumentierter normaler EXE-Start** in einem weiteren frischen Saveordner: $1.250, acht Karten, eine leere Factory Hall, Wirtschaftsstand2, SQLite-Integrität ok, keine Startup-Exception. Nur dieser isolierte Testprozess wurde danach gezielt beendet; die beiden anderen EXE-Läufe prüften reguläres Schließen und Save/Load. Für die Offscreen-Visualläufe wurden vorhandene Windows-Schriften explizit registriert, da das Offscreen-Qt-Plugin sie nicht zuverlässig aufzählt. Das ist keine neue normale Spielfunktion.

## 9. Reproduktion und offene Grenzen

Aus der Projektwurzel mit der bestehenden Umgebung, jeweils `-B`; alle Ergebnisse gehen ausschließlich nach `artifacts/phase11fg`:

```powershell
.\.venv\Scripts\python.exe -B scripts\phase11fg_sources.py
.\.venv\Scripts\python.exe -B scripts\phase11fg_mk.py
.\.venv\Scripts\python.exe -B scripts\phase11fg_validate.py chains
.\.venv\Scripts\python.exe -B scripts\phase11fg_validate.py xp
.\.venv\Scripts\python.exe -B scripts\phase11fg_validate.py progression
.\.venv\Scripts\python.exe -B scripts\phase11fg_genesis.py
.\.venv\Scripts\python.exe -B scripts\phase11fg_audit.py
.\.venv\Scripts\python.exe -B scripts\phase11fg_migrations.py
.\.venv\Scripts\python.exe -B scripts\phase11fg_regression.py
.\.venv\Scripts\python.exe -B scripts\phase11fg_snapshot.py verify
```

Der Rezept-Anwender `phase11fg_apply_recipes.py` ist absichtlich ein einmaliger, gegen N0 gesicherter Implementierungsschritt; auf einem bereits umgestellten N1-Katalog verweigert er eine zweite Anwendung. Migration ist dagegen ausdrücklich idempotent. Die Regression benötigt weder alte Audittools noch NumPy; unabhängige Referenzen liegen unter `tests/fixtures/economy-n1-c2.json`. Die erweiterten Offlinevergleiche lesen die bisherigen D/E-Werkzeuge und den bereits vorhandenen Audit-NumPy-Pfad unverändert. Ihre Caches ersetzen nur reine Katalogberechnungen, keine Spieltransaktion.

Ein zweiter Build benötigt einen **neuen** Ausgabepfad: das Buildskript verweigert das Überschreiben eines vorhandenen Economy-Testbuilds. EXE-Smokes erzeugen jeweils neue isolierte Unterordner. Die großen historischen Saveprüfungen laufen Datei für Datei; alte Referenzdaten werden nicht überschrieben.

Offene Grenzen: keine global optimale Mehrproduktfirma oder universelle Branchenfairness bewiesen; keine exakt durchgespielte Lebenszeitkarriere; keine kostenlose/optimierte Rarity-Beschaffung; keine globale Fuelportfoliooptimierung. Alte unzureichend dimensionierte Firmen müssen nach N1 gegebenenfalls zusätzliche Vorproduktion kaufen. Hohe MK-/Lagerinvestitionen und sehr große Catchup-Zeiten bleiben echte wirtschaftliche/technische Kosten. Die gezeigten stabilen Stundenfenster beweisen diese konkreten Firmen, keinen unbegrenzten Simulationshorizont. Alle ausdrücklich geforderten Implementierungs-, Test-, Migrations-, Bestandsschutz- und Buildprüfungen sind abgeschlossen.
