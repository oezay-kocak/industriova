from __future__ import annotations


from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS


class Theme:
    GUIDE_CHASSIS_LIGHT = "#d2d4d5"
    GUIDE_CHASSIS_MID = "#9fa3a6"
    GUIDE_CHASSIS_DARK = "#565c60"
    PRODUCTION_GUIDE_CANVAS = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {GUIDE_CHASSIS_LIGHT}, stop:1 {GUIDE_CHASSIS_MID})"
    GUIDE_HEADER_START = "#252a2e"
    GUIDE_HEADER_MID = "#151a1e"
    GUIDE_HEADER_END = "#20262b"
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
    TEXT_ON_LIGHT_PRIMARY = "#18201d"
    TEXT_ON_LIGHT_SECONDARY = "#33413b"
    TEXT_ON_LIGHT_MUTED = "#5a6861"
    FILTER_INACTIVE_TEXT = TEXT_ON_LIGHT_PRIMARY
    FILTER_ACTIVE_TEXT = TEXT
    GOOD = "#65d88f"
    SAFETY_YELLOW = "#ffd21f"
    HEADER_SUBTITLE_RED = "#9a2f22"
    WARN = "#c83a2b"
    TRAIN = GAME_UI_TOKENS.colors.train
    WARNING_ORANGE = "#df6b2f"
    BAD = "#f06f73"
    ENERGY = SAFETY_YELLOW
    CASH = "#7fed18"
    RESOURCE = "#25b9e8"
    RARE = "#b187ff"
    RARITY_COMMON = TEXT
    RARITY_UNCOMMON = GOOD
    RARITY_RARE = "#5c9edc"
    RARITY_EPIC = "#b278e2"
    RARITY_LEGENDARY = "#e6ac52"
    INDUSTRIAL_FONT = '"Bahnschrift Condensed", "Bahnschrift SemiCondensed", "Agency FB", "Arial Narrow", "Bahnschrift", "Segoe UI"'
    # Scoped concrete/painted-metal materials for secondary workspaces and Packs' outer shell.
    SECONDARY_SHELL_LIGHT = "#e6e4d8"
    SECONDARY_SHELL_MID = "#c7c9be"
    SECONDARY_SHELL_DARK = "#a6ada2"
    SECONDARY_SURFACE = "#b6bcb1"
    SECONDARY_RECESSED = SURFACE_1
    SECONDARY_CARD = SURFACE_3
    SECONDARY_CARD_HOVER = SURFACE_HOVER
    SECONDARY_SHELL_GRADIENT = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {SECONDARY_SHELL_LIGHT}, stop:0.55 {SECONDARY_SHELL_MID}, stop:1 {SECONDARY_SHELL_DARK})"
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
    min-width: 340px;
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
    min-width: 58px;
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
    font-size: 12px;
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
    background: {Theme.SURFACE_0};
    border: 1px solid {Theme.BORDER};
    border-radius: 3px;
}}
QLabel#eventFeedCaption {{ color: {Theme.SAFETY_YELLOW}; font-size: 9px; font-weight: 900; }}
QFrame#eventFeedViewport {{ background: #0d1416; border: 0; }}
QWidget#eventFeedTickerTape {{ background: transparent; border: 0; }}
QLabel#eventFeedTickerEntry {{ background: transparent; color: {Theme.TEXT}; font-size: 10px; font-weight: 700; }}
QPushButton#eventFeedHistoryButton, QPushButton#companyInboxButton {{
    background: #202829; color: {Theme.MUTED}; border: 1px solid {Theme.BORDER};
    border-radius: 2px; padding: 3px 7px; font-size: 9px; font-weight: 900;
}}
QPushButton#companyInboxButton[unread="true"] {{ color: {Theme.SAFETY_YELLOW}; border-color: {Theme.SAFETY_YELLOW}; }}
QFrame#eventFeedHistoryPanel, QFrame#companyInboxPanel {{
    background: transparent;
    border: 0;
}}
QFrame#activityPanelFrame {{
    background: {Theme.SECONDARY_SHELL_GRADIENT};
    border: 2px solid {Theme.GUIDE_CHASSIS_DARK};
    border-radius: 8px;
}}
QFrame#activityPanelHeader {{ background: transparent; border: 0; }}
QLabel#activityPanelTitle {{
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 22px;
    font-weight: 900;
}}
QLabel#activityPanelSubtitle {{ color: {Theme.HEADER_SUBTITLE_RED}; font-size: 9px; font-weight: 900; }}
QPushButton#activityPanelClose {{
    background: {Theme.SURFACE_2}; color: {Theme.TEXT}; border: 1px solid {Theme.BORDER_STRONG};
    border-radius: 2px; padding: 4px 9px; font-size: 9px; font-weight: 900;
}}
QScrollArea#activityPanelScroll, QWidget#activityPanelContent {{ background: {Theme.SURFACE_1}; border: 0; }}
QFrame#activityMessageCard {{
    background: {Theme.SURFACE_2};
    border: 1px solid {Theme.BORDER_STRONG};
    border-left: 3px solid {Theme.SAFETY_YELLOW};
    border-radius: 3px;
}}
QFrame#activityMessageCard[interactive="true"]:hover {{ background: {Theme.SURFACE_INTERACTIVE}; border-color: {Theme.SAFETY_YELLOW}; }}
QWidget#activityMessageIcon {{ background: {Theme.SURFACE_0}; border: 1px solid {Theme.BORDER}; border-radius: 3px; }}
QLabel#activityMessageTitle {{ color: {Theme.TEXT}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 15px; font-weight: 900; }}
QLabel#activityMessageSecondary {{ color: {Theme.MUTED}; font-size: 11px; font-weight: 700; }}
QLabel#activityMessageStatus {{ color: {Theme.SAFETY_YELLOW}; font-size: 9px; font-weight: 900; }}
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
QFrame#eventFeedEntry[eventType="delivery"] {{
    border-color: #456356;
}}
QFrame#eventFeedEntry[eventType="unlock"] {{
    border-color: #6f773a;
}}
QLabel#eventFeedIcon {{
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 900;
    min-width: 20px;
}}
QLabel#eventFeedAmount {{
    color: {Theme.SAFETY_YELLOW};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#eventFeedAmount[eventType="cash"] {{ color: {Theme.CASH}; }}
