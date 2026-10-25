"""Opt-in source/frozen QA, isolated by an explicit temporary LOCALAPPDATA."""
import os

if os.environ.get('INDUSTRIOVA_PERFORMANCE_SMOKE_ROOT'):
    import json
    from pathlib import Path
    import sys
    import traceback
    from time import monotonic, sleep
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication, QPushButton, QTabWidget
    from production_zero.persistence.paths import default_company_save_path
    from production_zero.ui import main_window as module

    root = Path(os.environ['INDUSTRIOVA_PERFORMANCE_SMOKE_ROOT']).resolve()
    assert default_company_save_path().resolve().is_relative_to(root)
    number = int(os.environ.get('INDUSTRIOVA_PERFORMANCE_SMOKE_PASS', '1'))

    class PerformanceSmokeWindow(module.MainWindow):
        def __init__(self, **kwargs):
            for name in ('segoeui.ttf', 'segoeuib.ttf', 'bahnschrift.ttf', 'consola.ttf'):
                path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / name
                if path.is_file():
                    QFontDatabase.addApplicationFont(str(path))
            super().__init__(**kwargs)
            QTimer.singleShot(800, self.probe)

        def failed(self):
            (root / f'error-{number}.txt').write_text(traceback.format_exc(), encoding='utf-8')
            QApplication.instance().exit(1)

        def probe(self):
            try:
                # Keep diagnostic timers running, stop only the game's timers.
                for timer in self.findChildren(QTimer):
                    timer.stop()
                from importlib.resources import files
                from production_zero.data.definitions import load_card_definitions
                from production_zero.core.commands import InstallCardInHall, SelectMachineProduction, InstallFreightCard, AssignFreightCard
                from production_zero.core.simulation import SimulationEngine
                from production_zero.ui.dev_tools_view import DevToolsView
                self.probe_start = monotonic()
                s = self._session_state
                defs = load_card_definitions(files('production_zero.data') / 'game_definitions.json')
                if number == 1:
                    assert s.cash.amount == 1250 and len(s.cards) == 8 and not s.installed_card_ids()
                    InstallCardInHall('plant-1', 0, 'test-solar-common-001', 'energy').apply(s)
                    InstallCardInHall('site-1', 0, 'test-drill-common-001', 'resources').apply(s)
                    SelectMachineProduction('test-drill-common-001', 'resource.iron_ore', 'iron_ore').apply(s)
                    engine = SimulationEngine(defs)
                    engine.advance_time(s, 60)
                    InstallCardInHall('hall-1', 0, 'test-furnace-common-001', 'factory').apply(s)
                    SelectMachineProduction('test-furnace-common-001', 'recipe.processor.iron', 'iron').apply(s)
                    for i in range(2):
                        card = f'starter-truck-common-00{i+1}'
                        InstallFreightCard('garage-1', i, card, defs).apply(s)
                        AssignFreightCard(card, 'iron', 'market').apply(s)
                    engine.advance_time(s, 180)
                    s.production_progress.pending_unlock_ids.clear()
                assert s.production_progress.lifetime_produced['iron'] > 0 and s.statistics.total_earnings > 0
                assert self._save_session(wait=True)
                diag = QApplication.instance().performance_probe
                assert diag is not None
                assert diag.recorder.summary()['logger_error'] is None
                tabs = self.findChild(QTabWidget, 'mainTabs')
                dev = self.findChild(DevToolsView)
                assert dev is not None
                tabs.setCurrentWidget(dev)
                buttons = {b.text(): b for b in dev.findChildren(QPushButton)}
                assert 'EXPORT TEST REPORT (F9)' in buttons
                buttons['SET TEST START'].click()
                self.diag = diag
                self.smoke_buttons = buttons
                self.smoke_phase = 'baseline'
                self.smoke_timer = QTimer(self)
                self.smoke_timer.timeout.connect(self.finish_probe)
                self.smoke_timer.start(150)
            except BaseException:
                self.failed()

        def finish_probe(self):
            try:
                if monotonic() - self.probe_start > 40:
                    raise TimeoutError('Performance smoke export timed out')
                diag = self.diag
                diag._poll()
                if diag._future is not None:
                    return
                if self.smoke_phase == 'baseline':
                    assert (diag.directory / 'baseline.sqlite').is_file()
                    # A known pause must be present in the event/heartbeat data.
                    sleep(.22)
                    self.smoke_buttons['MARK STUTTER (F8)'].click()
                    self.smoke_phase = 'sample'
                    return
                if self.smoke_phase == 'sample':
                    if diag.recorder.summary()['samples'] < 1:
                        return
                    self.smoke_buttons['EXPORT TEST REPORT (F9)'].click()
                    self.smoke_phase = 'export'
                    return
                assert diag.last_export and diag.last_export.is_file()
                assert self.grab().save(str(root / f'dev-tools-{number}.png'))
                tabs = self.findChild(QTabWidget, 'mainTabs')
                tabs.setCurrentIndex(0)
                QApplication.processEvents()
                assert self.grab().save(str(root / f'game-{number}.png'))
                s = self._session_state
                report = {'pass_number': number, 'frozen': bool(getattr(sys, 'frozen', False)),
                          'cards': len(s.cards), 'earnings': s.statistics.total_earnings,
                          'iron_produced': s.production_progress.lifetime_produced['iron'],
                          'save_path': str(default_company_save_path()),
                          'session': str(diag.directory), 'report': str(diag.last_export)}
                (root / f'pass-{number}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                self.smoke_timer.stop()
                self.close()
            except BaseException:
                self.smoke_timer.stop()
                self.failed()

    module.MainWindow = PerformanceSmokeWindow
