"""Auditable classification of the reference failures and test modernization."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path('artifacts/industriova-stabilization')
REASONS = {
    'test_card_definitions.py': 'A: Freigegebene Brennstoffrelation: Gas 60/min, Kernkraft 10/min; unveränderte Leistungs- und Leerzustandsprüfungen.',
    'test_commands_and_simulation.py': 'A: Festpreise, ein automatischer Vertrag, zitierte Arbeitswert-XP und automatische Periodenerneuerung; Teilmengen, Auszahlung und unveränderliche Snapshots bleiben geprüft.',
    'test_company_xp_progression.py': 'A: Ein automatisch materialisierter Vertrag; XP aus Arbeitswert, Kategorie und Company-Level, auch nach vier Regular-Abschlüssen; exakte Gesamtbuchungen bleiben geprüft.',
    'test_contract_selection_ui.py': 'A: Produkte werden automatisch festgelegt. Eindeutige vollständige Anforderungen, stabile Widgets und Lieferfortschritt ersetzen manuelle Auswahlpflicht.',
    'test_contracts_polish.py': 'A: Ein Vertrag je Kategorie und keine Pack-Prämien. Abbruch, veraltete Liefer-ID, vollständige Auszahlung, Feed-Einmaligkeit und drei Auflösungen bleiben geprüft.',
    'test_final_language_alignment.py': 'A: Freie nächste Route während einer Fahrt und reiner Sell-Pfad. Alte Packs-Komponente nur im expliziten Kompatibilitäts-Testaufbau.',
    'test_final_visual_audit_fix_pass.py': 'C: Die entfernte Inventory-Seite wird für ihre weiterhin geprüfte Komponenten-Geometrie ausdrücklich im Testaufbau montiert; die normale Navigation bleibt ohne sie.',
    'test_freight.py': 'A: Quadratische Gebäude-/Linienkosten, unbegrenzte Erweiterung, 40/400/4000/40000 Kapazität, 60/120/180/240 Sekunden, Festpreise und getrennte Sell-/Contract-Routen.',
    'test_inventory_workspaces.py': 'C: Die vorhandene Crafting-Komponentenprüfung braucht einen expliziten Legacy-Testaufbau; die Anwendung erzeugt keinen Inventory-Haupttab.',
    'test_leaderboard.py': 'A: Dritter Reiter Product Production; Sortierung, eigene Position, Hervorhebung und Auszahlungssummen bleiben unverändert geprüft.',
    'test_market.py': 'A: Preise bleiben über Ticks, Seeds, Ereignisgrenzen und lange Zeiträume fest; alte gespeicherte Preisabweichungen beeinflussen keinen Verkauf.',
    'test_packs.py': 'A: Daily-/Weekly-Abschlüsse erzeugen keine Packs; vorhandene Legacy-Pack-Funktionen bleiben getrennt als Komponenten abgedeckt.',
    'test_player_profile.py': 'C: Profilaktion der tatsächlich sichtbaren Rangliste wählen; die neue versteckte Produktionsrangliste enthält zusätzlich das lokale Profil.',
    'test_playtest2_consistency_followup.py': 'A: Navigation und Ticker teilen den Platz mit Layoutabstand; 12px Navigation, automatische Produkte und Mengenwahl im realen Kaufdialog.',
    'test_playtest_2_fix_pass.py': 'A: Automatisch aktiver Vertrag und spezialisierte Primärstandorte; vorhandene Rezeptwechsel und stabile Liefer-Widgets bleiben geprüft.',
    'test_playtest_fix_pass.py': 'A: Vertragsquote aus festen Preisen, direkte Installation in echte freie Slots und neuer Train-Durchsatz; Cash-/Identitäts-/Save-Prüfungen bleiben erhalten.',
    'test_post_audit_ui.py': 'C: Die entfernte Market-Komponente für ihren Fokus-/Identitätstest ausdrücklich im Testaufbau erzeugen.',
    'test_pre_research_polish.py': 'C: Acht echte Züge und bezahlte Linienausbauten erzeugen tatsächlich Überlauf; zwei Züge benötigen auf der aktuellen Oberfläche keinen Scrollweg.',
    'test_production_board_split.py': 'A: Sichtbarer Ressourcenstandort heißt Mining Complex; Board-Eigentum und Zielslot bleiben geprüft.',
    'test_rarity_only_progression.py': 'A: MK ist wieder persistierter Instanzfortschritt. Legacy-MKs werden gerettet und multiplizieren die unveränderten Basiswerte linear, getrennt von Rarity.',
    'test_research.py': 'C: Eine kontrollierte Vertragsquote vor der Aktivierung aufbauen; einen bereits aktiven Snapshot nicht nachträglich über den Angebotseintrag ersetzen.',
    'test_research_interaction_polish.py': 'C: Einen vorhandenen versteckten Bereich beobachten und echte Enter-/Leave-Ereignisse unabhängig von der Offscreen-Cursorposition auslösen; Commit-/Widget-/Hover-Prüftiefe bleibt erhalten.',
    'test_research_specialization.py': 'C: Kontrollierte Quote vor Aktivierung erzeugen; Respec darf die bereits akzeptierte Cash-/Freight-Quote weiterhin nicht ändern.',
    'test_resource_flow_consistency.py': 'A: Gasfluss 120 Produktion / 60 Brennstoff / 60 netto, in Kernanalyse und beiden UI-Einstiegspunkten.',
    'test_resources_and_cash.py': 'A: Lager über Level 10, steigende kubische Kosten, aktuelle Hallenkosten und Festpreis-Verkäufe; genaue Debit-/Stock-/History-Prüfungen bleiben bestehen.',
    'test_secondary_modernization.py': 'C: Zwei Starter-Trucks sind vorhanden; eine leere Auswahl darf in diesem Zustand nicht erwartet werden. Bestehende Filtertests bleiben erhalten.',
    'test_sqlite_store.py': 'A: Die tatsächlich akzeptierten XP persistieren, ein Vertrag je Kategorie und ersatzlose Entfernung alter Pack-Bestände; übrige Save-Assertions bleiben bestehen.',
    'test_supply.py': 'A: Käufe installieren direkt. Fixtures stellen echte kompatible freie Standorte bereit; Cash, Qualität, IDs, Installation, Tagesgrenzen und Save bleiben geprüft.',
}


def classify(node):
    module, _, name = node.partition('::')
    module = Path(module).name
    if 'title_milestone_grants_three_full_packs' in name:
        return 'B', 'Aktiver Titel-Meilenstein vergab trotz Entfernung des Pack-Systems noch drei Packs. Vergabe im XP-Pfad entfernt; Level-/Cash-Prüfung bleibt.'
    if 'readable_purchase_geometry' in name:
        return 'B', 'CSS übersteuerte die passend berechnete Preis-Schriftgröße. Tatsächliche Schriftgröße auf derselben CSS-Priorität gesetzt; unveränderte Breitenassertion besteht.'
    if 'topbar_primary_values' in name:
        return 'B', 'Geldwert war breiter als das Kopfmodul. Bestehende Fläche erhält eine gecachte passende Schriftgröße und konsistente kompakte Zahlen.'
    if 'machine_card_runtime_zones' in name:
        return 'A', 'Geometrie liegt jetzt im gecachten Kartenrenderer; Layoutprüfung dorthin übertragen und Entfernung des Produktionsbalkens ausdrücklich geprüft.'
    if module == 'test_factory_ui.py':
        if 'clears_pending_selection_state' in name:
            return 'B', 'Neue explizite Verkaufsaktion ließ eine zuvor offene Kartenauswahl stehen. Erfolgreicher Verkauf schließt den Drawer; keine Geld-/Kartenrestbestände.'
        if 'event_feed_suppresses' in name:
            return 'C', 'Fixture übersah bereits bestehenden XP-Feed-Schwellenwert 10. Winzige XP werden unterdrückt; Rundung positiver Bruchteile bleibt zusätzlich am Entry separat geprüft.'
        if any(word in name for word in ('draw', 'installed_freight', 'mixed_freight', 'freight_hover', 'freight_ready', 'freight_contract_assignment', 'freight_card_selection', 'freight_assignment_view', 'freight_runtime_actions', 'freight_assign_route', 'resource_selectors_share', 'resource_selection_tile', 'resource_selectors_share', 'resource_selectors', 'resource_selectors', 'tooltip_behavior', 'search_and_filter')):
            return 'C', 'Kontrollierter Drawer-Bestand: zwei reale Starter-Trucks wurden beim Stacken mit Testkarten zusammengefasst. Fixture setzt den gezielt getesteten Bestand; normale Starter-Ausstattung bleibt in Anwendung und eigenen Tests erhalten.'
        if 'main_tab_headers' in name:
            return 'C', 'Entfernte Legacy-Komponenten ausdrücklich für die Header-Komponentenprüfung anlegen und polieren; keine Wiederaufnahme in die normale Navigation.'
        return 'A', 'Aktuelle Bedienung/Spielregeln: Auswahl statt Entfernung per Linksklick, expliziter bestätigter Verkauf, nächster Freight-Ausbauslot ohne altes Maximum, MK-Metadaten, Sell-Beschriftung, Festpreise oder automatische Einzel-Contracts. Zugehörige Geometrie-/Buchungs-/Identitätsprüfungen bleiben erhalten.'
    reason = REASONS.get(module)
    if not reason:
        raise ValueError(f'Unclassified failure: {node}')
    return reason[0], reason[3:]


def main():
    records = {}
    reference = json.loads((ROOT / 'reference/results.json').read_text(encoding='utf-8'))
    for entry in reference:
        log = ROOT / 'reference' / (Path(entry['module']).stem + '.txt')
        for line in log.read_text(encoding='utf-8').splitlines():
            if line.startswith('FAILED '):
                node = line[7:].split(' - ', 1)[0]
                category, reason = classify(node)
                records[node] = dict(node=node, category=category, reason=reason, evidence=log.as_posix())
        if entry['exit_code'] == 124:
            module = entry['module']
            reason = ('C/D: Isolierter Stacktrace zeigt Warten im neuen echten Kaufdialog. Testtreiber bedient dessen Qt-Controls. Danach vollständige 217 Tests, keine Endlosschleife; Modulzeitbudget 360s für den gemessenen Gesamtumfang.' if module == 'test_factory_ui.py' else
                      'D: 147.58s für 353 × 512 × 512 einzelne Python/Qt-Pixelaufrufe, isoliert 149.43s insgesamt. Gleiche Vollbild-Schwelle, Pixelzahl und inklusive Randgrenzen jetzt über RGBA-Bytes, Translation und native Zeilenoperationen; alle vier Tests bestehen in wenigen Sekunden.')
            records[module + '::<timeout>'] = dict(node=module + '::<timeout>', category='C' if module == 'test_factory_ui.py' else 'D', reason=reason, evidence='factory-diagnosis.txt' if module == 'test_factory_ui.py' else 'raster-diagnosis.txt')
    # The longer first complete UI diagnosis exposed assertions beyond the old cutoff.
    for line in (ROOT / 'factory-pass1.txt').read_text(encoding='utf-8').splitlines():
        if line.startswith('FAILED '):
            node = line[7:].split(' - ', 1)[0]
            category, reason = classify(node)
            records.setdefault(node, dict(node=node, category=category, reason=reason, evidence='factory-pass1.txt'))
    changed = []
    with ZipFile('artifacts/release-backups/20261018T203430454897Z/working-tree.zip') as backup:
        for path in sorted(Path('tests').glob('test_*.py')):
            old = ast.parse(backup.read(path.as_posix()).decode('utf-8'))
            new = ast.parse(path.read_text(encoding='utf-8'))
            before = [n for n in old.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
            after = [n for n in new.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
            by_name = {n.name: n for n in after}
            for index, function in enumerate(before):
                current = by_name.get(function.name)
                if current is None:
                    assert index < len(after), f'Test removed: {path}:{function.name}'
                    current = after[index]
                if ast.dump(function) != ast.dump(current):
                    changed.append(dict(module=path.name, before=function.name, after=current.name))
    report = dict(classification_counts=dict(Counter(r['category'] for r in records.values())),
                  classified_results=len(records), updated_test_functions=len(changed),
                  updated_functions=changed, results=sorted(records.values(), key=lambda r: r['node']))
    (ROOT / 'classification.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    lines = ['# Industriova – vollständige Fehlerklassifizierung', '',
             'Jeder im unveränderten neuen Referenzlauf gemeldete Testfehler und beide Zeitlimits sind erfasst. Der erste vollständig ausführbare UI-Lauf ergänzt die zuvor abgeschnittenen Fälle. A = Solländerung, B = Produktfehler, C = Testaufbau, D = Laufzeit. Zusätzliche durch neue Integrations-/Sichtprüfungen gefundene Produktfehler stehen im Release-Bericht.', '',
             f"{len(records)} klassifizierte Ergebnisse; {len(changed)} bestehende Testfunktionen fachlich/technisch angepasst. Parametrisierungen zählen hier einmal je Funktion; der endgültige Prüflauf zählt ausgeführte Testfälle.", '',
             '| Test / Zeitlimit | Klasse | Ursache und Korrektur |', '| --- | --- | --- |']
    for record in report['results']:
        lines.append(f"| `{record['node'].replace('|', '/').replace(chr(10), ' ')}` | {record['category']} | {record['reason'].replace('|', '/')} |")
    Path('docs/industriova-regression-classification.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ('results', 'updated_functions')}))


if __name__ == '__main__':
    main()