QLabel#eventFeedAmount[eventType="xp"] {{ color: {Theme.RESOURCE}; }}
QLabel#eventFeedAmount[eventType="pack"], QLabel#eventFeedAmount[eventType="unlock"] {{ color: {Theme.SAFETY_YELLOW}; }}
QLabel#eventFeedAmount[eventType="contract"], QLabel#eventFeedAmount[eventType="delivery"] {{ color: {Theme.GOOD}; }}
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
    font-size: 11px;
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
    font-size: 11px;
    font-weight: 800;
}}
QTabWidget#mainTabs QTabBar::tab, QTabBar#mainNavigationTabs::tab {{
    padding: 8px 7px;
    margin-right: 2px;
    font-size: 9px;
}}
QTabBar#mainNavigationTabs {{
    font-family: "Bahnschrift";
    font-size: 12px;
    font-weight: 900;
}}
QTabBar#mainNavigationTabs::tab {{
    padding: 8px 3px;
    font-size: 12px;
    font-weight: 900;
}}
QLabel#factoryV2OperationsActivity {{
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 15px;
    font-weight: 900;
}}
QProgressBar#factoryV2OperationsProgress {{
    background: rgba(4, 9, 10, 190);
    border: 1px solid rgba(98, 166, 202, 90);
    border-radius: 3px;
}}
QProgressBar#factoryV2OperationsProgress::chunk {{
    background: #62a6ca;
    border-radius: 2px;
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
    max-height: 16777215px;
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
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 #ffd21f, stop:1 #f5a623);
    border: 1px solid #17191b;
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
QFrame#factoryCardSelectionView, QFrame#productionSelectionView, QFrame#productionSelectionDrawer, QFrame#productionGuideView, QFrame#freightCardSelectionView, QFrame#freightAssignmentSelectionView {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d3d2c8, stop:0.42 #9fa49b, stop:1 #565d59);
    border: 2px solid rgba(54, 58, 54, 184);
    border-radius: 16px;
}}
QFrame#productionGuideView {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Theme.GUIDE_CHASSIS_LIGHT}, stop:0.42 {Theme.GUIDE_CHASSIS_MID}, stop:1 {Theme.GUIDE_CHASSIS_DARK});
}}
QWidget#factoryCardSelectionGridHost, QWidget#productionSelectionGridHost, QWidget#productionGuideGridHost, QWidget#freightSelectionGridHost, QWidget#freightAssignmentResourceGridHost {{
    background: transparent;
    border: 0;
}}
QLabel#factoryCardSelectionResultCount {{
    background: rgba(22, 29, 29, 226);
    color: {Theme.TEXT};
    border: 1px solid rgba(112, 126, 121, 100);
    border-left: 3px solid {Theme.SAFETY_YELLOW};
    border-radius: 4px;
    padding: 7px 10px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 11px;
    font-weight: 900;
}}
QWidget#productionSelectionGridHost, QWidget#freightAssignmentResourceGridHost {{
    background: rgba(255, 255, 255, 7);
    border: 0;
}}
QScrollArea#factoryCardSelectionScroll, QScrollArea#productionSelectionScroll, QScrollArea#productionGuideScroll, QScrollArea#freightCardSelectionScroll, QScrollArea#freightAssignmentResourceScroll {{
    background: rgba(8, 12, 12, 116);
    border: 1px solid rgba(54, 58, 54, 116);
    border-radius: 10px;
}}
QFrame#productionGuideHeader, QFrame#chainInspectorHeader, QFrame#usedInDetailHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Theme.GUIDE_HEADER_START}, stop:0.58 {Theme.GUIDE_HEADER_MID}, stop:1 {Theme.GUIDE_HEADER_END});
    border: 1px solid rgba(255, 210, 31, 96);
    border-radius: 10px;
}}
QScrollArea#productionSelectionScroll, QScrollArea#freightAssignmentResourceScroll {{
    background: rgba(255, 255, 255, 7);
    border: 1px solid rgba(54, 58, 54, 92);
    border-radius: 10px;
}}
QWidget#resourceSelectionViewport {{
    background: rgba(255, 255, 255, 7);
    border: 0;
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
QFrame#freightSelectionFilters, QFrame#productionGuideFilters {{
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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e8e7dc, stop:0.60 #b5bbb2, stop:1 #737d76);
    border: 1px solid rgba(55, 62, 58, 150);
    border-radius: 10px;
}}
QFrame#marketEventPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #eeece1, stop:0.62 #bbbfb6, stop:1 #828b84);
    border: 1px solid rgba(55, 62, 58, 152);
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
QLineEdit#cardSearchInput, QLineEdit#productionSearchInput, QLineEdit#productionGuideSearchInput, QLineEdit#freightCardSearch, QLineEdit#freightAssignmentSearch, QLineEdit#supplySearch, QLineEdit#chartResourceSearch, QLineEdit#marketSearch, QLineEdit#leaderboardSearch {{
    background: rgba(6, 9, 9, 178);
    border: 1px solid rgba(158, 176, 180, 96);
    border-radius: 6px;
    color: {Theme.TEXT};
    padding: 7px 10px;
    min-width: 190px;
    selection-background-color: rgba(255, 210, 31, 70);
}}
QLineEdit#cardSearchInput:focus, QLineEdit#productionSearchInput:focus, QLineEdit#productionGuideSearchInput:focus, QLineEdit#freightCardSearch:focus, QLineEdit#freightAssignmentSearch:focus, QLineEdit#supplySearch:focus, QLineEdit#chartResourceSearch:focus, QLineEdit#marketSearch:focus, QLineEdit#leaderboardSearch:focus {{
    border-color: rgba(255, 210, 31, 150);
    background: rgba(10, 13, 13, 220);
}}
QFrame#resourceSelectorFilterPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e8e7dc, stop:0.60 #b5bbb2, stop:1 #737d76);
    border: 1px solid rgba(55, 62, 58, 150);
    border-radius: 10px;
}}
QFrame#resourceSelectorFilterPanel QLineEdit {{
    background-color: #e7e9e2;
    background: #e7e9e2;
    border: 1px solid rgba(45, 54, 50, 132);
    border-radius: 6px;
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    padding: 7px 10px;
    min-width: 190px;
    selection-background-color: rgba(37, 185, 232, 72);
}}
QFrame#resourceSelectorFilterPanel QLineEdit:focus {{
    background-color: #f2f3ee;
    background: #f2f3ee;
    border-color: rgba(37, 185, 232, 168);
}}
QFrame#resourceSelectorFilterPanel QComboBox {{
    background-color: #d6dbd3;
    background: #d6dbd3;
    border: 1px solid rgba(45, 54, 50, 132);
    border-radius: 6px;
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    padding: 7px 10px;
    min-width: 150px;
}}
QFrame#resourceSelectorFilterPanel QComboBox:hover {{
    background: #e3e6de;
    border-color: rgba(37, 80, 92, 156);
}}
QFrame#resourceSelectorFilterPanel QComboBox:focus {{
    border-color: rgba(37, 185, 232, 168);
}}
QLineEdit#marketSearch {{
    background-color: #e7e9e2;
    background: #e7e9e2;
    border: 1px solid rgba(45, 54, 50, 132);
    border-radius: 6px;
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    padding: 7px 10px;
    min-width: 190px;
    selection-background-color: rgba(255, 210, 31, 84);
}}
QLineEdit#marketSearch:focus {{
    background-color: #f2f3ee;
    background: #f2f3ee;
    border-color: rgba(255, 210, 31, 164);
}}
QWidget#marketFilterDeck QLineEdit#marketSearch {{
    background-color: #e7e9e2;
    background: #e7e9e2;
    border: 1px solid rgba(45, 54, 50, 132);
    border-radius: 6px;
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    padding: 6px 8px;
    min-width: 140px;
    font-size: 13px;
    selection-background-color: rgba(255, 210, 31, 84);
}}
QWidget#marketFilterDeck QLineEdit#marketSearch:focus {{
    background-color: #f2f3ee;
    background: #f2f3ee;
    border-color: rgba(255, 210, 31, 164);
}}
QWidget#marketFilterDeck QLabel#sectionLabel {{
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    font-family: "Segoe UI";
    font-size: 11px;
    font-weight: 800;
}}
QWidget#marketControlGroup {{
    background: transparent;
    border: 0;
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
    background: rgba(28, 34, 32, 32);
    border: 1px solid rgba(45, 54, 50, 132);
    border-radius: 5px;
    color: {Theme.FILTER_INACTIVE_TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 9px;
}}
QPushButton#chartFilterChip:hover {{
    background: rgba(20, 27, 27, 72);
    border-color: rgba(37, 80, 92, 160);
    color: #111715;
}}
QPushButton#chartFilterChip[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #354246, stop:1 #121a1c);
    border-color: rgba(37, 185, 232, 190);
    color: {Theme.FILTER_ACTIVE_TEXT};
}}
QPushButton#marketFilterChip {{
    background: rgba(255, 255, 255, 18);
    border: 1px solid rgba(45, 54, 50, 132);
    border-radius: 5px;
    color: {Theme.FILTER_INACTIVE_TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 9px;
}}
QPushButton#marketFilterChip:hover {{
    background: rgba(20, 27, 27, 54);
    border-color: rgba(37, 80, 92, 148);
    color: #111715;
}}
QPushButton#marketFilterChip[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 #ffd21f, stop:1 #f5a623);
    border-color: #292b2d;
    color: #17191b;
}}
QPushButton#supplyFilterChip {{
    background: rgba(255, 255, 255, 18);
    border: 1px solid rgba(45, 54, 50, 132);
    border-radius: 5px;
    color: {Theme.FILTER_INACTIVE_TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 9px;
}}
QPushButton#supplyFilterChip:hover {{
    background: rgba(20, 27, 27, 54);
    border-color: rgba(37, 80, 92, 148);
    color: #111715;
}}
QPushButton#supplyFilterChip[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #354246, stop:1 #121a1c);
    border-color: rgba(37, 185, 232, 180);
    color: {Theme.FILTER_ACTIVE_TEXT};
}}
QPushButton#marketCategorySelectorButton, QPushButton#marketEventSelectorButton, QPushButton#marketTrendSelectorButton, QPushButton#marketSortSelectorButton {{
    background: rgba(8, 12, 13, 210);
    border: 1px solid rgba(37, 80, 92, 132);
    border-radius: 5px;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 10px;
    text-align: left;
}}
QPushButton#marketCategorySelectorButton:hover, QPushButton#marketEventSelectorButton:hover, QPushButton#marketTrendSelectorButton:hover, QPushButton#marketSortSelectorButton:hover {{
    background: rgba(18, 27, 29, 232);
    border-color: rgba(37, 185, 232, 154);
    color: #f5fbff;
}}
QPushButton#marketCategorySelectorButton:pressed, QPushButton#marketEventSelectorButton:pressed, QPushButton#marketTrendSelectorButton:pressed, QPushButton#marketSortSelectorButton:pressed {{
    background: rgba(5, 8, 9, 238);
    border-color: rgba(255, 210, 31, 138);
}}
QPushButton#supplyMachineSelector, QPushButton#supplySortSelector {{
    background: rgba(8, 12, 13, 212);
    border: 1px solid rgba(142, 132, 98, 104);
    border-radius: 5px;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 10px;
    text-align: left;
}}
QPushButton#supplyMachineSelector:hover, QPushButton#supplySortSelector:hover {{
    background: rgba(19, 23, 20, 236);
    border-color: rgba(255, 210, 31, 150);
}}
QPushButton#supplyMachineSelector:pressed, QPushButton#supplySortSelector:pressed {{
    background: rgba(5, 8, 8, 242);
    border-color: rgba(255, 238, 128, 164);
}}
QFrame#marketSelectorFlyout, QFrame#supplySelectorFlyout {{
    background: rgba(7, 10, 10, 248);
    border: 1px solid rgba(159, 178, 173, 124);
    border-radius: 8px;
}}
QPushButton#marketSelectorOption, QPushButton#supplySelectorOption {{
    background: rgba(16, 22, 22, 232);
    border: 1px solid rgba(159, 178, 173, 58);
    border-radius: 5px;
    color: #c9d8d3;
    font-size: 10px;
    font-weight: 900;
    padding: 6px 10px;
    text-align: left;
    min-width: 150px;
}}
QPushButton#marketSelectorOption:hover, QPushButton#supplySelectorOption:hover {{
    background: rgba(25, 36, 38, 244);
    color: {Theme.TEXT};
    border-color: rgba(37, 185, 232, 132);
}}
QPushButton#marketSelectorOption[active="true"], QPushButton#supplySelectorOption[active="true"] {{
    background: rgba(255, 210, 31, 212);
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
QWidget#inventorySearchGroup {{
    background: transparent;
    border: 0;
}}
QFrame#inventoryCard {{
    background: transparent;
    border: 0;
}}
QFrame#packOpenedCardTile {{
    background: transparent;
    border: 0;
}}
QFrame#craftTargetCard, QFrame#craftMaterialCard {{
    background: transparent;
    border: 0;
}}
QFrame#craftResultCard {{
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
    background: transparent;
    border: 0;
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
    background: transparent;
    border: 0;
}}
QFrame#freightSelectionCard:hover, QFrame#freightSelectionCard:focus {{
    background: transparent;
    border: 0;
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
QFrame#cardHoverInfo, QFrame#supplyCardHoverInfo, QFrame#researchHoverInfo {{
    background: rgba(23, 33, 40, 238);
    border: 1px solid #3d5361;
    border-radius: 8px;
}}
QLabel#cardHoverIcon {{
    background: rgba(8, 13, 17, 150);
    border: 1px solid {Theme.BORDER};
    border-radius: 4px;
    padding: 2px;
}}
QLabel#cardHoverValue[field="bonus"] {{ color: {Theme.GOOD}; font-weight: 900; }}
QLabel#cardHoverValue[field="rarity"][rarity="common"] {{ color: {Theme.RARITY_COMMON}; }}
QLabel#cardHoverValue[field="rarity"][rarity="uncommon"] {{ color: {Theme.RARITY_UNCOMMON}; font-weight: 900; }}
QLabel#cardHoverValue[field="rarity"][rarity="rare"] {{ color: {Theme.RARITY_RARE}; font-weight: 900; }}
QLabel#cardHoverValue[field="rarity"][rarity="epic"] {{ color: {Theme.RARITY_EPIC}; font-weight: 900; }}
QLabel#cardHoverValue[field="rarity"][rarity="legendary"] {{ color: {Theme.RARITY_LEGENDARY}; font-weight: 900; }}
QFrame#inventoryActionPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(34, 40, 40, 252), stop:0.5 rgba(16, 21, 21, 254), stop:1 rgba(7, 10, 10, 255));
    border: 1px solid rgba(142, 154, 150, 82);
    border-radius: 10px;
}}
QFrame#inventoryScrapCardSummary {{
    background: rgba(255, 255, 255, 5);
    border: 1px solid rgba(142, 154, 150, 48);
    border-radius: 7px;
}}
QFrame#inventoryScrapRewardBlock {{
    background: rgba(255, 255, 255, 5);
    border: 1px solid rgba(142, 154, 150, 48);
    border-radius: 7px;
}}
QLabel#inventoryScrapAvailability, QLabel#inventoryScrapUnavailable {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 800;
}}
QLabel#inventoryScrapRewardLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#inventoryScrapReward {{
    background: transparent;
    color: {Theme.SAFETY_YELLOW};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 13px;
    font-weight: 900;
}}
QSpinBox#scrapQuantity {{
    background: rgba(255, 255, 255, 8);
    color: {Theme.TEXT};
    border: 1px solid rgba(142, 154, 150, 78);
    border-radius: 7px;
    padding: 4px 18px 4px 6px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 14px;
    font-weight: 900;
}}
QLabel#scrapConfirmationCard, QLabel#scrapConfirmationQuantity {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QPushButton#scrapCardButton, QPushButton#cancelScrapButton, QPushButton#confirmScrapButton {{
    background: {Theme.SURFACE_INTERACTIVE};
    color: {Theme.TEXT};
    border: 1px solid rgba(98, 190, 232, 70);
    border-radius: 7px;
    padding: 7px 12px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-weight: 900;
}}
QPushButton#cancelScrapButton:hover {{
    background: {Theme.SURFACE_HOVER};
}}
QPushButton#scrapCardButton, QPushButton#confirmScrapButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe65b, stop:0.55 {Theme.SAFETY_YELLOW}, stop:1 #d9a900);
    color: #11130b;
    border: 1px solid #fff097;
    min-width: 92px;
}}
QPushButton#scrapCardButton:hover, QPushButton#confirmScrapButton:hover {{
    background: #ffe86a;
}}
QPushButton#scrapCardButton:pressed, QPushButton#confirmScrapButton:pressed {{
    background: #c7960d;
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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f0eee3, stop:0.46 #e2e2d7, stop:1 #c5c9bf);
    border: 2px solid rgba(54, 58, 54, 184);
    border-radius: 14px;
}}
QFrame#mkUpgradeResultPanel, QFrame#mkUpgradeComparePanel, QFrame#mkUpgradeCostPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(52, 57, 55, 248), stop:0.46 rgba(20, 25, 25, 252), stop:1 rgba(6, 8, 8, 255));
    border: 2px solid rgba(142, 154, 150, 82);
    border-radius: 14px;
}}
QFrame#mkUpgradeResultPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f0eee3, stop:0.46 #e2e2d7, stop:1 #c5c9bf);
    border: 2px solid rgba(54, 58, 54, 184);
}}
QFrame#mkUpgradeComparePanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f7f5e9, stop:0.5 #dfdfd2, stop:1 #bdc3b6);
    border: 2px solid #687366;
}}
QFrame#craftActionPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f7f5e9, stop:0.5 #dfdfd2, stop:1 #bdc3b6);
    border: 1px solid #687366;
    border-radius: 10px;
}}
QFrame#mkUpgradeCurrentCard, QFrame#mkUpgradeTargetCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #faf6e9, stop:0.5 #d6d9cd, stop:1 #a5afa0);
    border: 1px solid #737d70;
    border-radius: 10px;
}}
QFrame#mkUpgradeCompareRow {{
    background: rgba(255, 255, 244, 126);
    border: 1px solid rgba(54, 65, 53, 90);
    border-radius: 6px;
    min-height: 22px;
}}
QFrame#mkUpgradeConnector {{
    background: transparent;
    border: 0;
}}
QFrame#craftConversionSign {{
    background: transparent;
    border: 0;
}}
QFrame#mkUpgradeConfirmZone {{
    background: transparent;
    border: 0;
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
    color: {Theme.TEXT_ON_LIGHT_SECONDARY};
    font-size: 10px;
    font-weight: 900;
}}
QLabel#mkUpgradeCompareValue {{
    background: transparent;
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    font-size: 11px;
    font-weight: 800;
}}
QLabel#mkUpgradeCompareArrow {{
    background: transparent;
    color: #a44d05;
    font-size: 12px;
    font-weight: 900;
}}
QLabel#mkUpgradePlaceholder {{
    background: transparent;
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    font-size: 12px;
    font-weight: 800;
}}
QFrame#craftTargetPreview, QFrame#craftMaterialSlots {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #faf6e9, stop:0.5 #d6d9cd, stop:1 #a5afa0);
    border: 1px solid #737d70;
    border-radius: 10px;
}}
QFrame#craftMaterialSlot {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe188, stop:0.15 #ffc344, stop:0.75 #f29b16, stop:1 #b65b0c);
    border: 1px solid #864710;
    border-radius: 7px;
    min-width: 58px;
    min-height: 106px;
}}
QFrame#craftMaterialSlot[filled="true"] {{
    border-style: solid;
    border-color: #873b09;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffd563, stop:0.22 #ffae18, stop:0.78 #f07d09, stop:1 #b44308);
}}
QFrame#craftMaterialSlot:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff0a1, stop:0.4 #ffd23b, stop:1 #f39a17);
    border-color: #fff8d0;
}}
QLabel#craftSectionTitle {{
    background: transparent;
    color: #171c1b;
    font-size: 18px;
    font-weight: 900;
}}
QFrame#craftPreviewPanel QLabel#craftSectionTitle, QFrame#mkUpgradeResultPanel QLabel#craftSectionTitle {{
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
}}
QFrame#mkUpgradeResultPanel QLabel#mkUpgradeCompareLabel, QFrame#mkUpgradeResultPanel QLabel#mkUpgradeCompareValue, QFrame#mkUpgradeResultPanel QLabel#mkUpgradePreview {{
    font-size: 14px;
}}
QCheckBox#craftConfirm, QCheckBox#mkUpgradeConfirm {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d7462d, stop:0.5 #ad241c, stop:1 #691811);
    border: 1px solid #5d1b12;
    border-radius: 5px;
    color: #fff0d6;
    font-size: 12px;
    padding: 6px;
}}
QCheckBox#craftConfirm::indicator, QCheckBox#mkUpgradeConfirm::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #9fb2ad;
    border-radius: 3px;
    background: #171c1b;
}}
QCheckBox#craftConfirm::indicator:checked, QCheckBox#mkUpgradeConfirm::indicator:checked {{
    background: #ffd21f;
    border-color: #ffd21f;
}}
QPushButton#craftCardButton, QPushButton#mkUpgradeButton {{
    font-size: 16px;
}}
QFrame#craftPreviewPanel QPushButton#craftCardButton, QFrame#mkUpgradeResultPanel QPushButton#mkUpgradeButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 {Theme.SAFETY_YELLOW}, stop:0.78 #c88f00, stop:1 #111008);
    color: #10120a;
    border: 2px solid rgba(7, 8, 7, 238);
    border-radius: 7px;
    font-weight: 900;
    padding: 10px 12px;
}}
QFrame#craftPreviewPanel QPushButton#craftCardButton:hover, QFrame#mkUpgradeResultPanel QPushButton#mkUpgradeButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff690, stop:0.45 #ffdc32, stop:0.78 #d9a10a, stop:1 #18130a);
    border-color: rgba(255, 246, 210, 210);
}}
QFrame#craftPreviewPanel QPushButton#craftCardButton:pressed, QFrame#mkUpgradeResultPanel QPushButton#mkUpgradeButton:pressed {{
    background: #be8d05;
}}
QFrame#craftPreviewPanel QPushButton#craftCardButton:disabled, QFrame#mkUpgradeResultPanel QPushButton#mkUpgradeButton:disabled {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e2d6a0, stop:1 #a79968);
    color: #665b3d;
    border-color: #807657;
}}
QPushButton#inventoryWorkspaceBack {{
    background: #242c2a;
    color: #f3f6ed;
    border: 1px solid #74817a;
    border-radius: 5px;
    padding: 8px 18px;
    font-weight: 900;
}}
QPushButton#inventoryWorkspaceBack:hover {{
    border-color: #ffd21f;
}}
QLineEdit#mkUpgradeSearch {{
    min-height: 30px;
    min-width: 230px;
    background: rgba(6, 9, 9, 178);
    font-size: 14px;
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
QLabel#craftOutputPreview, QLabel#craftMaterialSlotLabel {{
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    font-size: 13px;
}}
QFrame#freightSelectionCard[freightFamily="truck"] {{
    border-left: 3px solid rgba(107, 188, 132, 180);
}}
QFrame#freightSelectionCard[freightFamily="train"] {{
    border-left: 3px solid {Theme.TRAIN};
}}
QFrame#freightSelectionCard[freightFamily="ship"] {{
    border-left: 3px solid rgba(106, 165, 200, 180);
}}
QFrame#freightSelectionCard[freightFamily="aircraft"] {{
    border-left: 3px solid rgba(155, 184, 239, 180);
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
QLabel#freightSelectionEmpty {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 12px;
    font-weight: 800;
}}
QLabel#freightSelectionTarget {{
    background: transparent;
    color: {Theme.TEXT_ON_LIGHT_SECONDARY};
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
QFrame#factoryCardSelectionView QLabel#sectionLabel,
QFrame#productionSelectionView QLabel#sectionLabel,
QFrame#productionGuideView QLabel#sectionLabel,
QFrame#freightCardSelectionView QLabel#sectionLabel,
QFrame#freightAssignmentSelectionView QLabel#sectionLabel,
QWidget#supplyCommonPage QLabel#sectionLabel,
QWidget#supplyDailyPage QLabel#sectionLabel {{
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
}}
QLabel#productionCurrentLabel, QLabel#cardSelectionTargetLabel, QLabel#freightSelectionTarget {{
    background: transparent;
    color: {Theme.TEXT_ON_LIGHT_SECONDARY};
    font-size: 12px;
    font-weight: 800;
}}

