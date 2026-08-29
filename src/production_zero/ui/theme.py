from __future__ import annotations


class Theme:
    SURFACE_0 = "#080d11"
    SURFACE_1 = "#121719"
    SURFACE_2 = "#1a1f20"
    SURFACE_3 = "#282c2b"
    SURFACE_INTERACTIVE = "#303534"
    SURFACE_HOVER = "#3d4240"
    BACKGROUND = SURFACE_0
    PANEL = SURFACE_2
    PANEL_ALT = SURFACE_3
    BORDER = "#444945"
    BORDER_STRONG = "#62645c"
    GRID = "#333734"
    TEXT = "#edf6f2"
    MUTED = "#9fb2ad"
    DIM = "#637570"
    GOOD = "#65d88f"
    SAFETY_YELLOW = "#ffd21f"
    WARN = "#c83a2b"
    WARNING_ORANGE = "#df6b2f"
    BAD = "#f06f73"
    ENERGY = SAFETY_YELLOW
    CASH = "#7fed18"
    RESOURCE = "#25b9e8"
    RARE = "#b187ff"
    INDUSTRIAL_FONT = '"Bahnschrift Condensed", "Bahnschrift SemiCondensed", "Agency FB", "Arial Narrow", "Bahnschrift", "Segoe UI"'
    RADIUS_PANEL = 10
    RADIUS_CARD = 8


