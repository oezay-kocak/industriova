# P7: Infrastruktur- und Freight-Preistabelle

Cash, Preisversion 1. Werte direkt aus dem produktiven Preispfad. Bereits gekaufte Investitionen bleiben historisch.

| Bereich | Startplätze / eine Linie | Maximum | Zusatzslots je Linie | Weitere Linien | Vollausbau ohne Gebäude/Karten |
| --- | --- | --- | --- | --- | --- |
| factory | 3 | 5 × 10 | 40, 80, 120, 160, 200, 240, 280 | 900, 3,600, 8,100, 14,400 | 32,600 |
| resources | 1 | 3 × 10 | 90, 180, 270, 360, 450, 540, 630, 720, 810 | 900, 3,600 | 16,650 |
| energy | 1 | 3 × 5 | 100, 200, 300, 400 | 500, 2,000 | 5,500 |

Für k zusätzliche Plätze: Factory 40k, Resources 90k, Energy 100k. Linienpreis B(l−1)² mit B=900/900/500. Bei historischen abweichenden Linienmaßen wird B aus genau deren Start- und Maximalplätzen abgeleitet: auf 100 aufrunden von (letzter Zusatzslot × Startplätze + 1). Bereits bezahlte Linien bleiben unverändert.

| Bereits vorhandene Facilities | Factory | Resources je Spezialisierung | Energy |
| --- | --- | --- | --- |
| 0 | 1,000 | 500 | 1,000 |
| 1 | 15,200 | 4,000 | 2,200 |
| 2 | 86,000 | 22,700 | 12,500 |
| 3 | 237,000 | 62,400 | 34,300 |
| 4 | 486,400 | 128,000 | 70,400 |
| 5 | 849,800 | 223,700 | 123,000 |
| 6 | 1,340,400 | 352,800 | 194,000 |
| 7 | 1,970,600 | 518,600 | 285,300 |
| 8 | 2,751,500 | 724,100 | 398,300 |
| 9 | 3,693,600 | 972,000 | 534,600 |

Bei n≥1: auf 100 aufrunden von C × n^2.5; C=15.200 / 4.000 / 2.200. Factory maximal zehn Gebäude; Resources zählt Mining/Agriculture/Drilling getrennt. Erste Facility ohne vorhandenen Typ 500, Factory/Energy ohne Bestand 1.000. Die gegebenen Startergebäude bleiben kostenlos. Typwechsel eines leeren Standorts zahlt den aktuellen Zieltyp-Neubaupreis ohne Gutschrift alter Ausbauinvestitionen.

| Freight | Startslots | Grundpreis bei 0 Bestand | Kauf bei 1 Bestand | Kauf bei 2 Bestand | Erste Linie zusätzlich bis 8 |
| --- | --- | --- | --- | --- | --- |
| garage_depot | 3 | 2,000 | 8,000 | 18,000 | 60, 120, 180, 240, 300 |
| rail_station | 2 | 8,000 | 32,000 | 72,000 | 60, 120, 180, 240, 300, 360 |
| airport | 2 | 30,000 | 120,000 | 270,000 | 60, 120, 180, 240, 300, 360 |
| harbor | 2 | 100,000 | 400,000 | 900,000 | 60, 120, 180, 240, 300, 360 |

Freight-Facility bei n gleichen Anlagen: Grundpreis × (n+1)². Die erste Garage wird beim Spielstart gestellt; die nächste Garage kostet deshalb 8.000. Alle Freight-Linien haben acht Positionen. Linien 2–10 kosten für ihren ersten Platz: 900, 3.600, 8.100, 14.400, 22.500, 32.400, 44.100, 57.600, 72.900. Allgemein Linie l: 900(l−1)². Weitere sieben Plätze jeder zusätzlichen Linie kosten 60, 120, 180, 240, 300, 360, 420. Eine neue Linie kann vor vollständigem Ausbau der vorherigen gekauft werden; Lücken bleiben gesperrt. Späte weitere Gebäude können bei sehr vielen Linien wieder günstiger sein.

| Fahrzeug Common MK1 | Preis | Kapazität | Sekunden | Voll beladen Einheiten/min |
| --- | --- | --- | --- | --- |
| Freight Truck | 205.00 | 40 | 60 | 40.00 |
| Freight Train | 650.00 | 400 | 120 | 200.00 |
| Cargo Aircraft | 4,985.00 | 4,000 | 180 | 1,333.33 |
| Cargo Ship | 14,955.00 | 16,000 | 240 | 4,000.00 |

Die CSV enthält alle vier Fahrzeuge für MK1–99: Common-Basispreis, kumulierte Common-MK-Investition, nächste Upgradequote und effektive Kapazität/Zeit ohne Research. Die bestehende MK-Formel M=1+0,25(MK−1) bleibt erhalten. Rarity wirkt über den individuellen Bonus; identische Rarity-Namen allein garantieren keinen identischen zufälligen Bonus. Für Aircraft/Ship bei gleichem MK, Bonus und Research beträgt die Vollauslastungsrelation 3×. Cent-Rundungen bei MK-Kosten bleiben bestehen. Daily-Uncommon-Preise hängen vom Bonus ab; Common, Daily, Templates und MK beziehen ihren Basiswert aus common_card_price.

Common Ship: 14.955; Aircraft: 4.985. Ship MK1→2 kostet 15.000,01, Aircraft 5.000,00. Historische Käufe/Upgrades werden daraus nicht neu berechnet.

[Vollständige tabellarische Werte inklusive aller Freight-MK-Stufen](industriova-03-phase7-price-table.csv).