QWidget#chartFilterDeck QLabel#sectionLabel, QFrame#chartDetailHeader QLabel#sectionLabel {{
    color: #222a26;
    font-family: "Segoe UI";
    font-size: 11px;
    font-weight: 800;
}}
QWidget#chartControlGroup {{
    background: transparent;
    border: 0;
}}
QWidget#chartFilterDeck QComboBox {{
    background: #202a27;
    color: #edf6f2;
    border: 1px solid #64736a;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
}}
QWidget#chartFilterDeck QLineEdit#chartResourceSearch {{
    min-width: 140px;
    padding: 6px 9px;
    font-size: 13px;
}}
QFrame#productionGuideView QLabel#sectionLabel,
QFrame#chainInspectorView QLabel#sectionLabel,
QFrame#usedInDetailView QLabel#sectionLabel {{
    background: transparent;
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 28px;
    font-weight: 900;
}}
QFrame#chainInspectorView {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Theme.GUIDE_CHASSIS_LIGHT}, stop:0.42 {Theme.GUIDE_CHASSIS_MID}, stop:1 {Theme.GUIDE_CHASSIS_DARK});
    border: 2px solid rgba(54, 58, 54, 184);
    border-radius: 16px;
}}
QFrame#usedInDetailView {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Theme.GUIDE_CHASSIS_LIGHT}, stop:0.42 {Theme.GUIDE_CHASSIS_MID}, stop:1 {Theme.GUIDE_CHASSIS_DARK});
    border: 2px solid rgba(54, 58, 54, 184);
    border-radius: 16px;
}}
QGraphicsView#chainInspectorCanvas {{
    background: rgba(5, 8, 8, 205);
    border: 1px solid rgba(255, 210, 31, 58);
    border-radius: 10px;
}}
QFrame#chainInspectorFlowShell {{
    background: rgba(5, 8, 8, 178);
    border: 1px solid rgba(255, 210, 31, 58);
    border-radius: 10px;
}}
QWidget#chainInspectorStageHost {{
    background: transparent;
    border: 0;
}}
QFrame#productionGuideTile {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(32, 42, 44, 230), stop:1 rgba(12, 18, 19, 236));
    border: 1px solid rgba(142, 158, 151, 132);
    border-radius: 8px;
}}
QFrame#productionGuideTile:hover, QFrame#productionGuideTile:focus {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(42, 52, 52, 242), stop:1 rgba(18, 25, 25, 246));
    border-color: rgba(255, 210, 31, 180);
}}
QFrame#productionGuideTile[progressionState="next"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(91, 53, 22, 238), stop:0.62 rgba(38, 28, 18, 240), stop:1 rgba(14, 18, 18, 238));
    border-color: rgba(223, 107, 47, 210);
}}
QFrame#productionGuideTile[progressionState="later"] {{
    background: rgba(13, 18, 20, 154);
    border-color: rgba(84, 94, 91, 68);
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
    font-size: 14px;
    font-weight: 900;
}}
QLabel#productionGuideTileStage {{
    background: transparent;
    color: {Theme.SAFETY_YELLOW};
    font-size: 12px;
    font-weight: 900;
}}
QLabel#productionGuideTileCategory {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 850;
}}
QLabel#productionGuideUnlock {{
    background: rgba(0, 0, 0, 76);
    color: {Theme.TEXT};
    border: 1px solid rgba(166, 181, 170, 78);
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 12px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-weight: 900;
}}
QLabel#productionGuideUnlock[progressionState="unlocked"] {{
    background: rgba(29, 50, 39, 118);
    color: #dff5e6;
    border-color: rgba(101, 216, 143, 112);
}}
QLabel#productionGuideUnlock[progressionState="next"] {{
    background: rgba(223, 107, 47, 126);
    color: #fff3ce;
    border-color: rgba(255, 210, 31, 172);
}}
QLabel#productionGuideUnlock[progressionState="later"] {{
    background: rgba(0, 0, 0, 42);
    color: rgba(178, 188, 181, 156);
    border-color: rgba(118, 132, 126, 46);
}}
QLabel#productionGuideEmpty, QLabel#chainInspectorEmpty {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 13px;
    font-weight: 800;
    padding: 20px;
}}
QLabel#chainStageTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 16px;
    font-weight: 900;
}}
QFrame#chainResourceBox {{
    background: rgba(22, 31, 32, 224);
    border: 1px solid rgba(126, 146, 140, 116);
    border-radius: 8px;
}}
QFrame#chainResourceBox[target="true"] {{
    background: rgba(48, 37, 18, 228);
    border-color: rgba(255, 210, 31, 170);
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
    font-size: 13px;
    font-weight: 900;
}}
QLabel#chainMachineFamily {{
    background: transparent;
    color: {Theme.SAFETY_YELLOW};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#chainResourceAmount {{
    background: transparent;
    color: #f4d06a;
    font-size: 12px;
    font-weight: 900;
}}
QFrame#guideRecipeDetails {{
    background: transparent;
    border: 0;
}}
QFrame#guideRecipeSection {{
    background: rgba(8, 12, 12, 202);
    border: 1px solid rgba(255, 210, 31, 58);
    border-radius: 8px;
}}
QFrame#guideUsedInSummary, QFrame#usedInIdentity {{
    background: rgba(8, 12, 12, 210);
    border: 1px solid rgba(223, 107, 47, 112);
    border-radius: 8px;
}}
QLabel#guideUsedInSummaryTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 15px;
    font-weight: 900;
}}
QLabel#guideUsedInSummaryCount, QLabel#usedInDetailCount {{
    background: transparent;
    color: {Theme.WARNING_ORANGE};
    font-size: 14px;
    font-weight: 900;
}}
QLabel#guideUsedInSummaryProduct, QLabel#usedInIdentityFlow {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 900;
}}
QLabel#usedInIdentityName {{
    background: transparent;
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 24px;
    font-weight: 900;
}}
QPushButton#guideUsedInOpenButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe764, stop:0.48 {Theme.SAFETY_YELLOW}, stop:1 #a97200);
    border: 1px solid rgba(12, 14, 10, 230);
    border-radius: 7px;
    color: #11130b;
    font-size: 11px;
    font-weight: 900;
    padding: 7px 12px;
}}
QPushButton#guideUsedInOpenButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff097, stop:0.48 #ffdf38, stop:1 #bd8408);
    border-color: rgba(255, 246, 184, 210);
    color: #050706;
}}
QPushButton#guideUsedInOpenButton:pressed {{
    background: #c7960d;
    border-color: rgba(7, 8, 7, 230);
    color: #11130b;
}}
QPushButton#guideUsedInOpenButton:focus {{
    border: 2px solid rgba(255, 246, 184, 225);
}}
QPushButton#guideUsedInOpenButton:disabled {{
    background: rgba(16, 20, 20, 112);
    border-color: rgba(110, 128, 122, 48);
    color: {Theme.MUTED};
}}
QPushButton#usedInBackButton {{
    background: rgba(8, 12, 12, 168);
    border: 1px solid rgba(110, 128, 122, 96);
    border-radius: 7px;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
    padding: 8px 14px;
}}
QPushButton#usedInBackButton:hover {{
    border-color: rgba(255, 210, 31, 135);
    color: {Theme.CASH};
}}
QPushButton#productionGuideBackButton, QPushButton#chainInspectorBackButton {{
    font-size: 13px;
    padding: 8px 14px;
    border-color: rgba(255, 210, 31, 96);
}}
QScrollArea#usedInDetailScroll {{
    background: rgba(5, 8, 8, 205);
    border: 1px solid rgba(255, 210, 31, 58);
    border-radius: 8px;
}}
QWidget#usedInDetailGridHost {{
    background: transparent;
    border: 0;
}}
QScrollArea#guideRecipeSectionScroll {{
    background: rgba(4, 7, 7, 186);
    border: 1px solid rgba(44, 54, 52, 172);
    border-radius: 7px;
}}
QWidget#guideRecipeSectionContent {{
    background: transparent;
    border: 0;
}}
QLabel#guideRecipeSectionTitle {{
    background: transparent;
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 15px;
    font-weight: 900;
}}
QFrame#guideRecipeRow {{
    background: rgba(16, 24, 25, 226);
    border: 1px solid rgba(126, 146, 140, 114);
    border-radius: 5px;
}}
QFrame#guideRecipeRow[progressionState="next"] {{
    background: rgba(47, 34, 19, 228);
    border-color: rgba(223, 107, 47, 172);
}}
QFrame#guideRecipeRow[progressionState="later"] {{
    background: rgba(12, 17, 18, 158);
    border-color: rgba(100, 112, 108, 60);
}}
QLabel#guideRecipeName {{
    background: transparent;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#guideRecipeMeta, QLabel#guideRecipeInputLabel {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 850;
}}
QLabel#guideRecipeMeta[progressionState="later"] {{
    color: rgba(177, 188, 181, 166);
}}
QLabel#guideRecipeDetail {{
    background: transparent;
    color: #f4d06a;
    font-size: 12px;
    font-weight: 900;
}}
QLabel#guideRecipeEmpty, QLabel#guideRecipeInputEmpty {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QPushButton#guideRecipeLink, QPushButton#guideRecipeInputLink {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
    padding: 0;
    text-align: left;
}}
QPushButton#guideRecipeInputLink {{
    color: #f4d06a;
    font-size: 11px;
    font-weight: 900;
}}
QPushButton#guideRecipeLink[progressionState="later"] {{
    color: rgba(219, 224, 214, 184);
}}
QPushButton#guideRecipeLink:hover, QPushButton#guideRecipeInputLink:hover {{
    color: {Theme.CASH};
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
    font-size: 10px;
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
    max-height: 16777215px;
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
    font-size: 9px;
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
    font-size: 9px;
    font-weight: 900;
}}
QLabel#hallResourceNet[netState="negative"] {{
    background: transparent;
    color: {Theme.BAD};
    font-size: 9px;
    font-weight: 900;
}}
QLabel#hallResourceNet[netState="neutral"] {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 9px;
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
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(38, 44, 42, 226), stop:0.54 rgba(13, 18, 18, 242), stop:1 rgba(5, 8, 8, 250));
    border: 1px solid rgba(93, 183, 220, 116);
    border-left: 3px solid rgba(255, 210, 31, 150);
    border-radius: 8px;
}}
QScrollArea#contractsBoardScroll {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d9ddd4, stop:0.55 #a9b0aa, stop:1 #777f79);
    border: 1px solid rgba(43, 49, 47, 150);
    border-radius: 12px;
}}
QWidget#contractsBoard {{
    background: transparent;
}}
QFrame#contractPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ece8da, stop:0.28 #b9b9ad, stop:1 #737c75);
    border: 1px solid rgba(47, 53, 50, 165);
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
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 35, 34, 238), stop:0.56 rgba(11, 17, 17, 248), stop:1 rgba(5, 8, 8, 255));
    border: 1px solid rgba(57, 62, 58, 190);
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
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e1e4dc, stop:0.22 #b5bdb6, stop:0.23 rgba(28, 35, 35, 244), stop:1 rgba(7, 11, 11, 255));
    border: 1px solid rgba(52, 59, 56, 170);
    border-radius: 8px;
}}
QFrame#chartResourceCard:hover, QFrame#chartResourceCard:focus {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0efe3, stop:0.22 #c4c9bf, stop:0.23 rgba(35, 45, 45, 250), stop:1 rgba(9, 15, 16, 255));
    border-color: rgba(255, 210, 31, 156);
}}
QFrame#chartResourceIconHost, QFrame#chartDetailIconHost {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #edf0e8, stop:1 #8d9993);
    border: 1px solid rgba(55, 65, 61, 150);
    border-radius: 7px;
}}
QWidget#chartsOverviewPage, QWidget#chartsDetailPage {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d9ddd5, stop:0.55 #aab2ab, stop:1 #768079);
    border: 1px solid rgba(47, 54, 51, 145);
    border-radius: 12px;
}}
QWidget#chartFilterDeck, QFrame#chartDetailHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ece9dc, stop:0.60 #b9beb5, stop:1 #757f78);
    border: 1px solid rgba(55, 62, 58, 150);
    border-radius: 10px;
}}
QScrollArea#chartFilterScroll {{
    background: transparent;
    border: 0;
}}
QScrollArea#chartResourceScroll {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(26, 31, 31, 226), stop:1 rgba(6, 9, 9, 246));
    border: 1px solid rgba(54, 62, 58, 170);
    border-radius: 10px;
}}
QWidget#chartResourceGrid {{
    background: transparent;
}}
QWidget#chartDetailGrid {{
    background: transparent;
}}
QFrame#marketCard, QFrame#marketEventCard, QFrame#marketDetailSummary, QFrame#marketChartPanel {{
    background: {Theme.PANEL_ALT};
    border: 1px solid {Theme.BORDER};
    border-radius: 7px;
}}
QWidget#marketOverviewPage, QWidget#marketDetailPage {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #edeae2, stop:0.55 #d5d2ca, stop:1 #b5b2ac);
    border: 1px solid rgba(47, 54, 51, 145);
    border-radius: 12px;
}}
QFrame#marketEventPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #eeece1, stop:0.62 #bbbfb6, stop:1 #828b84);
    border: 1px solid rgba(55, 62, 58, 152);
    border-radius: 10px;
}}
QWidget#marketFilterDeck, QFrame#marketDetailHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0ede5, stop:0.60 #dbd8d0, stop:1 #b4b2ad);
    border: 1px solid rgba(55, 62, 58, 150);
    border-radius: 10px;
}}
QScrollArea#marketFilterScroll {{
    background: transparent;
    border: 0;
}}
QFrame#marketDetailSummary, QFrame#marketChartPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #efede5, stop:1 #d5d2ca);
    border: 1px solid #8b8780;
    border-radius: 10px;
}}
QTableView#marketTableView {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #bfc5bc, stop:0.055 #7c857e, stop:0.056 rgba(25, 29, 28, 240), stop:1 rgba(8, 10, 9, 248));
    border: 1px solid rgba(54, 61, 57, 180);
    border-radius: 10px;
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
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d9d8c9, stop:1 #858b82);
    color: #151911;
    border: 0;
    border-bottom: 1px solid rgba(82, 62, 12, 120);
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
    background: transparent;
    border: 0;
}}
QFrame#supplyHeaderMetric {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(38, 44, 42, 224), stop:0.52 rgba(12, 17, 17, 238), stop:1 rgba(5, 8, 8, 248));
    border: 1px solid rgba(93, 183, 220, 118);
    border-left: 3px solid rgba(255, 210, 31, 168);
    border-radius: 8px;
    min-width: 116px;
}}
QFrame#supplySectionHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0ecdd, stop:0.62 #b5b9b0, stop:1 #737d76);
    border: 1px solid rgba(55, 62, 58, 152);
    border-radius: 9px;
}}
QWidget#supplyDailyPage {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d7dcd4, stop:1 #8d978f);
    border: 1px solid rgba(50, 57, 54, 145);
    border-left: 4px solid rgba(93, 183, 220, 190);
    border-radius: 12px;
}}
QFrame#supplyDailyFreightSection, QFrame#supplyDailyMachineSection {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e7e4d8, stop:0.08 #aeb6af, stop:0.081 rgba(17, 22, 22, 238), stop:1 rgba(5, 8, 8, 250));
    border: 1px solid rgba(60, 68, 64, 168);
    border-top: 2px solid rgba(93, 183, 220, 154);
    border-radius: 9px;
}}
QScrollArea#supplyDailyScroll, QScrollArea#supplyDailyOfferScroll, QWidget#supplyDailyContent {{
    background: transparent;
    border: 0;
}}
QWidget#supplyCommonPage {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d7dcd4, stop:1 #8d978f);
    border: 1px solid rgba(50, 57, 54, 145);
    border-left: 4px solid rgba(255, 210, 31, 185);
    border-radius: 12px;
}}
QFrame#supplySectionSelector, QFrame#supplyToolbar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e8e6da, stop:0.62 #aeb6ae, stop:1 #707a73);
    border: 1px solid rgba(55, 62, 58, 152);
    border-radius: 10px;
}}
QStackedWidget#supplySectionStack {{
    background: transparent;
    border: 0;
}}
QScrollArea#commonSupplyScroll {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(25, 31, 31, 226), stop:1 rgba(6, 9, 9, 246));
    border: 1px solid rgba(54, 62, 58, 170);
    border-radius: 10px;
}}
QWidget#commonSupplyGrid {{
    background: transparent;
}}
QFrame#supplyDailyOfferBand {{
    background: rgba(2, 5, 5, 92);
    border: 1px solid rgba(93, 183, 220, 44);
    border-radius: 8px;
}}
QFrame#commonSupplyCard {{
    background: transparent;
    border: 0;
}}
QFrame#dailyFreightSupplyCard, QFrame#dailyMachineSupplyCard {{
    background: transparent;
    border: 0;
}}
QFrame#commonSupplyCard:hover {{
    background: transparent;
    border: 0;
}}
QFrame#dailyFreightSupplyCard:hover, QFrame#dailyMachineSupplyCard:hover {{
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
QWidget#packsPage {{
    background: {Theme.SECONDARY_SHELL_GRADIENT};
    border: 1px solid {Theme.BORDER_STRONG};
    border-radius: 10px;
}}
QWidget#packResultPage {{
    background: {Theme.SECONDARY_SHELL_GRADIENT};
    border: 1px solid {Theme.BORDER_STRONG};
    border-radius: 10px;
}}
QFrame#packsHeader {{
    background: transparent;
    border: 0;
}}
QFrame#packsHeaderMetric {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(42, 36, 50, 214), stop:0.55 rgba(17, 13, 21, 232), stop:1 rgba(6, 7, 8, 245));
    border: 1px solid rgba(177, 135, 255, 128);
    border-radius: 8px;
}}
QFrame#packsUnopenedHeader, QFrame#packResultHeader {{
    background: {Theme.SECONDARY_SHELL_GRADIENT};
    border: 1px solid {Theme.BORDER_STRONG};
    border-radius: 10px;
}}
QScrollArea#packResultScroll {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d8d8cf, stop:0.5 #c5c7c0, stop:1 #adb1aa);
    border: 1px solid #3b434b;
    border-radius: 10px;
}}
QLabel#guideRecipeRate {{
    background: transparent;
    color: {Theme.SAFETY_YELLOW};
    font-size: 12px;
    font-weight: 900;
}}
QWidget#packResultPage QWidget#packsCanvasViewport {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d8d8cf, stop:0.5 #c5c7c0, stop:1 #adb1aa);
    border: 0;
}}
QScrollArea#boosterPackScroll, QWidget#packsPage QWidget#packsCanvasViewport {{
    background: transparent;
    border: 0;
}}
QWidget#boosterPackGrid, QWidget#packResultGrid {{
    background: transparent;
    border: 0;
}}
QWidget#packResultGrid {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d8d8cf, stop:0.5 #c5c7c0, stop:1 #adb1aa);
}}
QWidget#packsCompositionCanvas {{
    background: transparent;
    border: 0;
}}
QWidget#boosterPackGrid {{
    background: rgba(255, 255, 255, 26);
    border: 1px solid rgba(70, 74, 70, 44);
    border-radius: 10px;
}}
QFrame#boosterPackArt, QFrame#boosterPackCategoryPanel, QFrame#boosterPackActionZone {{
    background: transparent;
    border: 0;
}}
QFrame#packCategoryFlyout {{
    background: rgba(7, 10, 10, 248);
    border: 1px solid rgba(177, 135, 255, 138);
    border-radius: 7px;
}}
QPushButton#packCategorySelector, QPushButton#packCategoryOption {{
    background: rgba(16, 22, 22, 232);
    border: 1px solid rgba(177, 135, 255, 92);
    border-radius: 6px;
    color: {Theme.TEXT};
    font-size: 10px;
    font-weight: 900;
    padding: 2px 8px;
}}
QPushButton#packCategorySelector:hover, QPushButton#packCategoryOption:hover {{
    background: rgba(35, 26, 48, 244);
    border-color: rgba(177, 135, 255, 170);
}}
QPushButton#packCategorySelector:pressed, QPushButton#packCategoryOption:pressed {{
    background: rgba(9, 8, 13, 248);
    border-color: rgba(216, 193, 255, 186);
}}
QPushButton#packCategoryOption[active="true"] {{
    background: rgba(177, 135, 255, 188);
    border-color: rgba(224, 208, 255, 220);
    color: #100d16;
}}
QWidget#leaderboardView {{
    background: transparent;
}}
QFrame#leaderboardPageHeader {{
    background: transparent;
    border: 0;
}}
QFrame#leaderboardHeaderMetric {{
    background: rgba(7, 10, 10, 178);
    border: 1px solid rgba(218, 184, 92, 120);
    border-radius: 8px;
}}
QFrame#leaderboardSwitchDeck {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e3e6e8, stop:0.62 #a5adb4, stop:1 #68727c);
    border: 1px solid #4c5862;
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
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2b3238, stop:1 #11171c);
    border: 1px solid #454e55;
    border-radius: 12px;
}}
QScrollArea#company_levelLeaderboardScroll, QScrollArea#total_earningsLeaderboardScroll {{
    background: transparent;
    border: 1px solid rgba(54, 62, 58, 170);
    border-radius: 10px;
}}
QWidget#company_levelLeaderboardContent, QWidget#total_earningsLeaderboardContent {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(23, 28, 28, 226), stop:1 rgba(6, 9, 9, 246));
    border: 0;
}}
QFrame#leaderboardRow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(35, 41, 40, 236), stop:0.52 rgba(13, 18, 18, 248), stop:1 rgba(5, 7, 7, 255));
    border: 1px solid rgba(142, 154, 150, 92);
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
QFrame#dailyFreightSupplyCard[state="available"], QFrame#dailyMachineSupplyCard[state="available"] {{
    border: 0;
}}
QFrame#dailyFreightSupplyCard[state="purchased"], QFrame#dailyMachineSupplyCard[state="purchased"] {{
    background: transparent;
    border: 0;
}}
QFrame#dailyFreightSupplyCard[state="locked"], QFrame#dailyMachineSupplyCard[state="locked"] {{
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
    color: #18201d;
    font-size: 14px;
    font-weight: 900;
}}
QLabel#marketCardName, QLabel#marketEventName {{
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 800;
}}
QLabel#marketEventName {{
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
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
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 24px;
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
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 17px;
    font-weight: 900;
}}
QLabel#boosterPackType, QLabel#boosterPackCardCount, QLabel#boosterPackCategoryInfo, QLabel#boosterPackArtLabel {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 800;
}}
QFrame#inventoryEmptyState, QFrame#commonSupplyEmptyState, QFrame#packsEmptyState, QFrame#packResultsEmptyState, QFrame#emptyStatePanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 33, 32, 226), stop:1 rgba(7, 10, 10, 246));
    border: 1px solid rgba(255, 210, 31, 78);
    border-radius: 10px;
}}
QLabel#emptyStateTitle {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 18px;
    font-weight: 900;
}}
QLabel#emptyStateMessage {{
    background: transparent;
    border: 0;
    color: {Theme.MUTED};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 12px;
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
    font-size: 13px;
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
    color: #252522;
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
    color: {Theme.TEXT_ON_LIGHT_SECONDARY};
}}
QLabel#marketEventRemaining {{
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
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
QFrame#chartDetailHeader QLabel#chartDetailTitle,
QFrame#chartDetailHeader QLabel#chartDetailAmount,
QFrame#chartDetailHeader QLabel#chartDetailNetChange {{
    color: #1c2421;
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
    color: #252522;
    font-size: 18px;
    font-weight: 800;
}}
QFrame#marketDetailIconHost {{
    background: #333538;
    border: 1px solid #7b7b77;
    border-radius: 7px;
}}
QFrame#marketDetailHeader QLabel#marketDetailChange {{
    color: #4b4945;
}}
QFrame#marketDetailHeader QLabel#sectionLabel {{
    color: #48453f;
    font-size: 11px;
    font-weight: 800;
}}
QFrame#marketDetailHeader QLabel#marketDetailPrice[change="positive"], QFrame#marketDetailHeader QLabel#marketDetailChange[change="positive"] {{
    color: #17613c;
}}
QFrame#marketDetailHeader QLabel#marketDetailPrice[change="negative"], QFrame#marketDetailHeader QLabel#marketDetailChange[change="negative"] {{
    color: #a52222;
}}
QFrame#marketDetailSummary QLabel#marketDetailMetricLabel {{
    color: #55514a;
    font-size: 10px;
}}
QFrame#marketDetailSummary QLabel#marketDetailMetric {{
    color: #242421;
    font-size: 13px;
}}
QFrame#marketDetailHeader QPushButton#marketFilterChip {{
    background: #d2cfc6;
    border-color: #8a857b;
    color: #302e29;
}}
QFrame#marketDetailHeader QPushButton#marketFilterChip[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 #ffd21f, stop:1 #f5a623);
    border-color: #292b2d;
    color: #17191b;
}}
QFrame#marketHeader QLabel#marketMetricValue, QFrame#marketHeader QLabel#marketMetricLabel {{
    color: #17191b;
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
    color: #161a17;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 38px;
    font-weight: 950;
}}
QLabel#contractsHeroSubtitle {{
    background: transparent;
    color: {Theme.HEADER_SUBTITLE_RED};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 12px;
    font-weight: 950;
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
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 11px;
    font-weight: 950;
}}
QFrame#contractRequirementChoice {{
    background: transparent;
    background-color: transparent;
    border: 0;
}}
QPushButton#contractProductSlot {{
    background: transparent;
    background-color: transparent;
    background-image: none;
    border: 0;
    border-image: none;
    border-bottom: 1px solid rgba(140, 161, 154, 72);
    border-radius: 0;
    color: {Theme.MUTED};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 11px;
    font-weight: 900;
    padding: 1px 2px;
    text-align: left;
}}
QPushButton#contractProductSlot:hover {{
    background: transparent;
    background-color: transparent;
    background-image: none;
    border-bottom-color: {Theme.SAFETY_YELLOW};
    color: {Theme.TEXT};
}}
QPushButton#contractProductSlot[selected="true"] {{
    background: transparent;
    background-color: transparent;
    background-image: none;
    color: {Theme.TEXT};
    font-weight: 950;
}}
QPushButton#contractProductSlot:disabled {{
    background: transparent;
    background-color: transparent;
    background-image: none;
    color: {Theme.DIM};
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
QLabel#inventoryCardQuantity, QLabel#inventoryCardStatus {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 11px;
    font-weight: 850;
}}
QLabel#inventoryCardRarity, QLabel#inventoryCardBonus {{
    background: transparent;
    color: {Theme.RESOURCE};
    font-size: 11px;
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
    font-size: 15px;
    font-weight: 900;
    padding: 4px 6px;
}}
QLabel#leaderboardPlayer {{
    background: transparent;
    border: 0;
    color: {Theme.TEXT};
    font-size: 13px;
    font-weight: 900;
}}
QLabel#leaderboardTitle {{
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(255, 255, 255, 18);
    border-radius: 4px;
    color: {Theme.MUTED};
    font-size: 9px;
    font-weight: 900;
    padding: 2px 6px;
}}
QLabel#leaderboardLevel {{
    background: transparent;
    border: 0;
    color: #b8d0d8;
    font-size: 9px;
    font-weight: 900;
}}
QLabel#leaderboardValue {{
    background: transparent;
    color: {Theme.CASH};
    font-size: 14px;
    font-weight: 900;
}}
QLabel#leaderboardSecondaryValue {{
    background: transparent;
    color: {Theme.MUTED};
    font-size: 9px;
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
QLabel#inventoryHeroTitle, QLabel#chartsHeroTitle, QLabel#marketHeroTitle,
QLabel#contractsHeroTitle, QLabel#packsHeaderTitle, QLabel#supplyStoreTitle,
QLabel#leaderboardHeroTitle, QLabel#consortiumHeroTitle, QLabel#consortiumIdentityName {{
    background: transparent;
    color: #161a17;
    font-family: "Segoe UI";
    font-size: 38px;
    font-weight: 900;
}}
QLabel#inventoryHeroSubtitle, QLabel#chartsHeroSubtitle, QLabel#marketHeroSubtitle,
QLabel#contractsHeroSubtitle, QLabel#packsHeaderSubtitle, QLabel#supplyStoreSubtitle,
QLabel#leaderboardHeroSubtitle, QLabel#consortiumHeroSubtitle, QLabel#consortiumIdentityMeta {{
    background: transparent;
    color: {Theme.HEADER_SUBTITLE_RED};
    font-family: "Segoe UI";
    font-size: 12px;
    font-weight: 900;
}}
QLabel#chartsMetricLabel, QLabel#marketMetricLabel, QLabel#contractsMetricLabel,
QLabel#supplyHeaderMetricLabel, QLabel#packsHeaderMetricLabel, QLabel#leaderboardMetricLabel {{
    color: #cfd7cf;
}}
QLabel#chartsMetricValue, QLabel#marketMetricValue, QLabel#contractsMetricValue,
QLabel#supplyHeaderMetricValue, QLabel#packsHeaderMetricValue, QLabel#leaderboardMetricValue {{
    color: {Theme.ENERGY};
}}
QLabel#contractSectionTitle, QLabel#supplySectionTitle, QLabel#packsSectionTitle,
QLabel#leaderboardSwitchLabel {{
    color: #151a17;
}}
QLabel#contractSectionSubtitle {{
    color: {Theme.HEADER_SUBTITLE_RED};
}}
QLabel#supplySectionSubtitle, QLabel#packsUnopenedCount {{
    color: #6d2301;
}}
QLabel#supplyDailySectionTitle {{
    color: #f2f7f1;
}}
QLabel#supplyDailySectionSubtitle {{
    color: {Theme.ENERGY};
}}
QFrame#contractCard QLabel#contractCardTitle,
QFrame#contractCard QLabel#contractBlockTitle,
QFrame#contractCard QLabel#contractRequirementLabel,
QFrame#contractCard QLabel#contractRequirementAmount,
QFrame#contractCard QLabel#contractRewardLabel,
QFrame#contractCard QLabel#contractProductOption,
QFrame#contractCard QLabel#contractProductQuantity {{
    color: {Theme.TEXT};
}}
QPushButton#leaderboardMetricChip {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(38, 43, 42, 214), stop:0.52 rgba(13, 18, 18, 232), stop:1 rgba(5, 7, 7, 248));
    border: 1px solid rgba(142, 154, 150, 92);
    border-radius: 6px;
    color: {Theme.MUTED};
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 10px;
    font-weight: 900;
    padding: 6px 11px;
}}
QPushButton#leaderboardMetricChip:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(48, 55, 53, 226), stop:0.52 rgba(17, 24, 24, 240), stop:1 rgba(7, 10, 10, 252));
    border-color: rgba(255, 210, 31, 128);
    color: {Theme.TEXT};
}}
QPushButton#leaderboardMetricChip[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 {Theme.SAFETY_YELLOW}, stop:0.78 #c88f00, stop:1 #111008);
    border-color: rgba(7, 8, 7, 224);
    color: #10120a;
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
    background: rgba(8, 12, 13, 226);
    color: {Theme.TEXT};
    border: 1px solid rgba(159, 178, 173, 104);
    border-radius: 7px;
    padding: 6px 10px;
    min-width: 120px;
    selection-background-color: rgba(255, 210, 31, 42);
}}
QComboBox:hover {{
    border-color: rgba(255, 210, 31, 112);
    background: rgba(18, 25, 25, 236);
}}
QComboBox:focus {{
    border-color: rgba(255, 210, 31, 156);
}}
QComboBox::drop-down {{
    width: 24px;
    border: 0;
    border-left: 1px solid rgba(142, 154, 150, 52);
}}
QComboBox QAbstractItemView {{
    background: rgba(7, 10, 10, 250);
    color: {Theme.TEXT};
    border: 1px solid rgba(159, 178, 173, 132);
    border-radius: 6px;
    outline: 0;
    padding: 4px;
    selection-background-color: rgba(255, 210, 31, 202);
    selection-color: #15120a;
}}
QComboBox#contractProductSelect {{
    border-color: rgba(255, 210, 31, 94);
    min-width: 118px;
}}
QScrollBar:vertical {{
    background: rgba(6, 8, 8, 112);
    border: 0;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: rgba(142, 154, 150, 132);
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 210, 31, 154);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: 0;
    background: transparent;
}}
QScrollBar:horizontal {{
    background: rgba(6, 8, 8, 112);
    border: 0;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(142, 154, 150, 132);
    border-radius: 4px;
    min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(255, 210, 31, 154);
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: 0;
    background: transparent;
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
QPushButton#buildHallButtonV2:disabled, QPushButton#buildFreightFacilityButton:disabled,
QPushButton#expandResourceStorageButton[factoryV2StorageCta="true"]:disabled {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4b504b, stop:0.5 #343934, stop:1 #1b1e1b);
    color: #9aa19b;
    border-color: #636a64;
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
QPushButton#sellResourceButton, QPushButton#devButton, QPushButton#acceptContractButton, QPushButton#deliverContractButton, QPushButton#claimContractButton, QPushButton#resourcesButton, QPushButton#closeDrawerButton, QPushButton#freightFacilityButton, QPushButton#freightCloseDrawerButton, QPushButton#freightRemoveButton, QPushButton#recycleCardButton, QPushButton#craftCardButton, QPushButton#mkUpgradeButton, QPushButton#expandResourceStorageButton, QPushButton#chartBackButton, QPushButton#chartCashBackButton, QPushButton#marketBackButton, QPushButton#productionGuideButton, QPushButton#buyCommonSupplyButton, QPushButton#buyDailyFreightSupplyButton, QPushButton#buyDailyMachineSupplyButton, QPushButton#openPackButton, QPushButton#backToPacksButton, QPushButton#cardSelectionBackButton, QPushButton#productionSelectionBackButton, QPushButton#selectProductionButton, QPushButton#closeProductionDrawerButton, QPushButton#freightAssignmentBackButton, QPushButton#productionGuideBackButton, QPushButton#chainInspectorBackButton {{
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
QPushButton#sellResourceButton:hover, QPushButton#devButton:hover, QPushButton#acceptContractButton:hover, QPushButton#deliverContractButton:hover, QPushButton#claimContractButton:hover, QPushButton#resourcesButton:hover, QPushButton#closeDrawerButton:hover, QPushButton#freightFacilityButton:hover, QPushButton#freightCloseDrawerButton:hover, QPushButton#freightRemoveButton:hover, QPushButton#recycleCardButton:hover, QPushButton#craftCardButton:hover, QPushButton#mkUpgradeButton:hover, QPushButton#expandResourceStorageButton:hover, QPushButton#chartBackButton:hover, QPushButton#chartCashBackButton:hover, QPushButton#marketBackButton:hover, QPushButton#productionGuideButton:hover, QPushButton#buyCommonSupplyButton:hover, QPushButton#buyDailyFreightSupplyButton:hover, QPushButton#buyDailyMachineSupplyButton:hover, QPushButton#openPackButton:hover, QPushButton#backToPacksButton:hover, QPushButton#cardSelectionBackButton:hover, QPushButton#productionSelectionBackButton:hover, QPushButton#selectProductionButton:hover, QPushButton#closeProductionDrawerButton:hover, QPushButton#freightAssignmentBackButton:hover, QPushButton#productionGuideBackButton:hover, QPushButton#chainInspectorBackButton:hover {{
    background: {Theme.SURFACE_HOVER};
    border-color: rgba(98, 190, 232, 130);
}}
QPushButton#productionGuideButton:hover {{
    border-color: rgba(255, 210, 31, 172);
}}
QPushButton#sellResourceButton:pressed, QPushButton#devButton:pressed, QPushButton#acceptContractButton:pressed, QPushButton#deliverContractButton:pressed, QPushButton#claimContractButton:pressed, QPushButton#resourcesButton:pressed, QPushButton#closeDrawerButton:pressed, QPushButton#freightFacilityButton:pressed, QPushButton#freightCloseDrawerButton:pressed, QPushButton#freightRemoveButton:pressed, QPushButton#recycleCardButton:pressed, QPushButton#craftCardButton:pressed, QPushButton#mkUpgradeButton:pressed, QPushButton#expandResourceStorageButton:pressed, QPushButton#chartBackButton:pressed, QPushButton#chartCashBackButton:pressed, QPushButton#marketBackButton:pressed, QPushButton#productionGuideButton:pressed, QPushButton#buyCommonSupplyButton:pressed, QPushButton#buyDailyFreightSupplyButton:pressed, QPushButton#buyDailyMachineSupplyButton:pressed, QPushButton#openPackButton:pressed, QPushButton#backToPacksButton:pressed, QPushButton#cardSelectionBackButton:pressed, QPushButton#productionSelectionBackButton:pressed, QPushButton#selectProductionButton:pressed, QPushButton#closeProductionDrawerButton:pressed, QPushButton#freightAssignmentBackButton:pressed, QPushButton#productionGuideBackButton:pressed, QPushButton#chainInspectorBackButton:pressed {{
    background: {Theme.SURFACE_2};
    border-color: rgba(98, 190, 232, 180);
}}
QPushButton#deliverContractButton, QPushButton#claimContractButton, QPushButton#selectProductionButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 {Theme.SAFETY_YELLOW}, stop:0.78 #c88f00, stop:1 #111008);
    color: #10120a;
    border: 2px solid rgba(7, 8, 7, 238);
}}
QPushButton#deliverContractButton:hover, QPushButton#claimContractButton:hover, QPushButton#selectProductionButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff690, stop:0.45 #ffdc32, stop:0.78 #d9a10a, stop:1 #18130a);
    border-color: rgba(255, 246, 210, 210);
}}
QPushButton#acceptContractButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 #ffd21f, stop:1 #f5a623);
    color: #17191b;
    border: 1px solid #f5a623;
}}
QPushButton#acceptContractButton:hover {{
    background: #ffe45b;
    border-color: #fff3a1;
}}
QPushButton#acceptContractButton:pressed {{
    background: #f5a623;
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
    background: rgba(232, 231, 220, 168);
    color: #171c19;
    border: 1px solid rgba(53, 60, 56, 126);
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 11px;
    font-weight: 900;
}}
QPushButton#supplySectionButton[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(39, 47, 46, 238), stop:0.55 rgba(10, 15, 15, 248), stop:1 rgba(5, 8, 8, 255));
    color: {Theme.TEXT};
    border: 1px solid rgba(255, 210, 31, 145);
    border-bottom-color: rgba(6, 8, 8, 230);
}}
QPushButton#supplySectionButton:hover {{
    background: rgba(239, 238, 228, 210);
    border-color: rgba(93, 183, 220, 142);
    color: #101512;
}}
QPushButton#supplySectionButton[active="true"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(47, 56, 54, 240), stop:0.56 rgba(13, 19, 19, 250), stop:1 rgba(5, 8, 8, 255));
    color: {Theme.TEXT};
}}
QPushButton#freightFacilityButton[selected="true"] {{
    border-color: {Theme.RESOURCE};
    color: {Theme.TEXT};
}}
QFrame#productionSelectionTile, QFrame#freightAssignmentResourceTile, QFrame#resourceSelectionTile {{
    background: rgba(21, 29, 33, 214);
    border: 1px solid rgba(110, 128, 122, 112);
    border-radius: 8px;
}}
QFrame#productionSelectionTile[current="true"], QFrame#freightAssignmentResourceTile[selected="true"], QFrame#resourceSelectionTile[selected="true"] {{
    background: rgba(24, 34, 35, 238);
    border: 2px solid rgba(255, 210, 31, 202);
}}
QFrame#productionSelectionTile:hover, QFrame#productionSelectionTile:focus, QFrame#freightAssignmentResourceTile:hover, QFrame#freightAssignmentResourceTile:focus, QFrame#resourceSelectionTile:hover, QFrame#resourceSelectionTile:focus {{
    background: rgba(26, 36, 40, 230);
    border-color: rgba(150, 176, 168, 166);
}}
QFrame#resourceSelectionIconHost {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 30), stop:1 rgba(0, 0, 0, 34));
    border: 1px solid rgba(255, 255, 255, 42);
    border-radius: 10px;
}}
QFrame#productionSelectionTile[stageAccent="extractor"] {{
    border-left: 3px solid rgba(107, 188, 132, 190);
}}
QFrame#productionSelectionTile[stageAccent="processor"] {{
    border-left: 3px solid rgba(98, 166, 202, 190);
}}
QFrame#productionSelectionTile[stageAccent="fabricator"] {{
    border-left: 3px solid rgba(177, 141, 222, 190);
}}
QFrame#productionSelectionTile[stageAccent="assembler"] {{
    border-left: 3px solid rgba(219, 154, 98, 190);
}}
QFrame#factoryCardSelectionTile {{
    background: transparent;
    border: 0;
}}
QFrame#factoryCardSelectionTile:hover, QFrame#factoryCardSelectionTile:focus {{
    background: transparent;
    border: 0;
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
QLabel#productionTileName, QLabel#freightAssignmentTileName, QLabel#resourceSelectionTileName {{
    color: {Theme.TEXT};
    font-size: 12px;
    font-weight: 900;
    background: transparent;
}}
QLabel#productionTileCategory, QLabel#productionTileStage, QLabel#freightAssignmentTileMeta, QLabel#freightAssignmentTileStock, QLabel#resourceSelectionTileSubtitle, QLabel#resourceSelectionTileDetail {{
    color: {Theme.MUTED};
    font-size: 10px;
    font-weight: 800;
    background: transparent;
}}
QLabel#productionTileCurrent, QLabel#freightAssignmentTileStatus, QLabel#resourceSelectionTileStatus {{
    background: rgba(59, 200, 118, 24);
    border: 1px solid rgba(59, 200, 118, 110);
    border-radius: 5px;
    color: #7be498;
    font-size: 10px;
    font-weight: 900;
    padding: 3px 7px;
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