APP_STYLESHEET = f"""
QMainWindow, QWidget {{
    background: {Theme.BACKGROUND};
    color: {Theme.TEXT};
    font-family: "Segoe UI";
}}
QLabel {{
    background: transparent;
}}
QLabel#title {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 24px;
    font-weight: 700;
}}
QLabel#subtitle {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 13px;
}}
QFrame#globalHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0b1419, stop:0.55 {Theme.SURFACE_2}, stop:1 #0f2229);
    border: 1px solid {Theme.BORDER_STRONG};
    border-radius: 14px;
}}
QFrame#commandDeckTitlePanel {{
    background: transparent;
    border: 0;
    min-width: 210px;
}}
QFrame#topbarEconomyCluster {{
    background: rgba(255, 255, 255, 5);
    border: 1px solid rgba(159, 178, 173, 32);
    border-radius: 12px;
}}
QFrame#cashStatusPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(216, 240, 106, 28), stop:1 rgba(216, 240, 106, 9));
    border: 1px solid rgba(216, 240, 106, 86);
    border-radius: 10px;
    min-width: 146px;
}}
QFrame#cashStatusPanel[cashPulse="true"] {{
    background: rgba(216, 240, 106, 34);
    border-color: {Theme.CASH};
}}
QFrame#energyStatusPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(98, 190, 232, 25), stop:1 rgba(98, 190, 232, 8));
    border: 1px solid rgba(98, 190, 232, 76);
    border-radius: 10px;
    min-width: 150px;
}}
QFrame#energyStatusPanel[energyState="strained"] {{
    background: rgba(242, 194, 91, 18);
    border-color: rgba(242, 194, 91, 118);
}}
QFrame#energyStatusPanel[energyState="overloaded"] {{
    background: rgba(240, 111, 115, 18);
    border-color: rgba(240, 111, 115, 125);
}}
QFrame#resourceStoragePanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(143, 180, 255, 25), stop:1 rgba(143, 180, 255, 8));
    border: 1px solid rgba(143, 180, 255, 76);
    border-radius: 10px;
    min-width: 174px;
}}
QFrame#topbarResourceStrip {{
    background: rgba(255, 255, 255, 3);
    border: 1px solid rgba(159, 178, 173, 20);
    border-radius: 10px;
}}
QFrame#topbarResourceChip {{
    background: rgba(255, 255, 255, 5);
    border: 1px solid rgba(159, 178, 173, 24);
    border-radius: 8px;
    min-width: 72px;
}}
QLabel#commandDeckLabel {{
    background: transparent;
    color: {Theme.RESOURCE};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#cashStatusTitle {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#cashStatusAmount {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 22px;
    font-weight: 900;
}}
QLabel#cashStatusIcon, QLabel#energyStatusIcon, QLabel#resourceStorageIcon {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(255, 255, 255, 22);
    border-radius: 8px;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 900;
    min-width: 26px;
    min-height: 30px;
}}
QLabel#energyStatusTitle, QLabel#resourceStorageTitle, QLabel#topbarResourceName {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#energyStatusAmount {{
    background: transparent;
    color: {Theme.ENERGY};
    font-size: 16px;
    font-weight: 900;
}}
QLabel#resourceStorageAmount {{
    background: transparent;
    color: {Theme.RESOURCE};
    font-size: 15px;
    font-weight: 900;
}}
QLabel#topbarResourceAmount {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 14px;
    font-weight: 900;
}}
QLabel#topbarResourceMarker {{
    background: transparent;
    color: {Theme.RESOURCE};
    font-size: 12px;
    font-weight: 900;
}}
QProgressBar#energyStatusProgress {{
    background: rgba(255, 255, 255, 18);
    border: 1px solid rgba(98, 190, 232, 54);
    border-radius: 3px;
    height: 6px;
}}
QProgressBar#energyStatusProgress::chunk {{
    background: {Theme.GOOD};
    border-radius: 3px;
}}
QProgressBar#energyStatusProgress[energyState="strained"]::chunk {{
    background: {Theme.WARN};
}}
QProgressBar#energyStatusProgress[energyState="overloaded"]::chunk {{
    background: {Theme.BAD};
}}
QWidget#companyProgressPanel {{
    background: transparent;
    min-width: 230px;
    max-width: 280px;
}}
QLabel#companyLevelLabel {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 14px;
    font-weight: 800;
}}
QLabel#companyXpLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 600;
}}
QProgressBar#companyXpProgress {{
    background: rgba(255, 255, 255, 18);
    border: 1px solid rgba(216, 240, 106, 42);
    border-radius: 3px;
    height: 6px;
}}
QProgressBar#companyXpProgress::chunk {{
    background: {Theme.CASH};
    border-radius: 3px;
}}
QFrame#eventFeed {{
    background: transparent;
    border: 0;
    min-width: 320px;
    max-width: 420px;
}}
QFrame#eventFeedEntry {{
    background: rgba(23, 33, 40, 215);
    border: 1px solid #34454f;
    border-radius: 7px;
}}
QFrame#eventFeedEntry[eventType="cash"] {{
    border-color: #566a35;
}}
QFrame#eventFeedEntry[eventType="xp"] {{
    border-color: #3c5870;
}}
QFrame#eventFeedEntry[eventType="pack"] {{
    border-color: #5b4e77;
}}
QFrame#eventFeedEntry[eventType="contract"] {{
    border-color: #456356;
}}
QLabel#eventFeedIcon {{
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    min-width: 20px;
}}
QLabel#eventFeedAmount {{
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#eventFeedAmount[eventType="cash"] {{
    color: {Theme.CASH};
}}
QLabel#eventFeedAmount[eventType="xp"] {{
    color: {Theme.ENERGY};
}}
QLabel#eventFeedAmount[eventType="pack"] {{
    color: #b98cff;
}}
QLabel#eventFeedLabel {{
    color: {Theme.MUTED};
    font-size: 12px;
    font-weight: 700;
}}
QTabWidget::pane {{
    border: 1px solid rgba(159, 178, 173, 24);
    background: {Theme.SURFACE_1};
    top: -1px;
}}
QTabBar::tab {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #313636, stop:0.48 #171b1b, stop:1 #050707);
    color: #f0f2e9;
    border: 1px solid rgba(34, 38, 36, 230);
    border-top-color: rgba(190, 190, 174, 76);
    border-radius: 7px;
    padding: 10px 17px;
    margin-right: 4px;
    margin-bottom: 4px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-weight: 900;
}}
QTabBar::tab:selected {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe764, stop:0.45 {Theme.SAFETY_YELLOW}, stop:1 #a97200);
    color: #11130b;
    border-color: rgba(7, 8, 7, 230);
}}
QTabBar::tab:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #303b3e, stop:1 #111819);
    color: {Theme.TEXT};
    border-color: rgba(255, 210, 31, 112);
}}
QTabBar::tab:pressed {{
    background: #c7960d;
    color: #11130b;
    border-color: rgba(8, 8, 7, 210);
}}
QFrame#inventoryPanel, QFrame#inventoryHeader, QFrame#craftingPanel, QFrame#craftSelectionPanel, QFrame#mkUpgradePanel, QFrame#cardSelectionDrawer, QFrame#resourceDrawer, QFrame#freightKpiPanel, QFrame#freightFacilityPanel, QFrame#freightSlotsPanel, QFrame#freightCardSelectionView, QFrame#freightAssignmentSelectionView, QFrame#salesPanel, QFrame#inventoryFilters, QFrame#chartControls, QFrame#marketControls, QFrame#marketEventPanel, QFrame#devPanel, QFrame#contractPanel, QFrame#supplyStoreHeader, QFrame#supplySectionSelector, QFrame#supplyToolbar {{
    background: {Theme.SURFACE_2};
    border: 1px solid {Theme.BORDER};
    border-radius: {Theme.RADIUS_PANEL}px;
}}
QFrame#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #182b34, stop:0.34 #0f1c23, stop:1 #070d12);
    border: 1px solid rgba(98, 190, 232, 68);
    border-radius: 16px;
}}
QFrame#factoryV2Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d3d2c8, stop:0.46 #999d93, stop:1 #49514d);
    border: 2px solid rgba(54, 58, 54, 180);
    border-radius: 16px;
}}
QFrame#factoryV2CommandDeck {{
    background: transparent;
    border: 0;
}}
QFrame#factoryV2PrimarySystems, QFrame#factoryV2ResourceStrip, QFrame#factoryV2ProgressionZone {{
    background: transparent;
    border: 0;
}}
QFrame#factoryV2Metric, QFrame#factoryV2StorageModule {{
    background: transparent;
    border: 0;
}}
QFrame#factoryV2PrimarySystems {{
    background: transparent;
    border: 0;
}}
QFrame#factoryV2ResourceStrip {{
    background: transparent;
    border: 0;
}}
QFrame#factoryV2ProgressionZone {{
    background: transparent;
    border: 0;
}}
QFrame#factoryV2RankEmblem {{
    background: transparent;
    border: 0;
}}
QLabel#factoryV2DeckLabel {{
    color: #10120e;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#factoryV2CashLabel, QLabel#factoryV2EnergyLabel, QLabel#factoryV2StorageLabel, QLabel#factoryV2OperationsLabel {{
    color: #f1f4ec;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#factoryV2CashLabel {{
    color: {Theme.CASH};
}}
QLabel#factoryV2EnergyLabel {{
    color: {Theme.SAFETY_YELLOW};
}}
QLabel#factoryV2StorageLabel {{
    color: #25b9e8;
}}
QLabel#factoryV2OperationsLabel {{
    color: #f4eee1;
}}
QLabel#factoryV2OperationsHint {{
    color: #d8d2c3;
    font-size: 9px;
    font-weight: 800;
}}
QLabel#factoryV2DeckTitle {{
    color: #080908;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 40px;
    font-weight: 900;
}}
QLabel#factoryV2Xp {{
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#factoryV2MetricValue, QLabel#factoryV2CashValue, QLabel#factoryV2EnergyValue, QLabel#factoryV2StorageValue {{
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 22px;
    font-weight: 900;
}}
QLabel#factoryV2ResourceAmount {{
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#factoryV2Level {{
    color: {Theme.SAFETY_YELLOW};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 17px;
    font-weight: 900;
}}
QLabel#factoryV2RankTitle {{
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#factoryV2LineEyebrow {{
    color: {Theme.WARN};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 8px;
    font-weight: 900;
}}
QLabel#factoryV2LineTitle {{
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 25px;
    font-weight: 900;
}}
QFrame#factoryHallCommandBoard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3d2a20, stop:0.2 #1d2d25, stop:0.46 #142a34, stop:0.68 #1f2a22, stop:0.84 #2a2516, stop:1 #101211);
    border: 1px solid rgba(142, 154, 150, 68);
    border-radius: 16px;
}}
QFrame#factoryHallHeader {{
    background: transparent;
    border: 0;
}}
QFrame#factoryV2HallOverview, QFrame#factoryV2HallStage, QFrame#factoryV2Board, QFrame#factoryV2ProductionTrack {{
    background: transparent;
    border: 0;
}}
QScrollArea#factoryV2Scroll, QWidget#factoryV2ScrollViewport, QWidget#factoryV2LinesContent {{
    background: transparent;
    border: 0;
}}
QFrame#lockedLinePanel[factoryV2="true"] {{
    background: transparent;
    border: 0;
    min-height: 104px;
    max-height: none;
}}
QFrame#factoryHallTitleShell {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(142, 154, 150, 12), stop:0.58 rgba(255, 255, 255, 7), stop:1 rgba(95, 109, 106, 12));
    border: 1px solid rgba(159, 178, 173, 34);
    border-radius: 11px;
}}
QFrame#factoryCommandDivider {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(142, 154, 150, 0), stop:0.18 rgba(142, 154, 150, 46), stop:0.82 rgba(95, 109, 106, 38), stop:1 rgba(95, 109, 106, 0));
    border: 0;
    border-radius: 1px;
}}
QFrame#factoryStatusZone {{
    background: transparent;
    border: 0;
}}
QFrame#linePanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #242c2e, stop:0.18 #1b2325, stop:0.55 #121819, stop:1 #080a0a);
    border: 1px solid rgba(142, 154, 150, 54);
    border-radius: 15px;
}}
QFrame#inventoryKpi, QFrame#cardDetailsSection, QFrame#cardPerformanceSection, QFrame#cardInventorySection, QFrame#freightKpi, QFrame#freightShipmentPanel {{
    background: {Theme.SURFACE_3};
    border: 1px solid {Theme.BORDER};
    border-radius: {Theme.RADIUS_CARD}px;
}}
QFrame#inventoryKpi {{
    background: rgba(255, 255, 255, 7);
    border: 1px solid rgba(159, 178, 173, 58);
    border-radius: {Theme.RADIUS_CARD}px;
}}
QFrame#inventoryCardsHeader {{
    background: transparent;
    border: 0;
}}
QFrame#chartsHeader {{
    background: transparent;
    border: 0;
}}
QFrame#chartsHeaderMetric {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(37, 46, 45, 238), stop:0.55 rgba(12, 18, 18, 246), stop:1 rgba(5, 7, 7, 255));
    border: 1px solid rgba(37, 185, 232, 135);
    border-radius: 8px;
}}
QFrame#marketHeader {{
    background: transparent;
    border: 0;
}}
QFrame#marketHeaderMetric {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(42, 37, 27, 238), stop:0.55 rgba(17, 15, 11, 246), stop:1 rgba(7, 6, 4, 255));
    border: 1px solid rgba(255, 210, 31, 128);
    border-radius: 8px;
}}
QFrame#inventoryScrapModule {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(37, 46, 45, 238), stop:0.55 rgba(12, 18, 18, 246), stop:1 rgba(5, 7, 7, 255));
    border: 1px solid rgba(158, 190, 202, 150);
    border-radius: 8px;
    min-width: 188px;
}}
QFrame#inventoryCardsBrowserShell {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d3d2c8, stop:0.42 #9fa49b, stop:1 #565d59);
    border: 2px solid rgba(54, 58, 54, 184);
    border-radius: 16px;
}}
QFrame#inventoryFilters {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 23, 23, 246), stop:0.55 rgba(9, 13, 13, 252), stop:1 rgba(18, 23, 23, 246));
    border: 1px solid rgba(142, 154, 150, 72);
    border-radius: 10px;
}}
QWidget#craftFilterDeck {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 23, 23, 246), stop:0.55 rgba(9, 13, 13, 252), stop:1 rgba(18, 23, 23, 246));
    border: 1px solid rgba(142, 154, 150, 72);
    border-radius: 10px;
}}
QWidget#mkUpgradeFilterDeck {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 23, 23, 246), stop:0.55 rgba(9, 13, 13, 252), stop:1 rgba(18, 23, 23, 246));
    border: 1px solid rgba(142, 154, 150, 72);
    border-radius: 10px;
}}
QWidget#chartFilterDeck {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 23, 23, 246), stop:0.55 rgba(9, 13, 13, 252), stop:1 rgba(18, 23, 23, 246));
    border: 1px solid rgba(142, 154, 150, 72);
    border-radius: 10px;
}}
QFrame#chartDetailHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 23, 23, 246), stop:0.55 rgba(9, 13, 13, 252), stop:1 rgba(18, 23, 23, 246));
    border: 1px solid rgba(37, 185, 232, 86);
    border-radius: 10px;
}}
QWidget#marketFilterDeck {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(21, 22, 19, 246), stop:0.55 rgba(10, 11, 10, 252), stop:1 rgba(22, 21, 16, 246));
    border: 1px solid rgba(142, 128, 86, 82);
    border-radius: 10px;
}}
QFrame#marketEventPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(42, 36, 18, 238), stop:0.48 rgba(13, 16, 15, 248), stop:1 rgba(28, 22, 12, 242));
    border: 1px solid rgba(255, 210, 31, 104);
    border-radius: 10px;
}}
QFrame#marketDetailHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(21, 22, 19, 246), stop:0.55 rgba(10, 11, 10, 252), stop:1 rgba(22, 21, 16, 246));
    border: 1px solid rgba(255, 210, 31, 104);
    border-radius: 10px;
}}
QLineEdit#inventorySearch {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(158, 176, 180, 96);
    border-radius: 6px;
    color: {Theme.TEXT};
    padding: 7px 10px;
    min-width: 190px;
}}
QLineEdit#chartResourceSearch {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(158, 176, 180, 96);
    border-radius: 6px;
    color: {Theme.TEXT};
    padding: 7px 10px;
    min-width: 190px;
}}
QLineEdit#marketSearch {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(180, 164, 98, 92);
    border-radius: 6px;
    color: {Theme.TEXT};
    padding: 7px 10px;
    min-width: 190px;
}}
QLineEdit#craftTargetSearch, QLineEdit#craftMaterialSearch {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(158, 176, 180, 96);
    border-radius: 6px;
    color: {Theme.TEXT};
    padding: 7px 10px;
    min-width: 190px;
}}
QLineEdit#mkUpgradeSearch {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(158, 176, 180, 96);
    border-radius: 6px;
    color: {Theme.TEXT};
    padding: 7px 10px;
    min-width: 190px;
}}
QPushButton#inventoryFilterChip {{
    background: rgba(255, 255, 255, 9);
    border: 1px solid rgba(142, 154, 150, 70);
    border-radius: 5px;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 9px;
}}
QPushButton#inventoryFilterChip:hover {{
    background: rgba(255, 255, 255, 18);
    border-color: rgba(142, 154, 150, 120);
    color: {Theme.TEXT};
}}
QPushButton#inventoryFilterChip[active="true"] {{
    background: rgba(255, 210, 31, 210);
    border-color: rgba(255, 241, 140, 230);
    color: #15120a;
}}
QPushButton#chartFilterChip {{
    background: rgba(255, 255, 255, 9);
    border: 1px solid rgba(142, 154, 150, 70);
    border-radius: 5px;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 9px;
}}
QPushButton#chartFilterChip:hover {{
    background: rgba(255, 255, 255, 18);
    border-color: rgba(142, 154, 150, 120);
    color: {Theme.TEXT};
}}
QPushButton#chartFilterChip[active="true"] {{
    background: rgba(37, 185, 232, 198);
    border-color: rgba(171, 232, 255, 218);
    color: #071115;
}}
QPushButton#marketFilterChip {{
    background: rgba(255, 255, 255, 9);
    border: 1px solid rgba(142, 132, 98, 74);
    border-radius: 5px;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 9px;
}}
QPushButton#marketFilterChip:hover {{
    background: rgba(255, 255, 255, 18);
    border-color: rgba(255, 210, 31, 126);
    color: {Theme.TEXT};
}}
QPushButton#marketFilterChip[active="true"] {{
    background: rgba(255, 210, 31, 205);
    border-color: rgba(255, 241, 140, 224);
    color: #15120a;
}}
QPushButton#supplyFilterChip {{
    background: rgba(255, 255, 255, 9);
    border: 1px solid rgba(142, 132, 98, 74);
    border-radius: 5px;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 9px;
}}
QPushButton#supplyFilterChip:hover {{
    background: rgba(255, 255, 255, 18);
    border-color: rgba(255, 210, 31, 126);
    color: {Theme.TEXT};
}}
QPushButton#supplyFilterChip[active="true"] {{
    background: rgba(255, 210, 31, 205);
    border-color: rgba(255, 241, 140, 224);
    color: #15120a;
}}
QPushButton#marketCategorySelectorButton, QPushButton#marketSortSelectorButton {{
    background: rgba(255, 255, 255, 9);
    border: 1px solid rgba(142, 132, 98, 86);
    border-radius: 5px;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 10px;
    text-align: left;
}}
QPushButton#marketCategorySelectorButton:hover, QPushButton#marketSortSelectorButton:hover {{
    background: rgba(255, 255, 255, 18);
    border-color: rgba(255, 210, 31, 142);
}}
QPushButton#supplyMachineSelector, QPushButton#supplySortSelector {{
    background: rgba(255, 255, 255, 9);
    border: 1px solid rgba(142, 132, 98, 86);
    border-radius: 5px;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 10px;
    text-align: left;
}}
QPushButton#supplyMachineSelector:hover, QPushButton#supplySortSelector:hover {{
    background: rgba(255, 255, 255, 18);
    border-color: rgba(255, 210, 31, 142);
}}
QFrame#marketSelectorFlyout {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(35, 34, 28, 250), stop:1 rgba(8, 9, 8, 255));
    border: 1px solid rgba(255, 210, 31, 118);
    border-radius: 8px;
}}
QFrame#supplySelectorFlyout {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(35, 34, 28, 250), stop:1 rgba(8, 9, 8, 255));
    border: 1px solid rgba(255, 210, 31, 118);
    border-radius: 8px;
}}
QPushButton#marketSelectorOption {{
    background: rgba(255, 255, 255, 7);
    border: 1px solid rgba(142, 132, 98, 58);
    border-radius: 5px;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 10px;
    text-align: left;
    min-width: 150px;
}}
QPushButton#supplySelectorOption {{
    background: rgba(255, 255, 255, 7);
    border: 1px solid rgba(142, 132, 98, 58);
    border-radius: 5px;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 10px;
    text-align: left;
    min-width: 150px;
}}
QPushButton#supplySelectorOption:hover {{
    background: rgba(255, 255, 255, 16);
    color: {Theme.TEXT};
    border-color: rgba(255, 210, 31, 116);
}}
QPushButton#supplySelectorOption[active="true"] {{
    background: rgba(255, 210, 31, 205);
    border-color: rgba(255, 241, 140, 224);
    color: #15120a;
}}
QPushButton#marketSelectorOption:hover {{
    background: rgba(255, 255, 255, 16);
    color: {Theme.TEXT};
    border-color: rgba(255, 210, 31, 116);
}}
QPushButton#marketSelectorOption[active="true"] {{
    background: rgba(255, 210, 31, 205);
    border-color: rgba(255, 241, 140, 224);
    color: #15120a;
}}
QWidget#cardInventoryGrid {{
    background: transparent;
}}
QWidget#chartChipGroup {{
    background: transparent;
    border: 0;
}}
QWidget#marketChipGroup {{
    background: transparent;
    border: 0;
}}
QWidget#marketSelectorGroup {{
    background: transparent;
    border: 0;
}}
QWidget#supplyFilterGroup {{
    background: transparent;
    border: 0;
}}
QWidget#inventoryFilterGroup {{
    background: transparent;
    border: 0;
}}
QFrame#inventoryCard {{
    background: transparent;
    border: 0;
}}
QFrame#packOpenedCardTile {{
    background: {Theme.SURFACE_3};
    border: 1px solid rgba(113, 138, 148, 112);
    border-radius: {Theme.RADIUS_CARD}px;
}}
QFrame#craftTargetCard, QFrame#craftMaterialCard {{
    background: transparent;
    border: 0;
}}
QFrame#mkUpgradeSelectionCard, QFrame#mkUpgradePreviewCard {{
    background: transparent;
    border: 0;
}}
QFrame#mkUpgradeLegacyCard {{
    background: {Theme.SURFACE_3};
    border: 1px solid rgba(113, 138, 148, 112);
    border-radius: {Theme.RADIUS_CARD}px;
}}
QFrame#inventoryCard:hover, QFrame#inventoryCard:focus {{
    background: transparent;
    border: 0;
}}
QFrame#craftTargetCard:hover, QFrame#craftTargetCard:focus, QFrame#craftMaterialCard:hover, QFrame#craftMaterialCard:focus {{
    background: transparent;
    border: 0;
}}
QFrame#mkUpgradeSelectionCard:hover, QFrame#mkUpgradeSelectionCard:focus, QFrame#mkUpgradePreviewCard:hover, QFrame#mkUpgradePreviewCard:focus {{
    background: transparent;
    border: 0;
}}
QFrame#packOpenedCardTile:hover, QFrame#packOpenedCardTile:focus {{
    background: {Theme.SURFACE_INTERACTIVE};
    border-color: rgba(98, 190, 232, 132);
}}
QFrame#inventoryCardHeader {{
    background: transparent;
    border: 0;
}}
QFrame#craftTargetCard[selected="true"], QFrame#craftMaterialCard[selected="true"] {{
    background: transparent;
    border: 0;
}}
QFrame#mkUpgradeSelectionCard[selected="true"], QFrame#mkUpgradePreviewCard[selected="true"] {{
    background: transparent;
    border: 0;
}}
QFrame#inventoryCard[selected="true"] {{
    border-color: {Theme.RESOURCE};
}}
QFrame#craftMaterialCard[enabled="false"] {{
    background: transparent;
    border: 0;
}}
QFrame#inventoryCard[cardType="energy"], QFrame#inventoryCard[cardType="extractor"], QFrame#inventoryCard[cardType="processor"], QFrame#inventoryCard[cardType="fabricator"], QFrame#inventoryCard[cardType="assembler"], QFrame#inventoryCard[cardType="freight"] {{
    background: transparent;
    border: 0;
}}
QFrame#packOpenedCardTile[cardType="energy"] {{
    border-left: 3px solid rgba(93, 183, 222, 180);
}}
QFrame#packOpenedCardTile[cardType="extractor"] {{
    border-left: 3px solid rgba(107, 188, 132, 180);
}}
QFrame#packOpenedCardTile[cardType="processor"] {{
    border-left: 3px solid rgba(98, 166, 202, 180);
}}
QFrame#packOpenedCardTile[cardType="fabricator"] {{
    border-left: 3px solid rgba(177, 141, 222, 180);
}}
QFrame#packOpenedCardTile[cardType="assembler"] {{
    border-left: 3px solid rgba(219, 154, 98, 180);
}}
QFrame#packOpenedCardTile[cardType="freight"] {{
    border-left: 3px solid rgba(155, 184, 239, 180);
}}
QFrame#inventoryRarityLine {{
    background: rgba(140, 161, 154, 120);
    border: none;
}}
QFrame#inventoryRarityLine[rarity="common"] {{
    background: rgba(140, 161, 154, 120);
}}
QFrame#inventoryRarityLine[rarity="uncommon"] {{
    background: rgba(107, 188, 132, 150);
}}
QFrame#inventoryRarityLine[rarity="rare"] {{
    background: rgba(92, 158, 220, 155);
}}
QFrame#inventoryRarityLine[rarity="epic"] {{
    background: rgba(178, 120, 226, 160);
}}
QFrame#inventoryRarityLine[rarity="legendary"] {{
    background: rgba(230, 172, 82, 170);
}}
QFrame#freightFacilityPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d3d2c8, stop:0.46 #999d93, stop:1 #49514d);
    border: 2px solid rgba(54, 58, 54, 180);
    border-radius: 16px;
}}
QFrame#freightSlotsPanel {{
    background: transparent;
    border: 0;
}}
QFrame#freightFacilityHeader {{
    background: transparent;
    border: 0;
}}
QFrame#freightBayTrack {{
    background: transparent;
    border: 0;
}}
QWidget#freightSlotGridHost {{
    background: transparent;
}}
QFrame#freightSlotCard {{
    background: transparent;
    border: none;
}}
QFrame#freightSlotCard:hover, QFrame#freightSlotCard:focus {{
    background: transparent;
    border: none;
}}
QFrame#freightSlotCard[slotState="empty"] {{
    background: transparent;
    border: none;
}}
QFrame#freightSlotCard[slotState="locked"] {{
    background: transparent;
    border: none;
}}
QFrame#freightSlotCard[freightFamily="truck"] {{
    border: none;
}}
QFrame#freightSlotCard[freightFamily="train"] {{
    border: none;
}}
QFrame#freightSlotCard[freightFamily="ship"] {{
    border: none;
}}
QFrame#freightSlotCard[freightFamily="aircraft"] {{
    border: none;
}}
QFrame#freightRarityLine {{
    background: rgba(140, 161, 154, 120);
    border: none;
}}
QFrame#freightRarityLine[rarity="common"] {{
    background: rgba(140, 161, 154, 120);
}}
QFrame#freightRarityLine[rarity="uncommon"] {{
    background: rgba(107, 188, 132, 150);
}}
QFrame#freightRarityLine[rarity="rare"] {{
    background: rgba(92, 158, 220, 155);
}}
QFrame#freightRarityLine[rarity="epic"] {{
    background: rgba(178, 120, 226, 160);
}}
QFrame#freightRarityLine[rarity="legendary"] {{
    background: rgba(230, 172, 82, 170);
}}
QFrame#freightSelectionCard {{
    background: rgba(21, 29, 33, 214);
    border: 1px solid rgba(110, 128, 122, 112);
    border-radius: 8px;
}}
QFrame#freightSelectionCard:hover, QFrame#freightSelectionCard:focus {{
    background: rgba(26, 36, 40, 230);
    border-color: rgba(150, 176, 168, 166);
}}
QFrame#freightAssignmentResourceTile, QFrame#freightDestinationTile, QFrame#freightContractAssignmentTile {{
    background: rgba(21, 29, 33, 214);
    border: 1px solid rgba(110, 128, 122, 112);
    border-radius: 8px;
}}
QFrame#freightAssignmentResourceTile:hover, QFrame#freightAssignmentResourceTile:focus, QFrame#freightDestinationTile:hover, QFrame#freightDestinationTile:focus {{
    background: rgba(26, 36, 40, 230);
    border-color: rgba(150, 176, 168, 166);
}}
QFrame#freightDestinationTile[destinationKind="market"] {{
    border-left: 3px solid rgba(214, 243, 106, 150);
}}
QFrame#freightDestinationTile[destinationKind="contract"] {{
    border-left: 3px solid rgba(168, 182, 255, 150);
}}
QFrame#freightAssignmentReservePanel, QFrame#freightAssignmentContractPanel {{
    background: rgba(255, 255, 255, 5);
    border: 1px solid rgba(140, 161, 154, 58);
    border-radius: 8px;
}}
QFrame#freightExpansionRow {{
    background: rgba(255, 255, 255, 5);
    border: 1px solid rgba(140, 161, 154, 58);
    border-radius: 8px;
}}
QFrame#freightHoverInfo {{
    background: rgba(23, 33, 40, 238);
    border: 1px solid #3d5361;
    border-radius: 8px;
}}
QFrame#cardHoverInfo, QFrame#supplyCardHoverInfo {{
    background: rgba(23, 33, 40, 238);
    border: 1px solid #3d5361;
    border-radius: 8px;
}}
QFrame#inventoryActionPanel {{
    background: rgba(255, 255, 255, 5);
    border: 1px solid rgba(140, 161, 154, 58);
    border-radius: 8px;
}}
QFrame#craftSelectionPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d3d2c8, stop:0.42 #9fa49b, stop:1 #565d59);
    border: 2px solid rgba(54, 58, 54, 184);
    border-radius: 16px;
}}
QFrame#mkUpgradePanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d3d2c8, stop:0.42 #9fa49b, stop:1 #565d59);
    border: 2px solid rgba(54, 58, 54, 184);
    border-radius: 16px;
}}
QFrame#craftPreviewPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(52, 57, 55, 248), stop:0.46 rgba(20, 25, 25, 252), stop:1 rgba(6, 8, 8, 255));
    border: 2px solid rgba(142, 154, 150, 82);
    border-radius: 14px;
}}
QFrame#mkUpgradeResultPanel, QFrame#mkUpgradeComparePanel, QFrame#mkUpgradeCostPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(52, 57, 55, 248), stop:0.46 rgba(20, 25, 25, 252), stop:1 rgba(6, 8, 8, 255));
    border: 2px solid rgba(142, 154, 150, 82);
    border-radius: 14px;
}}
QFrame#mkUpgradeCurrentCard, QFrame#mkUpgradeTargetCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 14), stop:0.5 rgba(7, 10, 10, 118), stop:1 rgba(0, 0, 0, 116));
    border: 1px solid rgba(158, 176, 180, 86);
    border-radius: 10px;
}}
QFrame#mkUpgradeCompareRow {{
    background: rgba(255, 255, 255, 7);
    border: 1px solid rgba(158, 176, 180, 48);
    border-radius: 6px;
    min-height: 26px;
}}
QFrame#mkUpgradeConnector {{
    background: transparent;
    border: 0;
    min-width: 66px;
}}
QFrame#mkUpgradeConfirmZone {{
    background: rgba(255, 255, 255, 7);
    border: 1px solid rgba(158, 176, 180, 64);
    border-radius: 8px;
}}
QLabel#mkUpgradeConnectorText {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#mkUpgradeConnectorArrow {{
    background: transparent;
    color: #ffd21f;
    font-size: 22px;
    font-weight: 900;
}}
QLabel#mkUpgradeSectionLabel, QLabel#mkUpgradeCompareLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#mkUpgradeCompareValue {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#mkUpgradeCompareArrow {{
    background: transparent;
    color: {Theme.RESOURCE};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#mkUpgradePlaceholder {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 12px;
    font-weight: 800;
}}
QFrame#craftTargetPreview, QFrame#craftMaterialSlots {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 14), stop:0.5 rgba(7, 10, 10, 118), stop:1 rgba(0, 0, 0, 116));
    border: 1px solid rgba(158, 176, 180, 86);
    border-radius: 10px;
}}
QFrame#craftMaterialSlot {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 10), stop:0.55 rgba(9, 12, 12, 176), stop:1 rgba(0, 0, 0, 150));
    border: 1px dashed rgba(158, 176, 180, 90);
    border-radius: 7px;
    min-width: 58px;
    min-height: 106px;
}}
QFrame#craftMaterialSlot[filled="true"] {{
    border-style: solid;
    border-color: rgba(255, 210, 31, 142);
    background: rgba(255, 210, 31, 16);
}}
QLabel#craftSectionTitle {{
    background: transparent;
    color: #f3f6ed;
    font-size: 15px;
    font-weight: 900;
}}
QLabel#craftMaterialCount {{
    background: transparent;
    color: #ffd21f;
    font-size: 12px;
    font-weight: 900;
}}
QLabel#craftEmptyState, QLabel#craftPreviewHint, QLabel#craftPreviewTargetText, QLabel#craftMaterialSlotLabel, QLabel#craftOutputPreview {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 750;
}}
QFrame#freightSelectionCard[freightFamily="truck"] {{
    border-left: 3px solid rgba(107, 188, 132, 180);
}}
QFrame#freightSelectionCard[freightFamily="train"] {{
    border-left: 3px solid rgba(98, 166, 202, 180);
}}
QFrame#freightSelectionCard[freightFamily="ship"] {{
    border-left: 3px solid rgba(106, 165, 200, 180);
}}
QFrame#freightSelectionCard[freightFamily="aircraft"] {{
    border-left: 3px solid rgba(155, 184, 239, 180);
}}
QFrame#freightSelectionFilters {{
    background: transparent;
    border: 0;
}}
QLabel#freightSelectionName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#freightSelectionRarity, QLabel#freightSelectionMeta {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 850;
}}
QLabel#freightAssignmentStepTitle, QLabel#freightDestinationTileTitle, QLabel#freightContractAssignmentName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#freightDestinationTileBody, QLabel#freightAssignmentHint, QLabel#freightAssignmentEmptyState, QLabel#freightContractAssignmentDetail {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 750;
}}
QLabel#freightAssignmentTileName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#freightAssignmentTileMeta {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 800;
}}
QLabel#freightAssignmentReserveValue {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 18px;
    font-weight: 900;
}}
QLabel#freightExpansionTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#freightExpansionProgress, QLabel#freightExpansionNext {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#freightHoverTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#freightHoverLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#freightHoverValue {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 750;
}}
QLabel#cardHoverTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#cardHoverLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#cardHoverValue {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 750;
}}
QLabel#freightSelectionFamily {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#freightSelectionTarget, QLabel#freightSelectionEmpty {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 12px;
    font-weight: 800;
}}
QFrame#packOpenedCardTile[selected="true"] {{
    border-color: {Theme.RESOURCE};
}}
QFrame#packOpenedCardTile[rarity="uncommon"] {{
    border-color: {Theme.GOOD};
}}
QFrame#packOpenedCardTile[rarity="rare"] {{
    border-color: {Theme.ENERGY};
}}
QFrame#packOpenedCardTile[rarity="epic"] {{
    border-color: #b98cff;
}}
QFrame#packOpenedCardTile[rarity="legendary"] {{
    border-color: {Theme.WARN};
}}
QWidget#cardInventoryGrid, QWidget#craftTargetGrid, QWidget#craftMaterialGrid, QWidget#mkUpgradeCardGrid {{
    background: transparent;
}}
QScrollArea#inventoryFilterScroll, QScrollArea#craftTargetFilterScroll, QScrollArea#craftMaterialFilterScroll, QScrollArea#mkUpgradeFilterScroll, QScrollArea#chartFilterScroll, QScrollArea#marketFilterScroll {{
    background: transparent;
    border: 0;
}}
QLabel#sectionLabel {{
    color: {Theme.MUTED};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 10px;
    font-weight: 900;
}}
QFrame#productionGuideFilters {{
    background: transparent;
    border: 0;
}}
QFrame#productionGuideTile {{
    background: rgba(21, 29, 33, 214);
    border: 1px solid rgba(110, 128, 122, 112);
    border-radius: 8px;
}}
QFrame#productionGuideTile:hover, QFrame#productionGuideTile:focus {{
    background: rgba(26, 36, 40, 230);
    border-color: rgba(150, 176, 168, 166);
}}
QFrame#productionGuideTile[stageAccent="extractor"] {{
    border-left: 3px solid rgba(107, 188, 132, 190);
}}
QFrame#productionGuideTile[stageAccent="processor"] {{
    border-left: 3px solid rgba(98, 166, 202, 190);
}}
QFrame#productionGuideTile[stageAccent="fabricator"] {{
    border-left: 3px solid rgba(177, 141, 222, 190);
}}
QFrame#productionGuideTile[stageAccent="assembler"] {{
    border-left: 3px solid rgba(219, 154, 98, 190);
}}
QLabel#productionGuideTileName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#productionGuideTileStage {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 850;
}}
QLabel#productionGuideTileCategory {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 750;
}}
QLabel#productionGuideEmpty, QLabel#chainInspectorEmpty {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 13px;
    font-weight: 800;
    padding: 20px;
}}
QFrame#chainStagePanel {{
    background: rgba(255, 255, 255, 4);
    border: 1px solid rgba(140, 161, 154, 64);
    border-radius: 8px;
}}
QLabel#chainStageTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 900;
}}
QFrame#chainStageRule {{
    background: rgba(140, 161, 154, 94);
    border: 0;
    max-height: 1px;
}}
QFrame#chainStageRule[stageAccent="extractor"] {{
    background: rgba(107, 188, 132, 150);
}}
QFrame#chainStageRule[stageAccent="processor"] {{
    background: rgba(98, 166, 202, 150);
}}
QFrame#chainStageRule[stageAccent="fabricator"] {{
    background: rgba(177, 141, 222, 150);
}}
QFrame#chainStageRule[stageAccent="assembler"] {{
    background: rgba(219, 154, 98, 150);
}}
QFrame#chainResourceBox {{
    background: rgba(21, 29, 33, 196);
    border: 1px solid rgba(110, 128, 122, 104);
    border-radius: 8px;
}}
QFrame#chainResourceBox[target="true"] {{
    border-color: rgba(244, 201, 93, 150);
}}
QFrame#chainResourceBox[stageAccent="extractor"] {{
    border-left: 3px solid rgba(107, 188, 132, 175);
}}
QFrame#chainResourceBox[stageAccent="processor"] {{
    border-left: 3px solid rgba(98, 166, 202, 175);
}}
QFrame#chainResourceBox[stageAccent="fabricator"] {{
    border-left: 3px solid rgba(177, 141, 222, 175);
}}
QFrame#chainResourceBox[stageAccent="assembler"] {{
    border-left: 3px solid rgba(219, 154, 98, 175);
}}
QLabel#chainResourceName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#chainMachineFamily {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 800;
}}
QLabel#chainResourceAmount {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 11px;
    font-weight: 850;
}}
QFrame#chainFlowConnector {{
    background: transparent;
    border: 0;
}}
QLabel#factoryNavTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 24px;
    font-weight: 900;
}}
QLabel#factoryV2NavTitle {{
    background: transparent;
    color: #090a08;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 42px;
    font-weight: 900;
}}
QLabel#factoryNavSubtitle {{
    background: transparent;
    color: {Theme.ENERGY};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#factoryV2NavSubtitle {{
    background: transparent;
    color: {Theme.WARN};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 16px;
    font-weight: 900;
}}
QLabel#hallCommandLabel {{
    background: transparent;
    color: {Theme.ENERGY};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#hallSlotCount {{
    background: transparent;
    color: {Theme.CASH};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#freightKpiValue {{
    color: {Theme.CASH};
    font-size: 18px;
    font-weight: 800;
}}
QLabel#freightNavTitle {{
    background: transparent;
    color: #10120f;
    font-size: 27px;
    font-weight: 900;
}}
QLabel#freightNavSubtitle {{
    background: transparent;
    color: #b6241d;
    font-size: 11px;
    font-weight: 900;
}}
QLabel#freightFacilityTitle, QLabel#freightCardName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 800;
}}
QLabel#freightFacilityTitle {{
    color: #f3f5ed;
    font-size: 34px;
    font-weight: 900;
}}
QLabel#freightFacilityTypeLabel, QLabel#freightSlotUsage {{
    background: transparent;
    color: #d9ded4;
    font-size: 13px;
    font-weight: 900;
}}
QLabel#freightEmptySlot, QLabel#freightMetaLabel {{
    background: transparent;
    color: {Theme.SAFETY_YELLOW};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#freightEmptyIcon {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 28px;
    font-weight: 900;
}}
QLabel#freightEmptyAction {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#freightSlotNumber, QLabel#freightCardClass, QLabel#freightCardRarity {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 850;
}}
QLabel#freightBayPlate {{
    background: #bd2f23;
    color: #fff8ed;
    border: 2px solid rgba(8, 8, 7, 220);
    border-radius: 5px;
    padding: 5px 16px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 20px;
    font-weight: 900;
}}
QLabel#freightBayStatus {{
    background: rgba(13, 17, 16, 232);
    color: {Theme.GOOD};
    border: 1px solid rgba(117, 130, 138, 150);
    border-radius: 5px;
    padding: 5px 12px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#freightStatLabel {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#freightStatusLabel {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 10px;
    font-weight: 800;
}}
QLabel#freightStatusLabel[status="in_transit"] {{
    color: {Theme.RESOURCE};
}}
QLabel#freightStatusLabel[status="ready"] {{
    color: {Theme.GOOD};
}}
QLabel#freightReserveLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 850;
}}
QFrame#freightAssignmentPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 246, 22), stop:0.48 rgba(7, 10, 10, 168), stop:1 rgba(0, 0, 0, 128));
    border: 1px solid rgba(255, 210, 31, 82);
    border-radius: 5px;
}}
QFrame#freightAssignmentPanel[paintedFreightControl="true"] {{
    background: transparent;
    border: none;
}}
QLabel#freightAssignmentResource {{
    background: transparent;
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#freightReserveSummary {{
    background: transparent;
    color: {Theme.MUTED};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 9px;
    font-weight: 800;
}}
QLabel#freightAssignmentDestination, QLabel#freightAssignmentArrow, QLabel#freightAssignmentEmpty {{
    background: transparent;
    color: {Theme.SAFETY_YELLOW};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#lineHeader {{
    background: transparent;
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#lineNumberBadge {{
    color: {Theme.ENERGY};
    font-family: {Theme.INDUSTRIAL_FONT};
    background: rgba(98, 190, 232, 18);
    border: 1px solid rgba(98, 190, 232, 68);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 900;
}}
QFrame#lineHeaderRule {{
    color: rgba(98, 190, 232, 54);
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(98, 190, 232, 62), stop:0.62 rgba(159, 178, 173, 28), stop:1 rgba(159, 178, 173, 0));
    border: 0;
    max-height: 2px;
}}
QLabel#lineLockedBadge {{
    color: {Theme.WARN};
    background: rgba(244, 201, 93, 22);
    border: 1px solid {Theme.BORDER};
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 9px;
    font-weight: 900;
}}
QLabel#lockedLine {{
    color: {Theme.DIM};
    background: transparent;
    border: 0;
    padding: 4px;
}}
QFrame#lockedLinePanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(242, 194, 91, 32), stop:0.55 rgba(36, 35, 24, 120), stop:1 rgba(98, 190, 232, 10));
    border: 1px solid rgba(242, 194, 91, 112);
    border-radius: 11px;
    min-height: 44px;
    max-height: 58px;
}}
QFrame#lockedLinePanel:hover, QFrame#lockedLinePanel:focus {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(242, 194, 91, 45), stop:1 rgba(98, 190, 232, 16));
    border-color: rgba(242, 194, 91, 140);
}}
QFrame#lockedLinePanel[factoryV2="true"], QFrame#lockedLinePanel[factoryV2="true"]:hover, QFrame#lockedLinePanel[factoryV2="true"]:focus {{
    background: transparent;
    border: 0;
    min-height: 104px;
    max-height: none;
}}
QLabel#lockedLineName {{
    color: {Theme.TEXT};
    background: transparent;
    font-size: 11px;
    font-weight: 900;
}}
QLabel#lockedLineDetail {{
    color: {Theme.MUTED};
    background: transparent;
    font-size: 11px;
    font-weight: 800;
}}
QLabel#lockedLineAction {{
    color: {Theme.CASH};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(216, 240, 106, 24), stop:1 rgba(98, 190, 232, 12));
    border: 1px solid rgba(216, 240, 106, 78);
    border-radius: 7px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 900;
}}
QFrame#lockedSlotPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(242, 194, 91, 28), stop:0.52 rgba(20, 20, 16, 150), stop:1 rgba(98, 190, 232, 8));
    border: 1px solid rgba(242, 194, 91, 92);
    border-radius: 10px;
}}
QFrame#lockedSlotPanel:hover, QFrame#lockedSlotPanel:focus {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(242, 194, 91, 40), stop:1 rgba(98, 190, 232, 13));
    border-color: rgba(242, 194, 91, 128);
}}
QLabel#lockedSlotIcon {{
    color: {Theme.WARN};
    background: rgba(242, 194, 91, 19);
    border: 1px solid rgba(242, 194, 91, 66);
    border-radius: 8px;
    padding: 4px;
    font-size: 11px;
    font-weight: 900;
}}
QLabel#lockedSlotTitle {{
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#lockedSlotHint {{
    color: {Theme.MUTED};
    font-size: 8px;
    font-weight: 900;
}}
QLabel#lockedSlotPrice {{
    color: {Theme.CASH};
    background: rgba(216, 240, 106, 16);
    border: 1px solid rgba(216, 240, 106, 34);
    border-radius: 6px;
    padding: 3px;
    font-size: 13px;
    font-weight: 900;
}}
QFrame#hallResourceSummaryItem {{
    background: rgba(255, 255, 255, 6);
    border: 1px solid #2f3b43;
    border-radius: 6px;
}}
QFrame#hallResourceSummaryItem[factoryV2Utility="true"] {{
    background: transparent;
    border: 0;
}}
QLabel#hallResourceName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#hallResourceAmount {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 700;
}}
QLabel#hallResourceNet[netState="positive"] {{
    background: transparent;
    color: {Theme.GOOD};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#hallResourceNet[netState="negative"] {{
    background: transparent;
    color: {Theme.BAD};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#hallResourceNet[netState="neutral"] {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QPushButton#chainInfoButton {{
    background: transparent;
    color: {Theme.RESOURCE};
    border: 1px solid rgba(168, 182, 255, 55);
    border-radius: 10px;
    padding: 0;
    font-size: 10px;
    font-weight: 900;
}}
QProgressBar#hallResourceStorageProgress {{
    background: rgba(255, 255, 255, 18);
    border: 1px solid rgba(143, 180, 255, 36);
    border-radius: 3px;
}}
QProgressBar#hallResourceStorageProgress::chunk {{
    background: {Theme.RESOURCE};
    border-radius: 2px;
}}
QProgressBar#hallResourceStorageProgress[storageState="full"]::chunk {{
    background: {Theme.WARN};
}}
QProgressBar#hallResourceStorageProgress[storageState="empty"]::chunk {{
    background: {Theme.DIM};
}}
QFrame#factoryCardHoverInfo {{
    background: rgba(23, 33, 40, 238);
    border: 1px solid #3d5361;
    border-radius: 8px;
}}
QLabel#factoryHoverTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#factoryHoverLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#factoryHoverValue {{
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 700;
    background: transparent;
}}
QFrame#contractsHeader {{
    background: transparent;
    border: 0;
}}
QFrame#contractsHeaderMetric {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(34, 45, 39, 238), stop:0.55 rgba(12, 18, 16, 246), stop:1 rgba(5, 7, 6, 255));
    border: 1px solid rgba(101, 216, 143, 126);
    border-radius: 8px;
}}
QScrollArea#contractsBoardScroll {{
    background: transparent;
    border: 0;
}}
QWidget#contractsBoard {{
    background: transparent;
}}
QFrame#contractPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(36, 42, 40, 238), stop:0.55 rgba(14, 19, 18, 248), stop:1 rgba(7, 9, 8, 255));
    border: 1px solid rgba(142, 154, 150, 82);
    border-radius: 10px;
}}
QFrame#contractPanel[kind="regular"] {{
    border-top: 2px solid rgba(140, 161, 154, 145);
}}
QFrame#contractPanel[kind="daily"] {{
    border-top: 2px solid rgba(93, 183, 220, 170);
}}
QFrame#contractPanel[kind="weekly"] {{
    border-top: 2px solid rgba(218, 184, 92, 190);
}}
QFrame#contractOfferPanel, QFrame#contractActivePanel, QFrame#contractCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(35, 42, 41, 232), stop:0.56 rgba(13, 19, 19, 244), stop:1 rgba(5, 8, 8, 252));
    border: 1px solid rgba(112, 130, 124, 118);
    border-radius: 8px;
}}
QFrame#contractCard[kind="regular"] {{
    border-color: rgba(140, 161, 154, 122);
}}
QFrame#contractCard[kind="daily"] {{
    border-color: rgba(93, 183, 220, 145);
}}
QFrame#contractCard[kind="weekly"] {{
    border-color: rgba(218, 184, 92, 168);
}}
QFrame#contractCard[state="active"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(38, 48, 48, 240), stop:1 rgba(8, 15, 16, 255));
    border-color: {Theme.RESOURCE};
}}
QFrame#contractCard[state="disabled"] {{
    border-color: {Theme.DIM};
    background: rgba(18, 24, 27, 176);
}}
QFrame#contractCard[state="completed"] {{
    background: rgba(26, 40, 36, 226);
    border-color: {Theme.GOOD};
}}
QFrame#contractCard[state="expired"] {{
    border-color: {Theme.BAD};
}}
QFrame#contractRequirements {{
    background: transparent;
    border: 0;
}}
QFrame#contractRewards {{
    background: transparent;
    border: 0;
}}
QFrame#contractActionFooter {{
    background: transparent;
    border: 0;
}}
QFrame#contractRequirementRow {{
    background: transparent;
    border: 0;
    min-height: 20px;
}}
QFrame#contractRequirementsInline {{
    background: transparent;
    border: 0;
}}
QFrame#contractRewardChip {{
    background: rgba(255, 255, 255, 7);
    border: 1px solid rgba(255, 255, 255, 18);
    border-radius: 5px;
}}
QFrame#contractRewardChip[rewardKind="cash"] {{
    border-color: rgba(94, 206, 139, 96);
}}
QFrame#contractRewardChip[rewardKind="xp"] {{
    border-color: rgba(93, 183, 220, 96);
}}
QFrame#contractRewardChip[rewardKind="pack"] {{
    border-color: rgba(218, 184, 92, 118);
    background: rgba(218, 184, 92, 18);
}}
QFrame#resourceRow, QFrame#resourceRowExpanded {{
    background: {Theme.PANEL_ALT};
    border: 1px solid {Theme.BORDER};
    border-radius: 5px;
}}
QFrame#chartResourceCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(37, 46, 45, 238), stop:0.54 rgba(15, 22, 22, 246), stop:1 rgba(6, 9, 9, 252));
    border: 1px solid rgba(110, 128, 122, 128);
    border-radius: 8px;
}}
QFrame#chartResourceCard:hover, QFrame#chartResourceCard:focus {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(45, 55, 53, 242), stop:0.54 rgba(17, 27, 28, 250), stop:1 rgba(7, 12, 13, 255));
    border-color: rgba(150, 176, 168, 166);
}}
QFrame#chartResourceIconHost, QFrame#chartDetailIconHost {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(37, 185, 232, 82);
    border-radius: 7px;
}}
QFrame#marketCard, QFrame#marketEventCard, QFrame#marketDetailSummary, QFrame#marketChartPanel {{
    background: {Theme.PANEL_ALT};
    border: 1px solid {Theme.BORDER};
    border-radius: 7px;
}}
QFrame#marketDetailSummary, QFrame#marketChartPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(35, 42, 41, 232), stop:0.56 rgba(13, 19, 19, 244), stop:1 rgba(5, 8, 8, 252));
    border: 1px solid rgba(142, 128, 86, 92);
    border-radius: 10px;
}}
QTableView#marketTableView {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(26, 29, 27, 236), stop:1 rgba(8, 10, 9, 248));
    border: 1px solid rgba(142, 128, 86, 92);
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: rgba(255, 210, 31, 40);
    selection-color: {Theme.TEXT};
}}
QTableView#marketTableView::item {{
    background: transparent;
    border: 0;
    outline: 0;
}}
QTableView#marketTableView::item:selected {{
    background: rgba(255, 210, 31, 36);
    color: {Theme.TEXT};
}}
QTableView#marketTableView QHeaderView::section {{
    background: rgba(14, 15, 13, 244);
    color: {Theme.MUTED};
    border: 0;
    border-bottom: 1px solid rgba(255, 210, 31, 72);
    padding: 7px 10px;
    font-size: 10px;
    font-weight: 900;
}}
QFrame#marketRow {{
    background: transparent;
    border: 0;
    border-bottom: 1px solid rgba(132, 151, 145, 42);
    min-height: 44px;
    max-height: 52px;
}}
QFrame#marketRow:hover {{
    background: rgba(255, 255, 255, 12);
}}
QFrame#marketRow[eventAffected="true"] {{
    border-left: 2px solid {Theme.ENERGY};
}}
QFrame#marketRow[change="positive"] {{
    border-bottom-color: rgba(82, 184, 137, 88);
}}
QFrame#marketRow[change="negative"] {{
    border-bottom-color: rgba(214, 100, 96, 88);
}}
QFrame#supplyStoreHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(31, 35, 34, 238), stop:0.58 rgba(18, 22, 22, 245), stop:1 rgba(78, 61, 25, 210));
    border: 1px solid rgba(255, 210, 31, 84);
    border-radius: 12px;
}}
QFrame#supplyHeaderMetric {{
    background: rgba(5, 7, 7, 126);
    border: 1px solid rgba(255, 255, 255, 34);
    border-radius: 7px;
    min-width: 116px;
}}
QFrame#supplySectionHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(34, 37, 35, 224), stop:1 rgba(16, 18, 18, 232));
    border: 1px solid rgba(159, 178, 173, 48);
    border-radius: 9px;
}}
QFrame#supplyDailyPage {{
    border-left: 2px solid rgba(93, 183, 220, 150);
}}
QFrame#supplyDailyRecipeSection, QFrame#supplyDailyFreightSection, QFrame#supplyDailyMachineSection {{
    background: rgba(255, 255, 255, 6);
    border: 1px solid rgba(159, 178, 173, 34);
    border-radius: 9px;
}}
QScrollArea#supplyDailyScroll, QWidget#supplyDailyContent {{
    background: transparent;
    border: 0;
}}
QFrame#supplyCommonPage {{
    border-left: 2px solid rgba(140, 161, 154, 120);
}}
QFrame#commonSupplyCard {{
    background: transparent;
    border: 0;
}}
QFrame#dailySupplyCard, QFrame#dailyFreightSupplyCard, QFrame#dailyMachineSupplyCard {{
    background: transparent;
    border: 0;
}}
QFrame#commonSupplyCard:hover {{
    background: transparent;
    border: 0;
}}
QFrame#dailySupplyCard:hover, QFrame#dailyFreightSupplyCard:hover, QFrame#dailyMachineSupplyCard:hover {{
    background: transparent;
    border: 0;
}}
QFrame#supplyCardStats {{
    background: transparent;
    border: 0;
}}
QFrame#supplyCardHeader {{
    background: transparent;
    border: 0;
}}
QFrame#supplyCardTitleRow {{
    background: transparent;
    border: 0;
}}
QFrame#supplyCardIconHost {{
    background: transparent;
    border: 0;
}}
QFrame#supplyRarityLine[rarity="common"] {{
    background: rgba(140, 161, 154, 160);
}}
QFrame#supplyRarityLine[rarity="uncommon"] {{
    background: rgba(88, 214, 141, 180);
}}
QFrame#supplyRarityLine[rarity="rare"] {{
    background: rgba(93, 183, 220, 190);
}}
QFrame#supplyRarityLine[rarity="epic"] {{
    background: rgba(168, 139, 255, 190);
}}
QFrame#supplyRarityLine[rarity="legendary"] {{
    background: rgba(244, 201, 93, 200);
}}
QFrame#boosterPackTile {{
    background: transparent;
    border: 0;
}}
QFrame#boosterPackTile:hover {{
    background: transparent;
    border: 0;
}}
QFrame#boosterPackTile[packType="full"] {{
    border: 0;
}}
QFrame#boosterPackTile[packType="daily_mini"] {{
    border: 0;
}}
QFrame#packsHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(38, 42, 40, 238), stop:0.58 rgba(15, 20, 20, 246), stop:1 rgba(59, 43, 92, 96));
    border: 1px solid rgba(177, 135, 255, 92);
    border-radius: 10px;
}}
QFrame#packsHeaderMetric {{
    background: rgba(7, 10, 10, 132);
    border: 1px solid rgba(177, 135, 255, 84);
    border-radius: 8px;
}}
QFrame#packsUnopenedHeader {{
    background: transparent;
    border-bottom: 1px solid rgba(140, 161, 154, 55);
}}
QFrame#boosterPackArt, QFrame#boosterPackCategoryPanel, QFrame#boosterPackActionZone {{
    background: transparent;
    border: 0;
}}
QFrame#packCategoryFlyout {{
    background: rgba(8, 12, 13, 238);
    border: 1px solid rgba(177, 135, 255, 130);
    border-radius: 7px;
}}
QPushButton#packCategorySelector, QPushButton#packCategoryOption {{
    background: rgba(8, 12, 13, 164);
    border: 1px solid rgba(177, 135, 255, 96);
    border-radius: 6px;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 2px 8px;
}}
QPushButton#packCategorySelector:hover, QPushButton#packCategoryOption:hover {{
    background: rgba(177, 135, 255, 42);
    border-color: rgba(177, 135, 255, 170);
}}
QWidget#leaderboardView {{
    background: transparent;
}}
QFrame#leaderboardPageHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(35, 40, 39, 238), stop:0.58 rgba(13, 18, 18, 246), stop:1 rgba(44, 34, 16, 190));
    border: 1px solid rgba(218, 184, 92, 92);
    border-radius: 10px;
}}
QFrame#leaderboardHeaderMetric {{
    background: rgba(6, 9, 9, 145);
    border: 1px solid rgba(218, 184, 92, 92);
    border-radius: 8px;
}}
QFrame#leaderboardSwitchDeck {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 23, 23, 246), stop:0.55 rgba(9, 13, 13, 252), stop:1 rgba(22, 18, 12, 246));
    border: 1px solid rgba(142, 154, 150, 72);
    border-radius: 10px;
}}
QTabWidget#leaderboardTabs {{
    background: transparent;
    border: 0;
}}
QTabWidget#leaderboardTabs::pane {{
    background: transparent;
    border: 0;
}}
QWidget#leaderboardRankingPage {{
    background: transparent;
}}
QScrollArea#company_levelLeaderboardScroll, QScrollArea#total_earningsLeaderboardScroll {{
    background: transparent;
    border: 0;
}}
QWidget#company_levelLeaderboardContent, QWidget#total_earningsLeaderboardContent {{
    background: transparent;
}}
QFrame#leaderboardRow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(34, 40, 39, 232), stop:0.54 rgba(13, 18, 18, 245), stop:1 rgba(7, 9, 9, 252));
    border: 1px solid rgba(112, 130, 124, 112);
    border-radius: 8px;
}}
QFrame#leaderboardRow:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(42, 50, 49, 238), stop:0.54 rgba(16, 23, 23, 250), stop:1 rgba(9, 13, 13, 255));
    border-color: rgba(159, 178, 173, 154);
}}
QFrame#leaderboardRow[rankTier="gold"] {{
    border-left: 3px solid rgba(244, 201, 93, 215);
    border-color: rgba(244, 201, 93, 155);
}}
QFrame#leaderboardRow[rankTier="silver"] {{
    border-left: 3px solid rgba(184, 208, 216, 196);
    border-color: rgba(184, 208, 216, 132);
}}
QFrame#leaderboardRow[rankTier="bronze"] {{
    border-left: 3px solid rgba(199, 121, 73, 198);
    border-color: rgba(199, 121, 73, 128);
}}
QFrame#leaderboardRow[ownPlayer="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(22, 46, 49, 238), stop:0.55 rgba(10, 21, 23, 252), stop:1 rgba(6, 11, 12, 255));
    border-color: rgba(37, 185, 232, 176);
}}
QFrame#ownLeaderboardPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(31, 36, 35, 238), stop:0.56 rgba(12, 17, 17, 246), stop:1 rgba(8, 11, 11, 252));
    border: 1px solid rgba(37, 185, 232, 92);
    border-radius: 9px;
}}
QFrame#leaderboardFooterMetric {{
    background: transparent;
    border: 0;
}}
QFrame#dailySupplyCard[state="available"], QFrame#dailyFreightSupplyCard[state="available"], QFrame#dailyMachineSupplyCard[state="available"] {{
    border: 0;
}}
QFrame#dailySupplyCard[state="purchased"], QFrame#dailyFreightSupplyCard[state="purchased"], QFrame#dailyMachineSupplyCard[state="purchased"] {{
    background: transparent;
    border: 0;
}}
QFrame#dailySupplyCard[state="locked"], QFrame#dailyFreightSupplyCard[state="locked"], QFrame#dailyMachineSupplyCard[state="locked"] {{
    background: transparent;
    border: 0;
}}
QFrame#marketCard[change="positive"] {{
    border-color: {Theme.GOOD};
}}
QFrame#marketCard[change="negative"] {{
    border-color: {Theme.BAD};
}}
QFrame#marketCard[change="neutral"] {{
    border-color: {Theme.BORDER};
}}
QFrame#marketCard[eventAffected="true"] {{
    background: #182229;
}}
QFrame#chartResourceCard[status="rising"] {{
    border-color: {Theme.GOOD};
}}
QFrame#chartResourceCard[status="falling"] {{
    border-color: {Theme.BAD};
}}
QFrame#chartResourceCard[status="neutral"] {{
    border-color: {Theme.BORDER};
}}
QFrame#resourceRowExpanded {{
    border-color: {Theme.RESOURCE};
}}
QLabel#resourceRowName {{
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 700;
}}
QLabel#chartResourceName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 14px;
    font-weight: 900;
}}
QLabel#marketCardName, QLabel#marketEventName {{
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 800;
}}
QLabel#marketEventName {{
    font-size: 15px;
    font-weight: 900;
}}
QLabel#marketColumnHeader {{
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 0px;
}}
QLabel#marketRowResourceName {{
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 800;
}}
QLabel#marketRowPrice {{
    color: {Theme.CASH};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#marketRowChange24h, QLabel#marketRowChange7d, QLabel#marketRowChange30d, QLabel#marketRowTrend, QLabel#marketRowAnchor, QLabel#marketRowEvent {{
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#marketRowChange24h[change="positive"], QLabel#marketRowChange7d[change="positive"], QLabel#marketRowChange30d[change="positive"], QLabel#marketRowTrend[change="positive"], QLabel#marketDetailChange[change="positive"] {{
    color: {Theme.GOOD};
}}
QLabel#marketRowChange24h[change="negative"], QLabel#marketRowChange7d[change="negative"], QLabel#marketRowChange30d[change="negative"], QLabel#marketRowTrend[change="negative"], QLabel#marketDetailChange[change="negative"] {{
    color: {Theme.BAD};
}}
QLabel#marketRowEvent {{
    color: {Theme.ENERGY};
}}
QLabel#marketDetailMetricLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#supplyStoreTitle {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 24px;
    font-weight: 900;
}}
QLabel#supplyStoreSubtitle {{
    background: transparent;
    border: 0;
    color: #d23f30;
    font-size: 11px;
    font-weight: 900;
}}
QLabel#supplyHeaderMetricLabel {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#supplyHeaderMetricValue {{
    background: transparent;
    border: 0;
    color: {Theme.ENERGY};
    font-size: 15px;
    font-weight: 900;
}}
QLabel#supplySectionTitle {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 14px;
    font-weight: 900;
}}
QLabel#supplySectionSubtitle {{
    background: transparent;
    border: 0;
    color: {Theme.ENERGY};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#supplyDailySectionTitle {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#supplyDailySectionSubtitle {{
    background: transparent;
    border: 0;
    color: {Theme.ENERGY};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#supplyCommonStatus {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#supplyCardName {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#packsHeaderTitle {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 18px;
    font-weight: 900;
}}
QLabel#packsHeaderSubtitle, QLabel#packsUnopenedCount {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#packsHeaderMetricLabel {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#packsHeaderMetricValue {{
    background: transparent;
    border: 0;
    color: {Theme.ENERGY};
    font-size: 18px;
    font-weight: 900;
}}
QLabel#packsSectionTitle, QLabel#boosterPackName, QLabel#packOpenedCardName {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#boosterPackType, QLabel#boosterPackCardCount, QLabel#boosterPackCategoryInfo, QLabel#boosterPackArtLabel, QLabel#packsEmptyState {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#boosterPackSource {{
    background: transparent;
    border: 0;
    color: {Theme.DIM};
    font-size: 10px;
    font-weight: 700;
}}
QLabel#boosterPackCategoryLabel {{
    background: transparent;
    border: 0;
    color: {Theme.DIM};
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 1px;
}}
QLabel#boosterPackQuantity {{
    background: transparent;
    border: 0;
    color: {Theme.CASH};
    font-size: 16px;
    font-weight: 900;
}}
QLabel#packOpenedCardRarity, QLabel#packOpenedCardMeta, QLabel#packOpenedCardBonus {{
    background: transparent;
    border: 0;
    color: {Theme.RESOURCE};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#supplyDailyStatus {{
    background: transparent;
    border: 0;
    color: {Theme.ENERGY};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#supplyFreightDailyStatus {{
    background: transparent;
    border: 0;
    color: {Theme.ENERGY};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#supplyCardMk {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#supplyCardOutput {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#supplyCardPower {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#supplyCardFunction {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#supplyCardRarity {{
    background: transparent;
    border: 0;
    color: {Theme.RESOURCE};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#supplyCardBonus {{
    background: transparent;
    border: 0;
    color: {Theme.RESOURCE};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#supplyCardPrice {{
    background: transparent;
    border: 0;
    color: {Theme.CASH};
    font-size: 18px;
    font-weight: 900;
}}
QLabel#marketCardPrice {{
    color: {Theme.CASH};
    font-size: 18px;
    font-weight: 800;
}}
QLabel#marketDetailPrice {{
    background: transparent;
    border: 0;
    color: {Theme.CASH};
    font-size: 18px;
    font-weight: 900;
}}
QLabel#marketDetailChange {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#marketCardAbsoluteChange, QLabel#marketCardPercentChange, QLabel#marketCardAnchor, QLabel#marketEventAffected, QLabel#marketEventRemaining, QLabel#marketDetailMetric {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 12px;
    font-weight: 800;
}}
QLabel#marketEventAffected {{
    color: {Theme.TEXT};
}}
QLabel#marketEventRemaining {{
    color: {Theme.ENERGY};
    font-weight: 900;
}}
QLabel#marketEventIndicator {{
    color: {Theme.ENERGY};
    font-size: 10px;
    font-weight: 800;
}}
QLabel#chartResourceAmount, QLabel#chartResourceNetChange, QLabel#chartDetailAmount, QLabel#chartDetailNetChange {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 12px;
    font-weight: 800;
}}
QLabel#chartResourceNetChange {{
    font-size: 14px;
    font-weight: 900;
}}
QLabel#chartResourceNetChange[status="rising"], QLabel#chartDetailNetChange[status="rising"] {{
    color: {Theme.GOOD};
}}
QLabel#chartResourceNetChange[status="falling"], QLabel#chartDetailNetChange[status="falling"] {{
    color: {Theme.BAD};
}}
QProgressBar#chartResourceStorageProgress {{
    background: rgba(255, 255, 255, 12);
    border: 1px solid rgba(140, 161, 154, 45);
    border-radius: 3px;
    height: 6px;
}}
QProgressBar#chartResourceStorageProgress::chunk {{
    background: {Theme.RESOURCE};
    border-radius: 3px;
}}
QLabel#chartEmptyState {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 13px;
    font-weight: 800;
}}
QWidget#chartResourceSparkline {{
    background: transparent;
    border: 0;
}}
QLabel#chartDetailTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 15px;
    font-weight: 800;
}}
QLabel#marketDetailTitle {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 15px;
    font-weight: 800;
}}
QFrame#marketDetailIconHost {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(255, 210, 31, 84);
    border-radius: 7px;
}}
QLabel#resourceRowPrice {{
    color: {Theme.CASH};
    font-size: 12px;
    font-weight: 700;
}}
QLabel#resourceRowStorage {{
    color: {Theme.MUTED};
    font-size: 11px;
}}
QProgressBar#resourceStorageProgress {{
    background: {Theme.PANEL};
    border: 1px solid {Theme.BORDER};
    border-radius: 3px;
    height: 7px;
}}
QProgressBar#resourceStorageProgress::chunk {{
    background: {Theme.RESOURCE};
    border-radius: 2px;
}}
QLabel#contractStatus {{
    color: {Theme.MUTED};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#contractsHeroTitle {{
    background: transparent;
    color: #f3f6ed;
    font-size: 38px;
    font-weight: 900;
}}
QLabel#contractsHeroSubtitle {{
    background: transparent;
    color: #d23f30;
    font-size: 12px;
    font-weight: 900;
}}
QLabel#contractsMetricLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#contractsMetricValue {{
    background: transparent;
    color: {Theme.GOOD};
    font-size: 17px;
    font-weight: 900;
}}
QLabel#contractSectionTitle {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#contractSectionSubtitle {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#contractCardTitle {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#contractBlockTitle {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#contractRequirementLabel {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#contractRequirementAmount {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#contractRequirementAmount[fulfilled="true"] {{
    color: {Theme.GOOD};
}}
QLabel#contractRewardLabel {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#contractRewardIcon {{
    background: transparent;
    border: 0;
    color: {Theme.RESOURCE};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#contractCardStatus {{
    background: rgba(255, 255, 255, 10);
    border: 1px solid rgba(255, 255, 255, 22);
    border-radius: 4px;
    padding: 3px 7px;
    color: {Theme.CASH};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#contractCardStatus[state="active"] {{
    color: {Theme.RESOURCE};
    border-color: rgba(93, 183, 220, 92);
}}
QLabel#contractCardStatus[state="completed"] {{
    color: {Theme.GOOD};
    border-color: rgba(94, 206, 139, 94);
}}
QLabel#contractCardStatus[state="disabled"] {{
    color: {Theme.DIM};
    border-color: rgba(88, 98, 101, 84);
}}
QLabel#saleResourceLabel {{
    color: {Theme.TEXT};
    font-size: 11px;
}}
QLabel#cardDetail {{
    color: {Theme.TEXT};
    background: transparent;
    border: 0;
    padding: 0;
}}
QLabel#cardDetailsTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 14px;
    font-weight: 900;
}}
QLabel#cardDetailsEmpty {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 13px;
    font-weight: 800;
    padding: 24px;
}}
QLabel#cardDetailLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#cardDetailValue {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 750;
}}
QLabel#cardDetailsActionText {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 11px;
    font-weight: 850;
}}
QLabel#inventoryActionHint {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#inventoryActionTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#inventoryKpiLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#inventoryHeroTitle, QLabel#chartsHeroTitle, QLabel#marketHeroTitle {{
    background: transparent;
    color: #f3f6ed;
    font-size: 38px;
    font-weight: 900;
}}
QLabel#inventoryHeroSubtitle, QLabel#chartsHeroSubtitle, QLabel#marketHeroSubtitle {{
    background: transparent;
    color: #d23f30;
    font-size: 12px;
    font-weight: 900;
}}
QLabel#inventoryTotalCardsLabel, QLabel#inventoryStacksLabel, QLabel#industrialScrapLabel, QLabel#inventoryStorageLabel {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 20px;
    font-weight: 900;
}}
QLabel#industrialScrapLabel {{
    color: #b8d0d8;
}}
QLabel#chartsMetricLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#chartsMetricValue {{
    background: transparent;
    color: #25b9e8;
    font-size: 20px;
    font-weight: 900;
}}
QLabel#marketMetricLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#marketMetricValue {{
    background: transparent;
    color: {Theme.ENERGY};
    font-size: 16px;
    font-weight: 900;
}}
QLabel#inventoryCardName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#inventoryCardMk, QLabel#inventoryCardQuantity, QLabel#inventoryCardStatus {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 850;
}}
QLabel#inventoryCardRarity, QLabel#inventoryCardBonus {{
    background: transparent;
    color: {Theme.RESOURCE};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#inventoryCardFunction {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#leaderboardHeroTitle {{
    background: transparent;
    color: #f3f6ed;
    font-size: 38px;
    font-weight: 900;
}}
QLabel#leaderboardHeroSubtitle {{
    background: transparent;
    color: #d23f30;
    font-size: 12px;
    font-weight: 900;
}}
QLabel#leaderboardMetricLabel, QLabel#leaderboardFooterLabel, QLabel#leaderboardSwitchLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#leaderboardMetricValue {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 18px;
    font-weight: 900;
}}
QLabel#leaderboardFooterValue {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#leaderboardRank {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(218, 184, 92, 94);
    border-radius: 5px;
    color: {Theme.CASH};
    font-size: 17px;
    font-weight: 900;
    padding: 6px 8px;
}}
QLabel#leaderboardPlayer {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 15px;
    font-weight: 900;
}}
QLabel#leaderboardTitle {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(255, 255, 255, 18);
    border-radius: 4px;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    padding: 2px 6px;
}}
QLabel#leaderboardLevel {{
    background: transparent;
    border: 0;
    color: #b8d0d8;
    font-size: 10px;
    font-weight: 900;
}}
QLabel#leaderboardValue {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 16px;
    font-weight: 900;
}}
QLabel#leaderboardSecondaryValue {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 850;
}}
QLabel#leaderboardYouBadge {{
    background: rgba(37, 185, 232, 24);
    border: 1px solid rgba(37, 185, 232, 130);
    border-radius: 4px;
    color: #25b9e8;
    font-size: 9px;
    font-weight: 900;
    padding: 2px 6px;
}}
QPushButton#leaderboardMetricChip {{
    background: rgba(7, 10, 10, 160);
    border: 1px solid rgba(142, 154, 150, 82);
    border-radius: 6px;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 11px;
}}
QPushButton#leaderboardMetricChip:hover {{
    background: rgba(255, 255, 255, 14);
    border-color: rgba(218, 184, 92, 118);
    color: {Theme.TEXT};
}}
QPushButton#leaderboardMetricChip[active="true"] {{
    background: rgba(218, 184, 92, 34);
    border-color: rgba(244, 201, 93, 178);
    color: {Theme.CASH};
}}
QLineEdit#hallNameEdit {{
    background: {Theme.PANEL};
    color: {Theme.TEXT};
    border: 1px solid {Theme.BORDER};
    border-radius: 5px;
    padding: 8px 10px;
    font-size: 18px;
    font-weight: 700;
}}
QLineEdit#hallNameEdit[factoryHeader="true"] {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 26px;
    font-weight: 900;
    padding: 0;
}}
QTreeWidget#hallTree, QListWidget#inventoryList, QListWidget#cardSelectionList {{
    background: {Theme.PANEL_ALT};
    color: {Theme.TEXT};
    border: 1px solid {Theme.BORDER};
    border-radius: 5px;
    outline: 0;
}}
QTreeWidget#hallTree {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 7), stop:1 rgba(98, 190, 232, 5));
    border: 1px solid rgba(98, 190, 232, 46);
    border-radius: 11px;
    font-size: 13px;
    font-weight: 800;
}}
QTreeWidget#hallTreeV2 {{
    background: rgba(8, 13, 14, 178);
    color: {Theme.TEXT};
    border: 1px solid rgba(48, 59, 62, 142);
    border-radius: 13px;
    outline: 0;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 19px;
    font-weight: 900;
}}
QTreeWidget#freightFacilityTreeV2 {{
    background: rgba(8, 13, 14, 178);
    color: {Theme.TEXT};
    border: 1px solid rgba(48, 59, 62, 142);
    border-radius: 13px;
    outline: 0;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 19px;
    font-weight: 900;
}}
QTableWidget#cardInventoryTable, QTableWidget#marketTable, QTableWidget#packsTable, QTableWidget#resourceDrawerTable {{
    background: {Theme.PANEL_ALT};
    color: {Theme.TEXT};
    gridline-color: {Theme.GRID};
    border: 1px solid {Theme.BORDER};
    border-radius: 5px;
    alternate-background-color: {Theme.PANEL};
}}
QLabel#marketEventLabel {{
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 700;
}}
QHeaderView::section {{
    background: {Theme.PANEL};
    color: {Theme.MUTED};
    border: 1px solid {Theme.BORDER};
    padding: 6px;
    font-weight: 800;
}}
QComboBox {{
    background: {Theme.SURFACE_3};
    color: {Theme.TEXT};
    border: 1px solid {Theme.BORDER};
    border-radius: 7px;
    padding: 6px 10px;
    min-width: 120px;
}}
QCheckBox#autoSellEnabled, QSpinBox#autoSellThreshold {{
    color: {Theme.TEXT};
    background: {Theme.SURFACE_3};
    border: 1px solid {Theme.BORDER};
    border-radius: 7px;
    padding: 4px;
}}
QTreeWidget#hallTree::item, QListWidget#inventoryList::item, QListWidget#cardSelectionList::item {{
    padding: 8px;
}}
QTreeWidget#hallTree::item {{
    padding: 12px 10px;
    margin: 4px 4px;
    border-radius: 9px;
}}
QTreeWidget#hallTreeV2::item {{
    padding: 24px 14px;
    margin: 6px 5px;
    border: 1px solid rgba(35, 37, 35, 218);
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(34, 38, 37, 228), stop:0.58 rgba(13, 17, 17, 238), stop:1 rgba(5, 6, 5, 248));
}}
QTreeWidget#freightFacilityTreeV2::item {{
    padding: 24px 14px;
    margin: 6px 5px;
    border: 1px solid rgba(35, 37, 35, 218);
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(34, 38, 37, 228), stop:0.58 rgba(13, 17, 17, 238), stop:1 rgba(5, 6, 5, 248));
}}
QTreeWidget#hallTree::item:selected, QListWidget#inventoryList::item:selected, QListWidget#cardSelectionList::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(98, 190, 232, 54), stop:1 rgba(216, 240, 106, 18));
    color: {Theme.TEXT};
}}
QTreeWidget#hallTreeV2::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(52, 47, 25, 230), stop:0.58 rgba(15, 17, 15, 242), stop:1 rgba(255, 210, 31, 94));
    border-color: rgba(255, 210, 31, 230);
    color: {Theme.TEXT};
}}
QTreeWidget#freightFacilityTreeV2::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(52, 47, 25, 230), stop:0.58 rgba(15, 17, 15, 242), stop:1 rgba(255, 210, 31, 94));
    border-color: rgba(255, 210, 31, 230);
    color: {Theme.TEXT};
}}
QPushButton#buildHallButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(216, 240, 106, 38), stop:0.52 rgba(98, 190, 232, 20), stop:1 rgba(255, 255, 255, 8));
    color: {Theme.TEXT};
    border: 1px solid rgba(216, 240, 106, 118);
    border-radius: 12px;
    padding: 12px;
    font-weight: 900;
}}
QPushButton#buildHallButtonV2, QPushButton#buildFreightFacilityButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 {Theme.SAFETY_YELLOW}, stop:0.78 #c88f00, stop:1 #111008);
    color: #10120a;
    border: 2px solid rgba(7, 8, 7, 238);
    border-radius: 9px;
    padding: 12px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-weight: 900;
    font-size: 15px;
}}
QPushButton#buildHallButtonV2:hover, QPushButton#buildFreightFacilityButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff690, stop:0.45 #ffdc32, stop:0.78 #d9a10a, stop:1 #18130a);
    border-color: rgba(255, 246, 210, 210);
}}
QPushButton#buildHallButtonV2:pressed, QPushButton#buildFreightFacilityButton:pressed {{
    background: #be8d05;
    color: #060705;
    border-color: rgba(7, 8, 7, 240);
}}
QPushButton#expandResourceStorageButton[factoryV2StorageCta="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 {Theme.SAFETY_YELLOW}, stop:0.78 #c88f00, stop:1 #111008);
    color: #10120a;
    border: 2px solid rgba(7, 8, 7, 238);
    border-radius: 7px;
    padding: 6px 10px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-weight: 900;
}}
QPushButton#sellResourceButton, QPushButton#devButton, QPushButton#acceptContractButton, QPushButton#deliverContractButton, QPushButton#claimContractButton, QPushButton#resourcesButton, QPushButton#closeDrawerButton, QPushButton#freightFacilityButton, QPushButton#freightCloseDrawerButton, QPushButton#freightRemoveButton, QPushButton#recycleCardButton, QPushButton#craftCardButton, QPushButton#mkUpgradeButton, QPushButton#expandResourceStorageButton, QPushButton#chartBackButton, QPushButton#chartCashBackButton, QPushButton#marketBackButton, QPushButton#productionGuideButton, QPushButton#buyCommonSupplyButton, QPushButton#buyDailySupplyButton, QPushButton#buyDailyFreightSupplyButton, QPushButton#buyDailyMachineSupplyButton, QPushButton#openPackButton, QPushButton#backToPacksButton {{
    background: {Theme.SURFACE_INTERACTIVE};
    color: {Theme.TEXT};
    border: 1px solid rgba(98, 190, 232, 70);
    border-radius: 7px;
    padding: 7px 10px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-weight: 900;
}}
QPushButton#productionGuideButton {{
    border-color: rgba(255, 210, 31, 118);
    border-bottom-color: rgba(8, 8, 7, 210);
}}
QPushButton#sellResourceButton:hover, QPushButton#devButton:hover, QPushButton#acceptContractButton:hover, QPushButton#deliverContractButton:hover, QPushButton#claimContractButton:hover, QPushButton#resourcesButton:hover, QPushButton#closeDrawerButton:hover, QPushButton#freightFacilityButton:hover, QPushButton#freightCloseDrawerButton:hover, QPushButton#freightRemoveButton:hover, QPushButton#recycleCardButton:hover, QPushButton#craftCardButton:hover, QPushButton#mkUpgradeButton:hover, QPushButton#expandResourceStorageButton:hover, QPushButton#chartBackButton:hover, QPushButton#chartCashBackButton:hover, QPushButton#marketBackButton:hover, QPushButton#productionGuideButton:hover, QPushButton#buyCommonSupplyButton:hover, QPushButton#buyDailySupplyButton:hover, QPushButton#buyDailyFreightSupplyButton:hover, QPushButton#buyDailyMachineSupplyButton:hover, QPushButton#openPackButton:hover, QPushButton#backToPacksButton:hover {{
    background: {Theme.SURFACE_HOVER};
    border-color: rgba(98, 190, 232, 130);
}}
QPushButton#productionGuideButton:hover {{
    border-color: rgba(255, 210, 31, 172);
}}
QPushButton#sellResourceButton:pressed, QPushButton#devButton:pressed, QPushButton#acceptContractButton:pressed, QPushButton#deliverContractButton:pressed, QPushButton#claimContractButton:pressed, QPushButton#resourcesButton:pressed, QPushButton#closeDrawerButton:pressed, QPushButton#freightFacilityButton:pressed, QPushButton#freightCloseDrawerButton:pressed, QPushButton#freightRemoveButton:pressed, QPushButton#recycleCardButton:pressed, QPushButton#craftCardButton:pressed, QPushButton#mkUpgradeButton:pressed, QPushButton#expandResourceStorageButton:pressed, QPushButton#chartBackButton:pressed, QPushButton#chartCashBackButton:pressed, QPushButton#marketBackButton:pressed, QPushButton#productionGuideButton:pressed, QPushButton#buyCommonSupplyButton:pressed, QPushButton#buyDailySupplyButton:pressed, QPushButton#buyDailyFreightSupplyButton:pressed, QPushButton#buyDailyMachineSupplyButton:pressed, QPushButton#openPackButton:pressed, QPushButton#backToPacksButton:pressed {{
    background: {Theme.SURFACE_2};
    border-color: rgba(98, 190, 232, 180);
}}
QPushButton#productionGuideButton:pressed {{
    border-color: rgba(255, 210, 31, 206);
}}
QPushButton#freightRemoveButton, QPushButton#recycleCardButton {{
    border-color: rgba(240, 111, 115, 84);
}}
QPushButton#freightRemoveButton[freightCardSecondary="true"] {{
    background: rgba(6, 8, 8, 92);
    border: 1px solid rgba(239, 248, 244, 64);
    border-radius: 4px;
    color: rgba(239, 248, 244, 172);
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 7px;
    font-weight: 800;
    padding: 0 4px;
}}
QPushButton#freightRemoveButton[freightCardSecondary="true"]:hover {{
    background: rgba(30, 36, 35, 148);
    border-color: rgba(239, 248, 244, 104);
    color: {Theme.TEXT};
}}
QPushButton:disabled {{
    background: rgba(255, 255, 255, 4);
    color: {Theme.DIM};
    border-color: rgba(159, 178, 173, 28);
}}
QPushButton#supplySectionButton {{
    background: transparent;
    color: {Theme.MUTED};
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 7px 12px;
    font-size: 11px;
    font-weight: 900;
}}
QPushButton#supplySectionButton[active="true"] {{
    background: rgba(168, 182, 255, 18);
    color: {Theme.TEXT};
    border-color: rgba(168, 182, 255, 92);
}}
QPushButton#supplySectionButton:hover {{
    border-color: rgba(168, 182, 255, 62);
}}
QPushButton#freightFacilityButton[selected="true"] {{
    border-color: {Theme.RESOURCE};
    color: {Theme.TEXT};
}}
QFrame#productionSelectionTile {{
    background: {Theme.PANEL};
    border: 1px solid {Theme.BORDER};
    border-radius: 6px;
}}
QFrame#productionSelectionTile[current="true"] {{
    border-color: {Theme.RESOURCE};
}}
QFrame#factoryCardSelectionTile {{
    background: rgba(21, 29, 33, 214);
    border: 1px solid rgba(110, 128, 122, 112);
    border-radius: 8px;
}}
QFrame#factoryCardSelectionTile:hover, QFrame#factoryCardSelectionTile:focus {{
    background: rgba(26, 36, 40, 230);
    border-color: rgba(150, 176, 168, 166);
}}
QFrame#factoryCardSelectionTile[stageAccent="energy"] {{
    border-left: 3px solid rgba(240, 197, 91, 190);
}}
QFrame#factoryCardSelectionTile[stageAccent="extractor"] {{
    border-left: 3px solid rgba(107, 188, 132, 190);
}}
QFrame#factoryCardSelectionTile[stageAccent="processor"] {{
    border-left: 3px solid rgba(98, 166, 202, 190);
}}
QFrame#factoryCardSelectionTile[stageAccent="fabricator"] {{
    border-left: 3px solid rgba(177, 141, 222, 190);
}}
QFrame#factoryCardSelectionTile[stageAccent="assembler"] {{
    border-left: 3px solid rgba(219, 154, 98, 190);
}}
QLabel#factoryCardSelectionTileName {{
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 0px;
    background: transparent;
}}
QLabel#factoryCardSelectionTileRarity {{
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 800;
    background: transparent;
}}
QFrame#factoryCardSelectionRarityLine {{
    background: rgba(140, 161, 154, 120);
    border: none;
}}
QFrame#factoryCardSelectionRarityLine[rarity="common"] {{
    background: rgba(140, 161, 154, 120);
}}
QFrame#factoryCardSelectionRarityLine[rarity="uncommon"] {{
    background: rgba(107, 188, 132, 150);
}}
QFrame#factoryCardSelectionRarityLine[rarity="rare"] {{
    background: rgba(92, 158, 220, 155);
}}
QFrame#factoryCardSelectionRarityLine[rarity="epic"] {{
    background: rgba(178, 120, 226, 160);
}}
QFrame#factoryCardSelectionRarityLine[rarity="legendary"] {{
    background: rgba(230, 172, 82, 170);
}}
QLabel#factoryCardSelectionTileFunction {{
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
    background: transparent;
}}
QLabel#factoryCardSelectionTileBonus, QLabel#factoryCardSelectionTileCount {{
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
    background: transparent;
}}
QLabel#factoryCardSelectionTileCount {{
    color: {Theme.TEXT};
}}
QLabel#factoryCardSelectionEmpty {{
    color: {Theme.MUTED};
    font-size: 13px;
    font-weight: 800;
    padding: 20px;
    background: transparent;
}}
QLabel#productionTileName {{
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 800;
}}
QLabel#productionTileCategory {{
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 700;
}}
QLabel#productionTileCurrent {{
    color: {Theme.RESOURCE};
    font-size: 10px;
    font-weight: 800;
}}
QProgressBar#freightShipmentProgress {{
    background: rgba(255, 255, 255, 16);
    border: 1px solid rgba(143, 180, 255, 38);
    border-radius: 3px;
    height: 8px;
}}
QProgressBar#freightShipmentProgress::chunk {{
    background: {Theme.RESOURCE};
    border-radius: 2px;
}}
QScrollArea {{
    background: transparent;
}}
"""
