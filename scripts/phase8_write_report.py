"""Render the P8 report from accepted local evidence only."""
import json,re
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'artifacts/phase8'
def read(name):return json.loads((O/name).read_text(encoding='utf8'))
sim=read('contract-balance-simulation.json');reg=read('regression-summary.json')
perf=read('performance/comparison.json');progress=read('progression-summary.json')
protection=read('protected-verification.json');visual=read('visual-review.json')
migration=read('migration-after.json');dpi=read('dpi2-regression/results.json')
assert protection['ok'] and migration['passed']==16 and migration['failed']==0
assert len(dpi)==8 and all(r['exit_code']==0 and not r['skipped'] for r in dpi)
assert visual['verified_captures']==66 and visual['profiles_actually_viewed']==6
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(str(v) for v in row)+' |' for row in rows]])
def n(v):return f'{v:,.2f}'
def duration(row):
    if row.get('feasible') is False:return 'nicht verfügbar: '+row['error']
    return n(row['elapsed_minutes'])+('' if row['completed'] else ' (abgelaufen)' if row.get('status')=='expired' else ' (≥, 24-h-Messgrenze)')
single=sim['single_player'];group=sim['consortium']
lookup={(r['stage'],r['mk'],r['kind']):r for r in single['before']['scenarios']}
times=table(['Firma','MK','Art','P7 Minuten','P8 Minuten','P8 Cash','XP','RP'],[
    [r['stage'],r['mk'],r['kind'],duration(lookup[r['stage'],r['mk'],r['kind']]),duration(r),n(r['cash']),n(r['xp']),r['rp']]
    for r in single['after']['scenarios'] if r['mk'] in (1,99)])
xp=table(['Firma MK1','Art','Contract-XP / Spielstunde','Anteil nächstes Level','Contract-RP / Spielstunde','Level-Up-RP im Lauf'],[
    [r['stage'],r['kind'],n(r['xp_per_hour']),f"{r['xp_share_next_level']*100:.2f}%",n(r['contract_rp_per_hour']),r['levelup_rp']]
    for r in progress['scenarios'] if r['mk']==1])
oldgroup={(r['scenario'],r['kind']):r for r in group['before']['scenarios']}
groups=table(['Szenario','Art','Mitglieder','P7 min','P8 min','P8 Summe Cash-Receipts','P8 Bonus vs Basis-Sell'],[
    [r['scenario'],r['kind'],r['members'],duration(oldgroup[r['scenario'],r['kind']]),duration(r),n(r.get('total_receipt_cash',0)),f"{r['bonus_all_receipts']*100:.2f}%" if r.get('bonus_all_receipts') is not None else 'kein Abschluss']
    for r in group['after']['scenarios']])
perform=table(['Operation','P7 Median ms','P8 Median ms','Änderung','P8 Maximum ms'],[
    [r['operation'],f"{r['before_ms']:.3f}",f"{r['after_ms']:.3f}",f"{r['change_percent']:+.1f}%",f"{r['after_max_ms']:.3f}"] for r in perf['results']])
