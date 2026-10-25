"""Opt-in packaged smoke probe, strictly confined to an explicit test folder."""
import os
if os.environ.get('INDUSTRIOVA_ECONOMY_SMOKE_ROOT'):
    import json,sys,traceback
    from pathlib import Path
    from importlib.resources import files
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication,QLabel,QTabWidget,QLineEdit
    from production_zero.ui import main_window as module
    from production_zero.persistence.paths import default_company_save_path
    from production_zero.persistence.sqlite_store import serialize_game_state
    root=Path(os.environ['INDUSTRIOVA_ECONOMY_SMOKE_ROOT']).resolve()
    assert default_company_save_path().resolve().is_relative_to(root)
    number=int(os.environ.get('INDUSTRIOVA_ECONOMY_SMOKE_PASS','1'))
    class EconomySmokeWindow(module.MainWindow):
        def __init__(self,**kwargs):
            # The offscreen Qt platform may not enumerate Windows system fonts.
            # Register existing fonts explicitly only in this opt-in QA mode.
            from PySide6.QtGui import QFontDatabase
            for name in ('segoeui.ttf','segoeuib.ttf','bahnschrift.ttf','consola.ttf'):
                path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name
                if path.is_file():QFontDatabase.addApplicationFont(str(path))
            super().__init__(**kwargs)
            QTimer.singleShot(800,self.probe)
        def probe(self):
            try:
                for timer in self.findChildren(QTimer):timer.stop()
                from production_zero.data.definitions import load_card_definitions
                from production_zero.core.commands import InstallCardInHall,SelectMachineProduction,InstallFreightCard,AssignFreightCard,PurchaseHall
                from production_zero.core.simulation import SimulationEngine
                from production_zero.core.market import BASE_MARKET_PRICES
                from production_zero.core.mk_upgrades import mk_upgrade_cost
                from production_zero.ui.factory_view_v2 import FactoryViewV2
                from production_zero.ui.factory_view import ProductionGuideTile
                s=self._session_state;defs=load_card_definitions(files('production_zero.data')/'game_definitions.json')
                if number==1:
                    assert s.cash.amount==1250 and len(s.cards)==8 and not s.installed_card_ids()
                    InstallCardInHall('plant-1',0,'test-solar-common-001','energy').apply(s)
                    InstallCardInHall('site-1',0,'test-drill-common-001','resources').apply(s)
                    SelectMachineProduction('test-drill-common-001','resource.iron_ore','iron_ore').apply(s)
                    engine=SimulationEngine(defs);engine.advance_time(s,60)
                    assert 'recipe.processor.iron' in s.production_progress.unlocked_production_ids
                    InstallCardInHall('hall-1',0,'test-furnace-common-001','factory').apply(s)
                    SelectMachineProduction('test-furnace-common-001','recipe.processor.iron','iron').apply(s)
                    for i in range(2):
                        cid=f'starter-truck-common-00{i+1}'
                        InstallFreightCard('garage-1',i,cid,defs).apply(s);AssignFreightCard(cid,'iron','market').apply(s)
                    engine.advance_time(s,180)
                    assert s.production_progress.lifetime_produced['iron']>0 and s.statistics.total_earnings>0
                    # Separate synthetic funded infrastructure probe, not a
                    # claim that a new player earns ten halls in three minutes.
                    s.cash.amount=1e12
                    original=serialize_game_state(s)['halls']['hall-1']
                    for _ in range(10):PurchaseHall().apply(s)
                    assert len(s.halls)==11 and serialize_game_state(s)['halls']['hall-1']==original
                    s.production_progress.pending_unlock_ids.clear()
                    self._save_store.save('company',s)
                else:
                    assert len(s.halls)==11 and s.statistics.total_earnings>0
                assert s.economy_version==2 and BASE_MARKET_PRICES['iron']==4 and BASE_MARKET_PRICES['flour']==2
                view=self.findChild(FactoryViewV2);view._selected_hall_id='hall-1';view.refresh_view()
                tabs=self.findChild(QTabWidget,'mainTabs');tabs.setCurrentWidget(view)
                from production_zero.ui import release_board
                quoted=[];original_confirm=release_board.confirm
                def show_quote(parent,title,body):
                    quoted.append(body)
                    def capture_quote():
                        dialog=QApplication.activeModalWidget()
                        assert dialog.grab().save(str(root/f'upgrade-{number}.png'))
                        dialog.reject()
                    QTimer.singleShot(100,capture_quote)
                    return original_confirm(parent,title,body)
                release_board.confirm=show_quote
                try:view._upgrade_selection('test-furnace-common-001')
                finally:release_board.confirm=original_confirm
                quote=mk_upgrade_cost(s.cards['test-furnace-common-001'],defs['machine.processor'])
                assert quoted and f'${quote:,.2f}' in quoted[0]
                view._open_production_guide()
                view.findChild(QLineEdit,'productionGuideSearchInput').setText('iron')
                QApplication.processEvents()
                iron=next(tile for tile in view.findChildren(ProductionGuideTile) if tile.property('resourceId')=='iron')
                assert '$4.00' in iron.toolTip()
                view._open_chain_from_guide('flour')
                assert '120 / MIN' in view.findChild(QLabel,'chainSummaryRateValue').text()
                QApplication.processEvents()
                assets=list(files('production_zero').joinpath('assets/resources').iterdir())
                assert len([p for p in assets if p.name.endswith('.png')])>=353
                assert all(p.is_file() and p.stat().st_size>0 for p in assets)
                image=root/f'pass-{number}.png';assert self.grab().save(str(image))
                self._save_store.save('company',s)
                loaded=self._save_store.load('company')
                for key in ('cash','cards','resources','halls','machine_production','research','company'):
                    assert serialize_game_state(loaded)[key]==serialize_game_state(s)[key],key
                report=dict(pass_number=number,frozen=bool(getattr(sys,'frozen',False)),new_game=number==1,processing_produced=s.production_progress.lifetime_produced['iron'],earnings=s.statistics.total_earnings,factory_halls=len(s.halls),iron_price=4,flour_price=2,mk_quote=quote,quote_dialog=quoted[0],save_load=True,assets=len(assets),screenshot=str(image),save_path=str(default_company_save_path()))
                (root/f'pass-{number}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                self.close()
            except BaseException:
                (root/f'error-{number}.txt').write_text(traceback.format_exc(),encoding='utf-8')
                QApplication.instance().exit(1)
    module.MainWindow=EconomySmokeWindow