QPushButton#marketSelectorOption[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 #ffd21f, stop:1 #f5a623);
    color: #17191b;
    border-color: #292b2d;
}}

QPushButton#cancelContractButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f56a60, stop:1 #b32228);
    color: #ffffff;
    border: 1px solid #ff8b7e;
    border-radius: 5px;
    padding: 6px 10px;
    font-weight: 800;
}}
QPushButton#cancelContractButton:hover {{ background: #e3453d; }}
QPushButton#cancelContractButton:pressed {{ background: #a71e25; }}
QPushButton#acceptContractButton:disabled {{
    background: #323638;
    color: #92999c;
    border-color: #575d60;
}}
QLabel#contractChooseProductTitle {{
    color: #ffd21f;
    background: transparent;
    border: 0;
    font-size: 10px;
    font-weight: 800;
}}
QComboBox#contractProductSelect {{
    background: #202629;
    color: #fff3bc;
    border: 1px solid #ffd21f;
    border-radius: 4px;
    padding: 3px 7px;
}}
QComboBox#contractProductSelect:hover, QComboBox#contractProductSelect:focus {{
    border: 2px solid #ffae25;
    background: #30383c;
}}
QFrame#contractRewardChip[rewardKind="cash"] {{ background: #17673e; border-color: #48d88b; }}
QFrame#contractRewardChip[rewardKind="xp"] {{ background: #155788; border-color: #56bfff; }}
QFrame#contractRewardChip[rewardKind="pack"] {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 #ffd21f, stop:1 #f5a623); border-color: #ffbd30; }}
QFrame#contractRewardChip[rewardKind="cash"] QLabel, QFrame#contractRewardChip[rewardKind="xp"] QLabel {{ color: #ffffff; }}
QFrame#contractRewardChip[rewardKind="pack"] QLabel#contractRewardLabel, QFrame#contractRewardChip[rewardKind="pack"] QLabel#contractRewardIcon {{ color: #17191b; }}