completed=lambda data:sum(r.get('completed',False) for r in data['scenarios'])
late=[r for r in single['after']['scenarios'] if r['stage']=='late']
minmax=lambda kind:f"{min(r['elapsed_minutes'] for r in late if r['kind']==kind):.1f}–{max(r['elapsed_minutes'] for r in late if r['kind']==kind):.1f}"
text=f'''# INDUSTRIOVA 0.3 – P8: Contract & Consortium Balancing

Stand: 22.10.2026. P8 ist implementiert und gegen die vollständige P7-Arbeitskopie geprüft. Neue persönliche Verträge verwenden belegte, wiederherstellbare Kettenkapazität und Daily +20 % / Weekly +40 % Cash. Neue Consortium-Verträge verwenden die tatsächlich nachgewiesenen Firmenleistungen und einen beitragsabhängigen Rewardpool. Bereits angenommene alte Bedingungen bleiben erhalten.

**{reg['passed']}/{reg['tests']} Tests in {reg['modules']} vollständigen Modulen**, alle **1.779 bisherigen Fälle in 91 Modulen** anhand ihrer XML-Testidentitäten erhalten, keine übersprungenen Fälle. **16/16 ursprüngliche historische Migrationen**, zusätzliche Schema-8/9-Fälle und **{sum(r['tests'] for r in dpi)} zusätzliche Prüfungen bei 200 % Qt-Skalierung**. 66 MainWindow-Aufnahmen über sechs Größen-/Skalierungsprofile, repräsentative Bilder tatsächlich angesehen. Native Windows-Handabnahme bleibt offen. Kein P9 und kein neuer Windows-Build.

## 1. Bestehende Contractformeln und Quellen

Vorher ist `artifacts/phase8/before-tree`, die unveränderte vollständige P7-Arbeitskopie; der alte Git-HEAD ist keine Vergleichsgrundlage. Gelesen wurden Technical Audit, Economy Audit, Performance Baseline, Roadmap sowie P6-Bericht, P7-Bericht und P7-Preistabelle unter `docs/industriova-03-*`.

P7 summierte `PV je Einheit × nomineller Output je Minute × Karten-Outputmultiplikator` über konfigurierte Maschinen. Ohne Konfiguration gab es ein aus Kartenzahl/Freischaltungen konstruiertes Minimum von 0,75 PV/min. Budget: `min(Kapazität^0,88 × Zielminuten × Kategoriebonus, Kapazität × Kategorieobergrenze)`, anschließend abgestuft gerundet. Ziele Regular 6/10/16, Daily 25/45/75, Weekly 90/160/260; Vorwärtsfaktoren 1/1,25/1,65. Die verwendete mittlere Schwierigkeit wurde auf 2/3/4 manuell gewählte Produkte in gleichen PV-Anteilen verteilt. Cash bei Annahme war die vorhandene Research-Vertragsquote ohne die neuen +20/+40 %. XP verwendete bereits die unten erhaltene Arbeitswertformel.

Consortium zuvor: lokales PV-Budget `75 + 20 × lokale skalierte Kapazität` bzw. `450 + 90 × lokale skalierte Kapazität`. Produktmengen zusätzlich `Mitglieder^0,72`. Remote-Produktlisten waren Selbstauskunft ohne Produktionsbeleg. Cash-Basis Daily `700+2B`, Weekly `4000+2B`; Company-XP `350+B` bzw. `1500+0,75B`. Alle positiven berechtigten Beiträger bekamen jeweils den gesamten persönlichen Reward; zusätzlich skalierte dieser mit `1+0,35(n^0,72−1)`.

## 2. Nachgewiesene Probleme im P7-Stand

Die nominale Summe berücksichtigte weder verfügbare Inputketten noch Strom, Transporte oder endliches Lager. Zwischen- und Endprodukte derselben Kette wurden gemeinsam als exportierbare Leistung gezählt. Pause und Lagerleerstand senkten die alte Nennleistung bereits nicht direkt; eine pausenabhängige Sofortmessung wäre daher eine neue Manipulationsmöglichkeit gewesen. Die fehlenden Grenzprüfungen waren dagegen real. Ein volles Lager und falsche Lieferziele bleiben Betriebsprobleme: Die neue Quote beschreibt das nach Freiräumen und Umstellen erreichbare Potenzial.

Beim Consortium belegten Simulation und Tests außerdem Remote-Gutschriften ohne Lagerabzug, vollständige Rewardkopien für Kleinstbeiträge, gleichnamige Freight-IDs verschiedener Firmen, stale UI-Ziele und einen nach Save/Load an der alten Network-Instanz hängenden Service. Die neue Aufteilung, Firmenbindung der Belege und dynamische Network-Referenz korrigieren diese Befunde.

## 3. Neue Cash-Berechnung

Eine Preisquelle bleibt maßgeblich: `market_price_for` mit den festen Katalogpreisen. Pro Produkt `p × q × (1 + zulässiger Value-Researchbonus + vorhandener Contract-Researchbonus)`, dann Kategoriebonus. Value- und Contract-Research bleiben wie zuvor additiv. Sell verwendet `p × (1 + Valuebonus)`; vorhandener Contract-Research kann den effektiven Abstand zu Sell zusätzlich erhöhen. Das ist ausdrücklich kein zweites Preissystem.

`contract_reward_quote` ist die gemeinsame Vorschau-/Annahmequote. Preis, Research, Level und Raten werden beim neuen Angebot eingefroren; die vollständige manuelle Auswahl bildet die verbindlichen Mengen und Rewards. Abschluss zahlt nur diesen Snapshot. Reservierte Güter werden beim Versand einmal aus Global Storage abgezogen; angenommene Vertragsware wird nicht zusätzlich verkauft. Überschüsse und veraltete Ziele verwenden den bestehenden Sell-Fallback.

## 4. Daily-/Weekly-Boni

Neue Daily: `round(Research-Vertragswarenwert × 1,20, 2)`. Neue Weekly: `round(Research-Vertragswarenwert × 1,40, 2)`. Ohne Research exakt +20/+40 % gegenüber Sell, abgesehen von Cent-Rundung. Quote-, Forschungs-, Annahme-, Abschluss- und Save/Load-Tests prüfen die tatsächlichen Mengen. Cash/Minute muss gegenüber P7 nicht für jede Kombination steigen, weil sich Mengen und Produktgewichtung ändern; der Bonus vergleicht stets dieselben tatsächlich verlangten Waren mit Sell. Alte bereits aktive Verträge werden nicht nachvergütet oder neu berechnet.

## 5. Regular-Contract-Bewertung

Regular bleibt bei zwei selbst ausgewählten Produkten, ohne neue Levelhürde und ohne Cash-Kategorieaufschlag. Acht konservative Planminuten ersetzen große nominale PV-Ziele. Er bleibt wiederholbar; XP ist der zusätzliche Nutzen gegenüber gleichwertigem Sell, während Daily/Weekly weiter die vorhandenen UTC-Perioden verwenden. Ein Minimum von einer Einheit kann bei sehr teuren Produkten ein kurzes Ziel überschreiten; es wird kein Bruchteil eines Produkts erfunden.

Die Early-Fixture hat vier passende Extractors, reale Solarversorgung und drei Trucks. Zusätzliche Resources-Slots, ein zusätzlicher Extractor, Solarplatz/Karte und dritter Truck verwenden P7-Preise; es wird keine Ein-Truck-Flotte als unveränderte Normalannahme fortgeschrieben. Gegenüber den drei kostenlosen Extractors, einer Solar-Karte und zwei Trucks erfordert diese Fixture 1.365 Cash zusätzliche Anlagen/Slots/Karten; der Startbetrag1.250 reicht allein um115 nicht. Bestehende Startware hat352,20 festen Sellwert und kann diese kleine Lücke finanzieren; Ein separater echter Starter-Engine-Lauf verkauft mit den beiden vorhandenen Trucks nach126 Spielsekunden genügend Startware (192 Cash), ohne Produktion oder Contract-Reward; die Vertragsmessungen selbst erhalten diesen Vorrat nicht. `early-investment-proof.json` bindet die zentralen Preisquotes. Höhere MK bei Early sind gezielte Skalierungstests, keine zum Start finanzierbaren Käufe. Die Firmen sind kontrollierte Ausbaustände mit vorhandenen bezahlten Anlagen; Investitionsrendite und organischer Aufbau werden nicht durch diese Simulation bewiesen. Die ursprünglichen P0-Untergrenzen 570/2.700 Truck-Minuten sind der Anlass für den erneuten Ausbauvergleich, kein aktuelles P8-Ergebnis.

## 6. Erreichbares Kapazitätsmodell

`core/contract_capacity.py` rechnet einen konservativen kontinuierlichen Produktionsplan, keine zweite Spielsimulation. Berücksichtigt werden freigeschaltete vollständige Vorstufen, tatsächliche Karten/MK/Rarity/Research, bereits bezahlte kompatible Plätze, ganzzahlig einschaltbare Maschinen, Strombedarf, endliche Batch-Puffer und effektive Freight-Leistung. Eine unkonfigurierte neue Ware darf vorsichtig eine vorhandene kompatible Maschine umstellen; sie erhält nicht die ganze Maschinenfamilie. Gemeinsam benutzte Maschinenzeit und Inputs werden innerhalb einer Kette addiert. Kraftwerkbrennstoff reserviert dauerhafte Vorproduktion. Geprüfte Betriebsmodi sind unabhängige Energie, alle tatsächlich versorgbaren Brennstoffanlagen sowie je Brennstoff eine sparsame einzelne Anlage. Unversorgbare optionale Anlagen löschen keine funktionierende unabhängige bzw. etablierte Brennstoffkette; überschüssige Brennstoffanlagen müssen nicht gleichzeitig brennen. Ein reiner Brennstoff-Kaltstart braucht historischen Produktionsnachweis oder einen vollständig unabhängig herstellbaren Startbrennstoff. Der begrenzte Modusvergleich bleibt konservativ und ist keine exponentielle Kraftwerksoptimierung.

Für Produkt i sind `r_i` die nachhaltige Rate und `p_i` der feste Preis. Einzelspieler: `r_i = min(Kettenrate_i, gesamte Freight-Menge/min)`. Für die gewählte Kombination und Ziel T gilt `V = T / Σ[1/(r_i p_i)]`, `q_i = max(1, floor(V/p_i))`. Jedes Produkt erhält denselben Warenwert, alle ausgewählten Produkte teilen dieselbe konservative Zeitreserve. Dadurch werden Zwischenprodukte und ihre Weiterverarbeitung nicht doppelt versprochen. Unabhängige Ketten können tatsächlich parallel schneller sein; Anlauf, Batchgrößen und Lieferwege können langsamer sein.

Pause, aktuelle Warenmengen, Routenziel und Tickfortschritt sind keine Quoteingaben. Kapazitätsänderungen durch echte Anlagen-/Konfigurations-/Research-/Lager-/Freischaltungsänderungen invalidieren neue Angebote. Bereits aktive Snapshots bleiben unverändert. Historischer Brennstoffnachweis beschreibt einen etablierten Betrieb; realer Restart kann trotzdem einen endlichen Brennstoffvorrat benötigen. Die UI erläutert Wiederaufnahme, Konfiguration, Lagerfreiraum und Routenzuweisung als Betriebsannahmen.

## 7. Früh-/Mittel-/Spätspielzeiten

45 Szenarien je Version: drei Firmenstände × MK1/2/10/50/99 × Regular/Daily/Weekly. Early wählt Primärgüter; Mid Iron/Copper/Steel/Steel Components; Late Industrial Equipment/Cargo Aircraft/High Speed Network System/Steel Components. Early 3 Trucks; Mid 4 Trucks + 2 Trains; Late 4 Aircraft + 2 Ships, jeweils tatsächlicher MK. Endliche Lager werden aus einem zehnminütigen Vorstufenpuffer mit der vorhandenen Upgradeformel dimensioniert; Level, Kapazität und Investition stehen je Lauf im JSON. Rezepte sind nur soweit für die Fixture explizit freigeschaltet, keine automatische Freischaltung im Spiel.

Echte Engine, sechs Sekunden je Schritt, feste UTC-Startzeit 22.10.2026 14:14:20, maximal 24 Spielstunden bzw. realer Ablauf. Startware 0,001 je auswählbarem Produkt dient nur der alten Eligibility, keine Nachfüllung. Alle Inputs entstehen in realen Maschinen. Dieselbe deterministische manuelle Routingregel reserviert vorhandenen Bestand je vorgeschlagenem Fahrzeug, in sortierter Kartenreihenfolge; geforderte Vorprodukte werden erst nach ihren geforderten Nachprodukten exportiert. Produktionspuffer werden durch Pausieren begrenzt.

{times}

P7 schließt {completed(single['before'])}/45, P8 {completed(single['after'])}/45 in diesem Messfenster ab. Spätes Daily liegt über MK1–99 bei {minmax('daily')} Minuten, Weekly bei {minmax('weekly')} Minuten. 60/240 Minuten sind Kalibrierungsgrößen, keine Fristen oder Garantien. Abweichungen durch zusammenhängende Ketten, Serienbudget, Transportrundungen und Ramp-up werden als gemessene Abweichung beibehalten. Das JSON trennt nominelle direkte Outputzeit, erreichbares serielles Produktionsbudget, kontinuierliche Freight-Untergrenze und tatsächliche überlappende Abschlusszeit. Reale Routenoptimierung kann andere Werte ergeben. Ein pauschaler zusätzlicher Zeitmultiplikator allein aus den späten Laborfällen wurde bewusst nicht eingeführt: Er würde bereits kurze unabhängige Früh-/Mittelketten zusätzlich verkürzen. Die nächste Kalibrierung sollte echte Produktkombinationen und Routeentscheidungen vergleichen, bevor späte Ziele gesondert reduziert werden.

## 8. XP-/RP-Entwicklung

Arbeits-PV bleibt der rekursive Rezeptwert des vorhandenen `ProductionValueCalculator`. Company-XP bleibt `20 × sqrt(max(1,ArbeitsPV)) × [1+ln(1+Level)/4] × Kategorie(1/2/4)`, auf Cent gerundet und eingefroren. Keine neue XP-Multiplikation. Die Levelanforderung ist vor Level100 `500+125L+18L²`, danach `250000+9000(L−99)+450(L−99)²`. Die prozentualen Anteile beziehen sich auf die nächste Levelanforderung beim eingefrorenen Angebotslevel; Produktions-XP kann das tatsächliche Endlevel während der Lieferung erhöhen (separat im JSON). Die relative Quote kann deshalb spät sinken; eine isolierte synthetische Firma rechtfertigt keine pauschale globale Progressionsbeschleunigung.

{xp}

Daily 1 RP und Weekly 3 RP bleiben erhalten; Level-Ups vergeben weiter vorhandene RP. Bestehende Produktions-XP bleiben unverändert: Kontinuität40/min bis1.200/UTC-Tag, Nachholbank bis3.600, vier Effizienzstufen mit je500/Tag sowie einmalige Erstproduktions-/Familienbelohnungen. Die Labor-RP aus frühen Level-Ups sind deshalb nicht unbegrenzt pro identischem neuen Lauf wiederholbar. Katalog: {progress['nodes']} Research-Knoten mit {progress['node_rp_total']} RP, zusätzlich {progress['specialization_slots']} bestehende Spezialisierungsplätze mit {progress['specialization_rp_total']} RP. Das ist eine Katalogsumme, kein Anspruch auf jede gleichzeitig zulässige Belegung. Ein täglicher persönlicher Daily plus ein Weekly pro Woche liefert rechnerisch zehn Contract-RP/Woche; Level-Up-RP und bestehende Consortium-RP kommen hinzu. Eine Wiederholungsrate aus Regular oder Consortium darf nicht als zusätzliche persönliche Daily-Resetfrequenz gelesen werden. Alle 45 Fortschrittswerte, XP/Spielstunde, Anteil am nächsten Level und RP aus tatsächlich beobachteten Level-Ups stehen in `progression-summary.json`. Organisches Langzeit-Research und reale menschliche Spielstunden bleiben Playtestbedarf.

## 9. Vollständiger Consortium-Audit

Vorhanden bleiben lokale Netzwerkdaten, Mitgliedschaft, Open/Application/Invite-only, Chairman/Board Member/Member, Mindestlevel, Bewerbungen, Einladungen, Transfer, Ausschluss und Auflösung. Start/Erneuerung verlangen weiter Management; gewöhnliche Mitglieder dürfen beitragen. Beim Start eingefrorene Mitglieder bestimmen Rewardberechtigung; spätere Mitglieder können Ware beitragen, erhalten für diesen alten Vertrag keinen Reward. Austritt/Ausschluss verfällt bestehende Berechtigung, Wiedereintritt hebt dies nicht auf. Chairman-Wechsel verändert keine Vertragsbedingungen.

Die vorhandene Obergrenze bleibt 50; Freigaben: Level1→10, 5→15, 10→20, 15→25, 20→30, 30→40, 40→50 Mitglieder. Daily/Weekly haben weiter 3/4 manuelle Produkte und 24 Stunden/7 Tage Laufzeit ab Angebot. Bestehende Wiederholbarkeit bleibt; NEW CONTRACT macht nur die vorhandene Rotation nach Abschluss/Ablauf erreichbar. Historie40 und Aktivitätsliste100 bleiben begrenzt. Consortium-XP und Profil-/Leaderboardbezüge bleiben im vorhandenen System. Historische Lebenszeitbeiträge bleiben Stückzahlen und werden nicht rückwirkend in Warenwert-Ränge umgerechnet; die neue Rewardverteilung verwendet dagegen eingefrorenen Warenwert. Es gibt weiterhin keinen freien Manager-Abbruch eines aktiven Gemeinschaftsauftrags: Ablauf bzw. Auflösung und Mitgliederaustritt gelten nach den bestehenden Regeln, bereits gespendete Ware wird nicht zurückgegeben.

Dies ist ein lokaler autoritativer Stub mit bestehenden Remote-Identitäten, kein neu gebauter Multiplayer-Server. Remote-Kapazität muss über `update_capacity_snapshot(company_id, actual_company_state)` von einer authentifizierenden Server-/lokalen Instanz kommen. Fremde Namen, Level und deklarierte Produktlisten erzeugen keine Leistung. Remote-Leistungsbelege sind für neue Angebote höchstens24 Stunden gültig; kurze Pause reduziert die Quote nicht. Aktive Verträge werden beim Veralten nicht geändert. Remote-Reward-Receipts sind bestehende haltbare Ansprüche; die Engine zahlt automatisch nur dem jeweils lokalen Firmenwallet. Neue Online-Abholung/Settlement ist nicht implementiert und wird von den Simulationen nicht behauptet.

## 10. Consortium-Mengen und Skalierung

Pro Produkt werden ausschließlich belegte Kettenraten der einzelnen Firmen addiert. Spezialisierte Firmen liefern nur ihre unterstützten Produkte; unbekannte/alte Remote-Firmen tragen null Planleistung bei. Kein `lokale Menge × Mitgliederzahl`. Ziele: Daily120, Weekly480 konservative Planminuten mit derselben Serien-Warenwertformel.

Wesentliche Besonderheit: Das bestehende Consortium darf Global Storage direkt abbuchen. Seine Mengenbasis muss daher Produktionsleistung sein, auch wenn die Freight-Flotte absichtlich schwach ist. Eine künstlich winzige Freight-Quote wäre über direkte Abgabe ausnutzbar. Ohne Freight bleibt der direkte vorhandene Lieferweg möglich; ein reiner Freight-Lauf ohne Fahrzeuge darf dagegen nicht als erfüllbar ausgegeben werden. Schwache Flotten können anspruchsvolle Produktionsziele ohne zusätzlichen Ausbau verfehlen. Es gibt keine kostenlose Transportkarte und keine neu erfundene Route.

## 11. Mitgliedsbeiträge und Rewards

Neue Daily reservieren maximal `1,15 × eingefrorener Sell-Warenwert`, neue Weekly `1,25 × Sell-Warenwert`. Das sind eigenständig geprüfte Kandidaten mit geringerem Cashaufschlag als die zeitlich begrenzten persönlichen +20/+40 %, weil Consortium-Aufträge wiederholbar sind und Consortium-XP vergeben. Die maximale Poolreserve verwendet je Ware den höchsten belegten Mitglieds-Sellpreis. Jede Firma erhält ihren tatsächlich eingebrachten eingefrorenen Research-Sellwert als Anteil an dieser Reserve, auf Cent abgerundet. Ergebnis: eigener eingebrach­ter Sellwert ×1,15/1,25 innerhalb der Rundung, ohne Researchgewinn durch bloßes Umschichten an eine andere Firma.

Company-XP-Pool verwendet die eingefrorene Arbeitswert-/Kategorie-/Erstellerlevelquote. Aufteilung nach festem Basiswarenwert des eigenen Beitrags; Value-Research vergrößert nicht den XP-Anteil. Bei gleich starken größeren Gruppen kann die persönliche XP-Quote wegen des gemeinsamen konkaven Work-XP-Pools sinken. Cash bleibt proportional zum eigenen Warenwert und qualifizierende Weekly-RP bleiben pro Firma; die lineare Gruppen-XP fördert den gemeinsamen Ausbau. Diese Gewichtung gehört ausdrücklich in den Gruppen-Playtest. Nullbeitrag, nicht beim Start berechtigt oder ausgeschieden: keine Auszahlung. Verfallene Anteile bleiben unbezahlt und werden nicht auf verbleibende Firmen umverteilt. Gruppen-XP einmalig `400+ArbeitsPV` / `1750+ArbeitsPV`.

Das bestehende Weekly-1-RP bleibt mit einer kleinen belegten Anforderung erhalten: mindestens die Hälfte des bei Start aus der Produktleistung erwarteten Basiswarenwertanteils. Stock-only/unknown Beiträger verwenden die Hälfte des kleinsten positiven belegten Anteils. So erhalten schwache echte Firmen eine angemessene Schwelle; ein symbolisches Korn oder zusätzliche Geistermitglieder klonen keine RP. Die Schwellen sind Teil des Snapshots. Alte aktive Version0-Verträge behalten ihre vollen ursprünglichen persönlichen Rewards einschließlich RP.

## 12. Sicherheits- und Exploitbefunde

Direkte Beiträge prüfen endliche positive Menge, Mitgliedschaft, Vertrags-ID/Status/Ablauf, benötigte Ware, Restmenge, tatsächliche Quellenidentität und endlichen vorhandenen Lagerbestand vor Abbuchung/Gutschrift. Remote-Abgabe ohne tatsächlichen Quellzustand ist verboten. Freight nimmt nur die Restmenge; überschüssige, verspätete, abgeschlossene, entfernte oder abgelaufene Ziele gehen über die vorhandene Engine nach Sell. Die zentrale P5/P6-Abrechnung und Istlieferstatistik wurden nicht umgangen.

Request-/Freight-Belege enthalten eine eindeutig JSON-kodierte Kombination aus Firmen-ID und Request-ID. Damit unterdrückt `outbound-1` von Firma A nicht mehr die rechtmäßige Lieferung derselben lokalen ID von Firma B. Alte unzuordenbare rohe Belege werden konservativ weiter anerkannt. Abschlussstatus, persönliche Belege und Consortium-XP-Flag verhindern doppelte Auszahlung auch über Save/Load. Rotations-IDs binden Signatur/Zeit/Seed/Sequenz und vermeiden aktuelle, historische, quittierte und noch unterwegs referenzierte IDs.

UI-Start und Beitragsdialog verwenden die tatsächlich angezeigte Vertrags-ID. Veraltete Ziele erzeugen eine verständliche Aktualisierung ohne Warenverlust. Persönliche UI-Annahme übergibt zusätzlich die angezeigte Cash-/XP-Quote. Der Service folgt nach Laden dem neuen Network und verwirft alte Vorschaucaches. Die vorhandene Reward-Receipt-Liste bleibt absichtlich vollständig: sie ist ein dauerhaftes Anspruchsledger und kann über lange Spielzeit wachsen. Eine automatische Kürzung würde bestehende Ansprüche verlieren; dies wird nicht als konstante Speicherbelegung ausgegeben. Gleichzeitigkeit ist die bestehende sequenzielle Engine/Event-Schleife, keine Behauptung einer neuen verteilten Datenbanktransaktion.

## 13. Formeln und Konstanten

| Größe | Neue Regel |
| --- | --- |
| Balanceversion | 1 für neue Angebote, 0 für historische Snapshots |
| Persönliche Planzeit | Regular8 / Daily60 / Weekly240 Minuten |
| Persönliches Cash | Faktor1 / 1,20 / 1,40 auf vorhandene additive Research-Vertragsquote |
| Persönliches RP | 0 / 1 / 3, unverändert |
| Consortium-Planzeit | Daily120 / Weekly480 Produktionsminuten |
| Consortium-Cash | eigener eingefrorener Sellbeitrag ×1,15 / ×1,25, gemeinsamer Maximalpool |
| Consortium-Weekly-RP | bestehend1, ab halbem belegten erwarteten Beitragsanteil |
| Remote-Belegalter | höchstens86400 Sekunden für neue Angebote |
| Persistenzschema | 9; P7 war8 |

Alte PV-Konstanten bleiben für historische Version0-Angebote und kompatible Hilfsfunktionen erreichbar; sie sind nicht die neue Mengenformel. Neue Version1-Angebote verlangen eine vollständige explizite Auswahl, keine zufällige Ergänzung fehlender Slots.

## 14. Alte und neue Wirtschaftssimulationen

34 Consortium-Szenarien je Version, jeweils Daily/Weekly: 1/2 kleine, 5 mittlere, 10 starke Firmen, gemischt starke Firmen, fehlende Freight, einzelne fehlende Energie, starke Produktion mit Startertrucks, physisch getrennte Spezialisierung, Austritt nach zehn Minuten, direkte Warenabgabe sowie komplexe Endprodukte/gemischte Ketten. Vor der Quote wird bei der mittleren Weekly-Fixture ein tatsächlich vorhandener mehrfach belegter Ore-Extractor manuell auf die bereits freigeschaltete Bauxite-Produktion umgestellt; keine Karte und kein Unlock wird hinzugefügt. Spezialisierte Firmen behalten ausschließlich ihre echten eigenen Maschinen. Echte Engine pro Firma mit gemeinsamem lokalen Network, 30-Sekunden-Rundläufe, dieselben endlichen Lager-/Pufferannahmen. Verlassene Firmen laufen für reservierte Sell-Fallback-Ladung weiter; Restflüge werden nach Abschluss/Ablauf bis zu600 Sekunden abgewickelt. Diese Ausläufe zählen nicht als Vertragsabschlusszeit. Das30-Sekunden-Dispatchraster erzeugt zusätzliche Batch-/Wartezeit gegenüber dem feineren6-Sekunden-Einzelspielerlauf, besonders bei Trucks. Absolute Zeiten beider Matrizen sind daher nicht tickgenau gleichzusetzen; der jeweilige Vorher-/Nachher-Vergleich verwendet dasselbe Raster. Feinere Gruppen-Zeitschritte und menschliches Routing bleiben weitere Kalibrierung.

{groups}

Abgeschlossen P7 {completed(group['before'])}/34, P8 {completed(group['after'])}/34 innerhalb des Fensters. Absichtlich fehlende Freight, schlechte Flotten und Austritt können nicht abgeschlossene Fälle erzeugen; die Tabelle kennzeichnet sie. Direkte Läufe messen den vorhandenen schnelleren Lieferweg mit real erzeugtem Lagerbestand und ohne menschliche Klickverzögerung. Gutschriften aller Firmen stehen als Receipts, tatsächliche Wallets separat. Direkte Beiträge können bei knapper Freight deutlich mehr Cash je Spielminute liefern als Freight-Verkauf: Sie umgehen bereits im bestehenden System den Transport und verlangen manuelle Auswahl, Start und Warenabgabe. Die Simulation nimmt dabei null menschliche Verzögerung an. Die niedrigeren15/25-%-Aufschläge beseitigen diesen aktiven Transportvorteil nicht; er bleibt ein ausdrücklicher wirtschaftlicher Playtestpunkt. Es wurde weder eine neue Pflicht-Freight-Rolle noch ein neuer Cooldown oder automatischer Start eingeführt. Bei ausreichend ausgebauter Flotte begrenzt wieder die Produktion; passiver Sell und persönliche20/40-%-Quoten bleiben andere vorhandene Spielwege. Verfallene Beiträge senken die Gesamtauszahlung; deshalb muss der Gruppen-Gesamtbonus dann nicht +15/+25 % betragen. Pro Beitrag bleibt die eingefrorene persönliche Quote verbindlich.

Maschinenlesbare vollständige Anforderungen, Warenwerte, nominelle/erreichbare Produktionszeit, effektive Freight-Grenzen, Energie, Minutenerträge, Mengen, Istfortschritt, Einzelreceipts, Level/RP, Lagerpeaks, nichtnegative Bestände und Roundtripchecks: `artifacts/phase8/contract-balance-simulation.json`. Die früheren `candidate*`, `*-final`, `*-reproduced`, `consortium-final` und Diagnoseordner bleiben erhalten, gehören aber nicht zum akzeptierten Vergleich. Sie dokumentieren unter anderem die gefundene firmenübergreifende Freight-ID-Kollision und die zu schwache Quote vor Berücksichtigung direkter Abgabe. Für die akzeptierten vollständigen Engine-Matrizen wird ausschließlich im Offline-Harness der unveränderliche Company-XP-Rezeptwertgraph wiederverwendet (`phase8_offline_work_cache.py`). Alle353 Werte werden zuvor exakt verglichen; Übergänge, Zeit, Waren, Inputs und Rewards bleiben echte Engine. `offline-cache-equivalence.json` belegt zusätzlich die Gleichheit aller45 vollständigen P8-Ergebnisse mit dem zuvor fertig gerechneten Lauf ohne Hilfscache und der bereits ausgerechneten P7-Teilergebnisse. Der frühere langsame Referenzlauf wurde für diesen Harnesswechsel gestoppt; `before-matched-interrupted.log` bleibt Diagnose, der akzeptierte P7-Vergleich rechnet alle45 Fälle neu. Simulations-CPU-Laufzeit ist keine Wirtschaftsdauer oder Performancezahl. Der separate Benchmark prüft ausdrücklich, dass der Company-XP-Konstruktor die unveränderte Produktionsklasse und kein Hilfscache ist.

## 15. Save, Snapshot, Migration und Sicherung

Vor Änderungen: Sicherung `artifacts/phase8/backup-20261022T133551Z`, 57.017 Dateien /31.815.983.024 Bytes, Delta214.912.808 und unabhängiges Quellarchiv127.133.653 Bytes, beide CRC-geprüft. SHA256-Manifest mit intakter P7→P0-Kette; fünf persönliche Saves als Rohkopie und konsistentes SQLite-Backup, jeweils integrity_check=ok. Wiederherstellen in einen neuen Ordner nach Manifest; alte Archive sind gebundene Abhängigkeiten und bleiben erhalten.

Schema9 ist nötig, damit ein alter Schema8-Reader den neuen gemeinsamen Pool nicht als vollständige Belohnung pro Mitglied auszahlt. SQLite legt für Quelle≥8 eine separate `.pre-industriova-v9.sqlite` an und überschreibt keine vorhandene v8/v7/v5-Sicherung. Downgrade benötigt passende Vorher-Quelle und Vorher-Save; keine automatische Rückkonvertierung. Neue Snapshotfelder betreffen Raten, Preise/Research, Level, RP, Mitgliedspreise und Beitragsschwellen. Private berechnete Caches werden nicht gespeichert und sind aus dem fachlichen Dataclass-Gleichheitsvergleich ausgeschlossen; das erhält die atomaren Inventory-Prüfungen auch nach einer internen Kopie.

Alle16 historischen Payloads zunächst vollständig gegen final P7 bestätigt, danach Schema9 idempotent geladen/gespeichert. Nach Entfernen ausschließlich neu ergänzter Defaultfelder und Normalisierung der Schemanummer ist der gesamte historische Geschäftsinhalt SHA256-identisch; historische Balanceversion bleibt0. Alte angenommene Mengen, Rewards, Beiträge, Belege und Rechte bleiben erhalten. Noch verfügbare persönliche Version0-Angebote behalten ihre bisherigen PV-Mengen bis zur normalen Rotation; eine neue Annahme bindet die aktuelle angezeigte Cashquote mit Kategoriebonus. Verfügbare alte Consortium-Angebote werden vor neuem Start durch eindeutig neue Version1-Angebote ersetzt; bereits aktive bleiben unangetastet. Neue Tests prüfen außerdem echte Schema8-Dateien und die separate v9-Sicherung. Abschließend **{len(protection['protected'])} geschützte Bestandsdateien und alle fünf persönlichen Original-Saves SHA256-unverändert**. Katalog, Ressourcen, Rezepte, Research, MK, P7-Infrastrukturpreise, SimulationEngine und bestehende Builds bleiben unverändert.

## 16. Performance-Vergleich

Serielle Vorher-/Nachher-Messung ohne gleichzeitige Tests, Simulationen oder Hashprüfung: 353 vorhandene Produkte, 500 konkrete Karten, zehn Mitglieder, identische UI-Schriften/Fixture, Qt offscreen100 %, sieben rohe Einzelmessungen je Operation. Die zusätzliche500-Slot-Halle ist ausdrücklich ein synthetischer Lasttest jenseits normaler Gebäudemaße. Median, Maximum und rohe Werte liegen unter `performance/before-matched`, `after-matched` und `comparison.json`.

{perform}

Neue Kettenplanung läuft nur bei Angebotsgenerierung bzw. dauerhaften Änderungen; kein Engine-Tick pro Paint. Unveränderte UI-Signaturen überspringen den Neuaufbau. Der unveränderliche rekursive Arbeitswertgraph wird je Definitionsidentität wiederverwendet; Austausch von Definitionen, New Game und Load verwerfen passende Caches. Lager/Rewards werden nicht global gecacht. Die Auswahlquote sinkt von17,13 auf1,18 ms, die unveränderte persönliche Ansicht von47,95 auf4,65 ms und20 Tabwechsel von1.296 auf788 ms. Dagegen steigt die Neuberechnung nach Kapazitätsänderung von1,73 auf24,24 ms, Annahme von18,65 auf34,26 ms, warmer Tick von4,01 auf5,23 ms und Save von21,95 auf48,17 ms. Das Snapshot-Payload wächst in dieser353-Produkte-/10-Mitglieder-Fixture von438.207 auf836.519 Bytes durch unveränderliche Raten-/Preis-/Researchdaten. Die unveränderte Consortium-Ansicht steigt von0,05 auf1,32 ms. Ersttick maximal47,63 ms, Speichern maximal50,31 ms; kalte Zustandswechsel können somit einzelne Frames kosten. Es wird keine allgemeine Performanceverbesserung oder native60-FPS-Garantie behauptet. Kaltstart und Annahme nach Load sind teurer als warme Abfragen; Unterschiede und Maxima stehen ausdrücklich in der Tabelle. Millisekunden im synthetischen Offscreenlauf beweisen weder native FPS noch jedes reale Gerät.

## 17. Neue Testfälle

74 neue Corefälle in `test_phase8_contract_balance.py`, 16 echte UI-Fälle in `test_phase8_contract_ui.py`: Boni mit/ohne Research, exakte Vorschau/Annahme/Auszahlung, vollständige manuelle Auswahl, Ketten/Strom/Lager/Freight/MK, Brennstoffbootstrap, Zwischenproduktbudget, Pause/Leerstand/Route-Anti-Reroll, Cacheinvalidierung, alte Snapshots, Schema8/9, nichtendliche Eingaben, 1/2/5/10/50 Mitglieder, tatsächliche Belege/Spezialisierung, Wert-/XP-/RP-Aufteilung, Rechte/Wechsel/Austritt, echte Remote-Quellabbuchung, Namensraumkollisionen, Expiry/Fallback/P6-Istzählung, doppelte Ereignisse, Stale-Ansichten, Rotation und Network-Neubindung. Große Mengen und signed32bit-Grenzen sind separat geprüft.

## 18. Vollständige Regressionsergebnisse

Finaler vollständiger Lauf: **{reg['passed']}/{reg['tests']}**, {reg['modules']} Module, {reg['failures']} Fehlerfälle, {reg['errors']} Laufzeitfehler, {reg['skipped']} übersprungen. `final-regression/results.json`, einzelne Logs und XML sind die akzeptierte vollständige Regression; Vorläufe bleiben als Diagnose erkennbar. `regression-summary.json` vergleicht die Multimenge `(classname, testcase-name)` aller91 P7-Module: 1.779/1.779 erhalten. Vorhandene fachliche Erwartungen wurden nur für die autorisierten Boni, reale Kapazitätsfixtures, explizite Auswahl, Schema9 und proportionale Consortium-Rewards angepasst; keine alten Fälle entfernt oder übersprungen.

Zusätzlich acht vollständige relevante Core/UI-Module bei200 %: {sum(r['tests'] for r in dpi)} Fälle, alle bestanden; Drag/Swap, Freight, P6-Statistik, P7-Economy und P8 bleiben abgedeckt. Der zuletzt gefundene optionale Brennstoff-Randfall ergänzt vier Fälle in zwei Betriebsmodi. Die gesamte Regression wurde anschließend erneut gerechnet. `optional-fuel-solar-equivalence.json` bestätigt für alle15 Solar-Fixturen einschließlich MK1/2/10/50/99 die vollständige Gleichheit des alten und finalen Kapazitätsplans; die ausschließlich mit Solar bestückten Matrizen und gesichteten Bilder behalten dadurch ihre Quoten. Alte von Tests neu erzeugte Screenshotdateien wurden aus der Backupkette restauriert und frische Versionen unter `phase8/legacy-test-captures` erhalten. `protected-verification.json`, `implementation.diff` und `final-source-sha256.json` binden den geprüften Stand. Tests ändern keine persönlichen AppData-Saves.

## 19. Visuelle Abnahme

66 tatsächlich erzeugte und als `screenshots-accepted` erhaltene MainWindow-Captures: 1366×768,1600×980,1920×1080 bei100 % und200 % Qt-Skalierung. Je Profil elf Zustände: persönliche Auswahl/Annahme/Teillieferung/Großmengen/Abschluss sowie Consortium-Auswahl/Annahme/Teillieferung/Großmengen/Abschluss/Ablauf. Cash/XP/RP, lange Produktnamen und Fortschritt wurden über alle sechs Profile anhand repräsentativer finaler Bilder angesehen; `visual-review.json` nennt die tatsächlich betrachteten Dateien und SHA256. Alle66 Pixelmaße und Dateihashes sind geprüft. Sichtbare Scrollbereiche sind vorhanden, kein Anspruch, jede Zeile gleichzeitig in768 Pixel Höhe zu zeigen.

Die erste Bildkontrolle fand abgeschnittene große Mengen und einen int32-Überlauf des Consortium-Fortschritts. K/M/B/T-Anzeige, zwei Mengenzeilen, exakte Tooltip-/Accessibilitywerte und auf0–1000 normalisierte Progressbar korrigieren dies. Cash/XP zeigen kompakte Zahlen mit exakten gebundenen Werten. Der native Beitragsspinboxbereich begrenzt nur eine einzelne Eingabe auf2.147.483.647, die Summary erklärt dies; weitere Beiträge und größere Backendmengen bleiben möglich. Stark vergrößerte Zahlen und künstliche Statuswechsel sind isolierte Darstellungsfixtures, keine verdienten Ökonomiewerte. Theme/Navigation bleiben im bestehenden Stil.

## 20. Offene Fragen für den späteren Playtest und Stopp

Organisch erspielte Firmen, echte Routenentscheidungen, begrenztes Kapital, Betriebsunterbrechungen, Brennstoff-Neustart und Langzeit-Research müssen weiter gespielt werden. Besonders die gemessene späte Daily-/Weekly-Dauer, erreichbare RP-Beitragsschwellen ungleicher Firmen und die wiederholbaren Consortium-Quoten sind Playtestpunkte. Das bestehende lokale Remote-Settlement und langfristiges Receipt-Wachstum sind dokumentierte technische Grenzen. Native Windows-Handabnahme mit realem Fenster, Maus und DPI-Wechsel bleibt offen.

P8 endet hier. Kein Tutorial, keine P9-Navigation, keine neue Ressource/Rezepte/Researchbäume/Rollen, keine neue Marktökonomie, keine neuen Freight-MK- oder Infrastrukturpreisformeln. Persönliche Saves und bestehende Builds wurden geschützt; kein Windows-Build erstellt.

### Reproduktion und Evidenz

Mit `.venv/Scripts/python.exe` aus dem Repository: `scripts/phase8_final_validation.py` führt vollständige Regression, die vier `*-matched`-Simulationen, Migration, Captures und serielle Benchmarks aus. Die finale200-%-Suite mit acht vollständigen Modulen steht unter `dpi2-regression`. `scripts/phase8_evidence_summary.py` prüft XML-Retention und Szenarioinvarianten und erstellt die kombinierte Tabelle. Nach tatsächlicher Bildsichtung: `phase8_preserve_legacy_outputs.py`, `phase8_verify_protected.py`, `phase8_write_report.py`. Bilder werden mit `phase8_capture.py` je `QT_SCALE_FACTOR=1/2` erzeugt (für den gesichteten Satz zusätzlich `PHASE8_CAPTURE_ROOT=artifacts/phase8/screenshots-accepted`), niemals durch persönliche Saves. `final-validation-queue.json` protokolliert Exitcodes; Testergebnisse werden zusätzlich ausgewertet, weil der Modullaufrunner selbst keine Fehler-Exitcodes aggregiert. `delivery-manifest.json` bindet abschließend Quellen, Tests, Werkzeuge, Bericht und akzeptierte Belege mit SHA256.
'''
# Keep identifiers/formulas in inline code intact while spacing German prose.
readable=[]
for line in text.splitlines():
    if not line.startswith('|'):
        parts=re.split(r'(`[^`]*`)',line)
        for index in range(0,len(parts),2):
            parts[index]=re.sub(r'\b(alle(?:r|n)?|bei|in|auf|bis|von|zu|mit|nach|vor|ab|am|je|und|bzw|das|die|der|des|als|nur|rund|etwa|mindestens|höchstens|maximal|zusätzlich|weitere|Level|Version|Schema|Daily|Weekly|Regular|Historie|Aktivitätsliste|Kontinuität|Firmenlevel|Startbetrag)(?=\d)',r'\1 ',parts[index],flags=re.I)
            parts[index]=re.sub(r'(?<=\d)(RP|XP|Minuten|Sekunden|Spielsekunden|Spielstunden|Tabwechsel|Fälle|Mitglieder|Karten|Trucks)\b',r' \1',parts[index])
        line=''.join(parts)
    readable.append(line)
text='\n'.join(readable)+'\n'
examples=f"Bildbeispiele: [Vertragsmengen bei 1366×768 / 100 %](<{R.as_posix()}/artifacts/phase8/screenshots-accepted/dpi1/contracts-large-numbers-1366x768.png>), [Consortium-Großmengen bei 1600×980 / 200 %](<{R.as_posix()}/artifacts/phase8/screenshots-accepted/dpi2/consortium-large-numbers-1600x980.png>).\n\n"
text=text.replace('## 20. Offene Fragen',examples+'## 20. Offene Fragen')
(R/'docs/industriova-03-phase8-contract-balance-report.md').write_text(text,encoding='utf8')
print('report written',len(text))