QFrame#marketEventHover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #282f32, stop:1 #111719);
    border: 1px solid #77817f;
    border-top: 3px solid {Theme.SAFETY_YELLOW};
    border-radius: 8px;
}}
QFrame#marketEventHover QLabel {{ background: transparent; border: 0; color: {Theme.TEXT}; font-family: "Segoe UI"; font-size: 12px; }}
QFrame#marketEventHover QLabel#marketEventHoverTitle {{ color: {Theme.SAFETY_YELLOW}; font-size: 17px; font-weight: 800; }}
QFrame#marketEventHover QLabel#marketEventHoverMeta {{ color: #bdc9c6; font-size: 11px; }}
QFrame#marketEventHover QLabel#marketEventHoverCaption {{ color: #bdc9c6; font-size: 10px; font-weight: 800; }}

QLabel#supplyDailySectionTitle {{ color: #151a17; }}
QLabel#supplyDailySectionSubtitle {{ color: {Theme.HEADER_SUBTITLE_RED}; }}

QFrame#dailyFreightSupplyCard QPushButton, QFrame#dailyMachineSupplyCard QPushButton, QFrame#commonSupplyCard QPushButton {{
    padding: 1px 3px;
    font-size: 9px;
    min-height: 0;
}}
QFrame#dailyFreightSupplyCard QPushButton#buyDailyFreightSupplyButton,
QFrame#dailyMachineSupplyCard QPushButton#buyDailyMachineSupplyButton,
QFrame#commonSupplyCard QPushButton#buyCommonSupplyButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff690, stop:0.38 {Theme.SAFETY_YELLOW}, stop:1 #f5a623);
    color: #15170f;
    border: 1px solid #fff2a0;
    border-bottom: 2px solid #9f6700;
    border-radius: 6px;
    padding: 2px 6px;
    font-family: {Theme.INDUSTRIAL_FONT};
    font-size: 12px;
    font-weight: 950;
}}
QFrame#dailyFreightSupplyCard QPushButton#buyDailyFreightSupplyButton:hover,
QFrame#dailyMachineSupplyCard QPushButton#buyDailyMachineSupplyButton:hover,
QFrame#commonSupplyCard QPushButton#buyCommonSupplyButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fffac0, stop:0.42 #ffe45b, stop:1 #ffb128);
    border-color: #fffbd7;
}}
QFrame#dailyFreightSupplyCard QPushButton#buyDailyFreightSupplyButton:pressed,
QFrame#dailyMachineSupplyCard QPushButton#buyDailyMachineSupplyButton:pressed,
QFrame#commonSupplyCard QPushButton#buyCommonSupplyButton:pressed {{
    background: #e99a12;
    border-top: 2px solid #9f6700;
    border-bottom: 1px solid #ffe67a;
}}
QFrame#dailyFreightSupplyCard QPushButton#buyDailyFreightSupplyButton:disabled,
QFrame#dailyMachineSupplyCard QPushButton#buyDailyMachineSupplyButton:disabled,
QFrame#commonSupplyCard QPushButton#buyCommonSupplyButton:disabled {{
    background: #343a3c;
    color: #89918f;
    border: 1px solid #555d5d;
}}
QWidget#packsView QFrame#packsEmptyState {{
    background: transparent;
    border: 0;
}}
QFrame#packsEmptyState QLabel#emptyStateTitle {{
    font-family: "Segoe UI";
    color: {Theme.TEXT_ON_LIGHT_PRIMARY};
    font-size: 23px;
    font-weight: 800;
    letter-spacing: 2px;
}}
QFrame#packsEmptyState QLabel#emptyStateMessage {{
    font-family: "Segoe UI";
    color: {Theme.TEXT_ON_LIGHT_SECONDARY};
    font-size: 14px;
}}
QWidget#packsView QLabel#packsSectionTitle, QWidget#packsView QLabel#packsUnopenedCount,
QLabel#packResultsLabel {{
    color: {Theme.TEXT_ON_LIGHT_SECONDARY};
    background: transparent;
}}
QPushButton#confirmCollectButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe46b, stop:0.5 #ffd21f, stop:1 #d9aa08);
    color: #151a1c;
    border: 1px solid #ffe985;
    border-bottom: 3px solid #92700a;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 900;
    letter-spacing: 1px;
}}
QPushButton#confirmCollectButton:hover {{ background: #ffe16a; }}
QPushButton#confirmCollectButton:pressed {{ background: #e6b90e; }}
QFrame#leaderboardPinnedContainer {{ background: transparent; border: 0; }}
QLabel#leaderboardSearchStatus {{ color: #202d36; background: transparent; font-size: 11px; }}
QFrame#leaderboardRow[alternating="true"][ownPlayer="false"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #293138, stop:0.52 #141c22, stop:1 #0c1217);
}}
QFrame#leaderboardRow[located="true"] {{ border: 2px solid #ffd21f; }}
"""

APP_STYLESHEET += f"""
QWidget#consortiumView {{ background: #172023; color: #eaf0e9; font-family: {Theme.INDUSTRIAL_FONT}; }}
QWidget#consortiumLanding, QWidget#consortiumMemberWorkspace {{ background: #172023; }}
QFrame#consortiumMainHeader, QFrame#consortiumIdentityHeader {{ background: transparent; border: 0; }}
QFrame#consortiumHeaderProgressModule {{ background: #162322; border: 1px solid #58816b; border-radius: 8px; }}
QLabel#consortiumIdentityLevel, QLabel#consortiumProgressionLevel {{ color: #42a768; font-size: 20px; font-weight: 950; }}
QLabel#consortiumNextMilestone {{ color: #9fd1ac; font-size: 10px; font-weight: 850; }}
QFrame#consortiumDirectoryRow {{ background: #1c2528; border: 1px solid #687672; border-left: 3px solid #4c9bbb; border-radius: 4px; }}
QLabel#consortiumDirectoryName {{ color: #f0f4ef; font-size: 14px; font-weight: 950; }}
QLabel#consortiumDirectoryMeta {{ color: #b9c5c0; font-size: 10px; font-weight: 800; }}
QProgressBar#consortiumXpProgress, QProgressBar#consortiumXpProgressLarge {{ background: #1c282b; color: #eaf6f4; border: 1px solid #65736f; border-radius: 4px; text-align: center; font-weight: 900; }}
QProgressBar#consortiumXpProgress {{ min-height: 24px; max-height: 24px; font-size: 11px; }}
QProgressBar#consortiumXpProgressLarge {{ min-height: 24px; max-height: 24px; }}
QProgressBar#consortiumXpProgress::chunk, QProgressBar#consortiumXpProgressLarge::chunk {{ background: #2d9bc1; }}
QTabWidget#consortiumMemberTabs::pane {{ border: 1px solid #53635b; background: #11191c; top: -1px; }}
QFrame#consortiumOperationCard, QFrame#consortiumContractHeader, QFrame#consortiumContractMetadata, QFrame#consortiumEligibilityPanel,
QFrame#consortiumMemberActions, QFrame#consortiumChairmanSettings {{ background: #1b2427; border: 1px solid #66736f; border-radius: 5px; }}
QLabel#consortiumSectionTitle {{ color: #f1f4ef; font-size: 14px; font-weight: 950; letter-spacing: 1px; }}
QLabel#consortiumSectionLabel, QLabel#consortiumMetricLabel {{ color: #9fb0aa; font-size: 9px; font-weight: 850; }}
QLabel#consortiumMetricValue {{ color: #f2f5ef; font-size: 15px; font-weight: 950; }}
QLabel#consortiumMutedText, QLabel#consortiumActivityLine {{ color: #aebbb6; font-size: 10px; }}
QFrame#consortiumRequirementRow {{ background: #222d30; border: 1px solid #5e6d68; border-left: 3px solid #2c96b9; border-radius: 4px; }}
QLabel#consortiumRequirementName {{ color: #f2f5f0; font-size: 13px; font-weight: 950; }}
QLabel#consortiumRequirementValue {{ color: #f1d856; font-size: 13px; font-weight: 950; }}
QProgressBar#consortiumRequirementProgress, QProgressBar#consortiumContractProgress {{ background: #101719; border: 1px solid #596762; border-radius: 3px; color: #e8eeee; text-align: center; }}
QProgressBar#consortiumRequirementProgress::chunk, QProgressBar#consortiumContractProgress::chunk {{ background: #46a66e; }}
QLabel#consortiumContractState {{ color: #ffd21f; font-weight: 950; }}
QLabel#consortiumEligibilityValue {{ color: #c4ccc8; font-size: 14px; font-weight: 950; }}
QLabel#consortiumEligibilityValue[satisfied="true"], QLabel#consortiumEligibilityGranted {{ color: #62d68b; font-weight: 950; }}
QLabel#consortiumEligibilityReason {{ color: #efa84b; font-weight: 900; }}
QFrame#consortiumMilestoneRow {{ background: #283234; border: 1px solid #64716d; border-left: 4px solid #5c6965; border-radius: 4px; }}
QFrame#consortiumMilestoneRow[milestoneState="complete"] {{ border-left-color: #46a66e; }}
QFrame#consortiumMilestoneRow[milestoneState="current"] {{ border-left-color: #ffd21f; }}
QLabel#consortiumMilestoneLevel {{ color: #79c7e2; font-weight: 950; }}
QLabel#consortiumMilestoneCapacity, QLabel#consortiumMilestoneState {{ color: #edf2ee; font-weight: 850; }}
QLabel#consortiumMaximumState {{ color: #62d68b; font-size: 15px; font-weight: 950; }}
QLabel#consortiumDialogTitle {{ color: #16201d; font-size: 18px; font-weight: 950; }}
QLabel#consortiumFormError {{ color: #a72d31; font-weight: 900; }}
QWidget#consortiumDirectoryHost {{ background: #202a2d; border: 1px solid #68736f; }}
QScrollArea#consortiumDirectoryScroll {{ background: #202a2d; border: 1px solid #7e8781; }}
QFrame#consortiumDirectoryEmpty {{ background: #202a2d; border: 1px dashed #687b73; min-height: 360px; }}
QFrame#consortiumDirectoryEmpty QLabel#emptyStateTitle {{ color: #f2f4ee; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 20px; font-weight: 950; letter-spacing: 1px; }}
QFrame#consortiumDirectoryEmpty QLabel#emptyStateMessage {{ color: #bac9c2; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 12px; }}
QProgressBar#consortiumXpProgress::chunk, QProgressBar#consortiumXpProgressLarge::chunk {{ background: #48ab69; }}
QTabWidget#consortiumMemberTabs QTabBar::tab {{ min-height: 31px; min-width: 116px; font-size: 12px; }}
QFrame#consortiumOperationCard {{ background: #182226; border: 1px solid #77847e; border-top: 5px solid #5f7972; border-bottom: 3px solid #56645e; }}
QFrame#consortiumOperationCard[operation="status"] {{ border-top-color: #46a66e; }}
QFrame#consortiumActivityEntry {{ background: #253035; border-left: 3px solid #6093a3; border-bottom: 1px solid #45565b; }}
QLabel#consortiumActivityLine {{ color: #e0e9e2; font-size: 11px; font-weight: 700; }}
QFrame#consortiumProductSelection {{ background: #1b2629; border: 1px solid #687b76; border-left: 4px solid #d8b42e; }}
QLabel#consortiumProductPreviewReward {{ color: #76c994; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 11px; font-weight: 900; }}
QFrame#consortiumRequirementRow {{ min-height: 54px; }}
QProgressBar#consortiumRequirementProgress {{ min-height: 15px; max-height: 15px; }}
QFrame#consortiumRosterHousing {{ background: #263135; border: 1px solid #78857d; border-bottom: 3px solid #596a61; }}
QFrame#consortiumRosterHeader {{ background: #344146; border-bottom: 2px solid #72837a; }}
QLabel#consortiumRosterHeading {{ color: #d8e3dc; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 10px; font-weight: 950; letter-spacing: 1px; }}
QScrollArea#consortiumRosterScroll, QWidget#consortiumRosterBody {{ background: #172124; border: 0; }}
QFrame#consortiumRosterRow {{ background: #1d292c; border-bottom: 1px solid #354348; }}
QFrame#consortiumRosterRow[role="chairman"] {{ border-left: 4px solid #e2bd38; }}
QFrame#consortiumRosterRow[role="board_member"] {{ border-left: 4px solid #6aa3b2; }}
QFrame#consortiumRosterRow[selected="true"] {{ background: #344645; border: 1px solid #d3b132; }}
QLabel#consortiumRosterCell {{ color: #ecf0e9; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 11px; font-weight: 800; }}
QLabel#consortiumRosterRole {{ color: #b6cfc2; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 10px; font-weight: 900; }}
QFrame#consortiumRosterRow[role="chairman"] QLabel#consortiumRosterRole {{ color: #ffe16a; }}
QFrame#consortiumRosterRow[role="board_member"] QLabel#consortiumRosterRole {{ color: #83cade; }}
QFrame#consortiumChairmanSettings {{ border-top: 4px solid #69857a; }}
QComboBox#consortiumSettingsPolicy, QLineEdit#consortiumSettingsMinimum {{ background: #111b1e; color: #e8eee8; border: 1px solid #64766e; min-height: 29px; padding: 3px 8px; font-family: {Theme.INDUSTRIAL_FONT}; font-weight: 800; }}
QFrame#consortiumDangerArea {{ background: #201c1d; border-top: 1px solid #7e5658; }}
QLabel#consortiumInviteResolved {{ color: #1f3028; font-size: 13px; font-weight: 900; }}
QLabel#consortiumInviteEligibility {{ color: #28784d; font-size: 11px; font-weight: 900; }}
QWidget#consortiumCreateDialog, QWidget#consortiumContributionDialog, QWidget#consortiumInviteDialog {{ background: rgba(6, 13, 16, 198); }}
QFrame#consortiumCreateDialog, QFrame#consortiumContributionDialog, QFrame#consortiumInviteDialog {{ background: rgba(6, 13, 16, 198); }}
QFrame#consortiumConfirmDialog {{ background: rgba(6, 13, 16, 198); }}
QFrame#consortiumConfirmDialog QLabel#consortiumDialogTitle {{ color: #17221e; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 20px; font-weight: 950; }}
QFrame#consortiumConfirmDialog QLabel#consortiumConfirmMessage {{ color: #26352f; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 12px; }}
QFrame#consortiumModalPanel {{ background: #d1d7d2; border: 2px solid #76847b; border-top: 6px solid #d6ae20; border-bottom: 4px solid #59665f; border-radius: 5px; }}
QFrame#consortiumModalPanel QLabel#consortiumDialogTitle {{ color: #17221e; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 20px; font-weight: 950; letter-spacing: 1px; }}
QFrame#consortiumModalPanel QLabel {{ color: #26352f; font-family: {Theme.INDUSTRIAL_FONT}; font-weight: 800; }}
QFrame#consortiumModalPanel QLineEdit, QFrame#consortiumModalPanel QComboBox, QFrame#consortiumModalPanel QSpinBox {{ background: #172225; color: #f0f5ee; border: 1px solid #66776e; border-radius: 3px; min-height: 28px; padding: 3px 8px; font-family: {Theme.INDUSTRIAL_FONT}; font-weight: 800; }}
QFrame#consortiumModalPanel QFrame#resourceSelectionTile QLabel {{ color: #eaf0e9; }}
QFrame#consortiumModalPanel QFrame#resourceSelectionTile QLabel#resourceSelectionTileSubtitle,
QFrame#consortiumModalPanel QFrame#resourceSelectionTile QLabel#resourceSelectionTileDetail {{ color: #acbdb4; }}
QFrame#consortiumModalPanel QFrame#resourceSelectionTile QLabel#resourceSelectionTileStatus {{ color: #6cda91; }}
"""

# Scoped convergence: material hierarchy of the existing secondary workspaces.
APP_STYLESHEET += f"""
QWidget#consortiumView {{ background: {Theme.SECONDARY_SHELL_GRADIENT}; border: 2px solid {Theme.BORDER_STRONG}; border-radius: 10px; }}
QWidget#consortiumLanding, QWidget#consortiumMemberWorkspace {{ background: transparent; border: 0; }}
QWidget#consortiumView QScrollArea {{ background: transparent; border: 0; }}
QWidget#consortiumDirectoryHost {{ background: {Theme.SURFACE_1}; border: 1px solid {Theme.BORDER_STRONG}; border-radius: 8px; }}
QFrame#consortiumDirectoryEmpty {{ background: {Theme.SURFACE_1}; border: 0; min-height: 220px; }}
QFrame#consortiumHeaderProgressModule, QFrame#consortiumOperationCard, QFrame#consortiumRosterHousing {{ background: transparent; border: none; }}
QLabel#consortiumIdentityLevel, QLabel#consortiumProgressionLevel {{ color: {Theme.SAFETY_YELLOW}; }}
QLabel#consortiumNextMilestone {{ color: {Theme.TEXT}; }}
QTabWidget#consortiumMemberTabs::pane {{ background: transparent; border: 0; }}
QFrame#consortiumContractHeader, QFrame#consortiumContractMetadata, QFrame#consortiumEligibilityPanel,
QFrame#consortiumMemberActions, QFrame#consortiumChairmanSettings, QFrame#consortiumProductSelection {{ background: {Theme.SURFACE_1}; border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 3px solid {Theme.SURFACE_0}; border-radius: 8px; }}
QFrame#consortiumDirectoryRow, QFrame#consortiumRequirementRow, QFrame#consortiumMilestoneRow {{ background: {Theme.SURFACE_2}; border-color: {Theme.BORDER_STRONG}; }}
QFrame#consortiumRosterHeader {{ background: {Theme.SURFACE_3}; border-bottom: 2px solid {Theme.BORDER_STRONG}; }}
QScrollArea#consortiumRosterScroll, QWidget#consortiumRosterBody {{ background: {Theme.SURFACE_1}; border: 0; }}
QFrame#consortiumRosterRow {{ background: {Theme.SURFACE_2}; border-bottom: 1px solid {Theme.BORDER}; }}
QFrame#consortiumRosterRow:hover {{ background: {Theme.SURFACE_HOVER}; }}
QFrame#consortiumRosterRow[selected="true"] {{ background: {Theme.SURFACE_3}; border: 1px solid {Theme.SAFETY_YELLOW}; }}
QFrame#consortiumActivityEntry {{ background: {Theme.SURFACE_3}; border-left: 3px solid {Theme.RESOURCE}; border-bottom: 1px solid {Theme.BORDER}; }}
QProgressBar#consortiumXpProgress, QProgressBar#consortiumXpProgressLarge {{ background: {Theme.SURFACE_0}; border-color: {Theme.BORDER_STRONG}; }}
QProgressBar#consortiumXpProgress::chunk, QProgressBar#consortiumXpProgressLarge::chunk {{ background: {Theme.RESOURCE}; }}
QWidget#consortiumView QLabel#consortiumSectionTitle, QWidget#consortiumView QLabel#consortiumProgressionLevel {{ color: {Theme.TEXT}; }}
QFrame#consortiumOperationCard QLabel#consortiumSectionTitle,
QFrame#consortiumChairmanSettings QLabel#consortiumSectionTitle,
QFrame#consortiumContractHeader QLabel#consortiumSectionTitle,
QFrame#consortiumMemberActions QLabel#consortiumSectionTitle {{ color: {Theme.TEXT}; }}
"""

APP_STYLESHEET += f"""
QPushButton#consortiumProfileLink {{ background: transparent; color: {Theme.TEXT}; border: none; padding: 0; text-align: left; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 11px; font-weight: 800; }}
QPushButton#consortiumProfileLink:hover, QPushButton#consortiumProfileLink:focus {{ color: {Theme.SAFETY_YELLOW}; text-decoration: underline; }}
"""

APP_STYLESHEET += "QStackedWidget#consortiumStack { background: transparent; border: 0; }"

APP_STYLESHEET += f"""
QWidget#consortiumLanding QPushButton#inventoryFilterChip:!checked {{ background: {Theme.SECONDARY_SURFACE}; color: {Theme.TEXT_ON_LIGHT_PRIMARY}; border-color: {Theme.BORDER_STRONG}; }}
QWidget#consortiumLanding QPushButton#inventoryFilterChip:hover:!checked {{ background: {Theme.SECONDARY_SHELL_LIGHT}; }}
"""

APP_STYLESHEET += "QTabWidget#consortiumMemberTabs QTabBar { background: transparent; border: 0; }"

APP_STYLESHEET += """
QTabWidget#consortiumMemberTabs QTabBar::tab { font-family: Bahnschrift; font-size: 13px; min-width: 126px; min-height: 20px; }
QFrame#consortiumPageChassis, QFrame#consortiumContractSection { background: transparent; border: 0; }
QScrollArea#consortiumOverview, QScrollArea#consortiumContracts, QScrollArea#consortiumMembers, QScrollArea#consortiumProgression { background: transparent; border: 0; }
QLabel#consortiumBigStat { font-family: 'Segoe UI'; font-size: 25px; font-weight: 900; color: #ffd21f; }
QLabel#consortiumRosterHeading { font-family: 'Segoe UI'; font-size: 12px; }
QLabel#consortiumRosterCell, QLabel#consortiumRosterRole { font-family: 'Segoe UI'; font-size: 14px; }
QPushButton#consortiumProfileLink { font-family: 'Segoe UI'; font-size: 14px; text-align: left; padding: 4px; }
QMenu#consortiumMemberMenu { background: #1b2225; color: #edf0ef; border: 2px solid #727773; border-radius: 6px; padding: 7px; font-size: 14px; }
QMenu#consortiumMemberMenu::item { padding: 10px 18px; }
QMenu#consortiumMemberMenu::item:selected { background: #ffd21f; color: #111719; border-radius: 4px; }
QFrame#consortiumRosterRow:focus { border: 1px solid #ffd21f; }
QFrame#consortiumContractSection QFrame#consortiumRequirementRow { background: transparent; border: 0; }
QTabWidget#consortiumMemberTabs, QTabWidget#consortiumMemberTabs QStackedWidget,
QWidget#consortiumWorkspaceViewport, QFrame#consortiumPageChassis { background: transparent; border: 0; }
QFrame#consortiumStatModule { background: transparent; border: 0; }
QFrame#consortiumProductSelection { background: #3d4240; border: 1px solid #75828a; border-bottom: 2px solid #0b1112; border-radius: 8px; }
QFrame#consortiumContractMetadata, QFrame#consortiumEligibilityPanel { background: #282c2b; border: 1px solid #58636a; border-radius: 6px; }
QFrame#consortiumChairmanSettings { background: #303534; border: 1px solid #75828a; border-radius: 8px; }
"""

# Consortium contrast pass: layout-neutral wrappers must reveal their parent.
APP_STYLESHEET += f"""
QWidget#consortiumMemberWorkspace QTabBar, QTabWidget#consortiumMemberTabs QTabBar QWidget,
QFrame#consortiumLayoutHost, QWidget#consortiumView QFrame#contractRequirementChoice {{ background: transparent; border: 0; }}
QFrame#consortiumProductSelection, QFrame#consortiumChairmanSettings {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Theme.SECONDARY_SHELL_LIGHT}, stop:1 {Theme.SECONDARY_SHELL_MID});
    border-color: {Theme.SECONDARY_SHELL_DARK};
}}
QFrame#consortiumStatModule QLabel,
QWidget#consortiumView QFrame#consortiumProductSelection > QLabel,
QWidget#consortiumView QFrame#consortiumChairmanSettings > QLabel {{ background: transparent; color: {Theme.TEXT_ON_LIGHT_PRIMARY}; }}
QFrame#consortiumStatModule QLabel#consortiumMetricLabel,
QFrame#consortiumChairmanSettings QLabel#consortiumMetricLabel {{ color: {Theme.TEXT_ON_LIGHT_SECONDARY}; }}
"""

APP_STYLESHEET += f"""
QFrame#consortiumActiveRequirements {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {Theme.SECONDARY_SHELL_LIGHT},stop:1 {Theme.SECONDARY_SHELL_MID}); border: 0; border-radius: 8px; }}
QFrame#consortiumActiveRequirements QFrame#consortiumRequirementRow > QLabel {{ color: {Theme.TEXT_ON_LIGHT_PRIMARY}; background: transparent; }}
"""
