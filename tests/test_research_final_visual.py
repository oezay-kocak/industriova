import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QFont, QFontMetricsF
from PySide6.QtWidgets import QApplication, QTabWidget
from production_zero.core.research import grant_research_points
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView
from production_zero.tools.ui_contact_sheet import _load_qa_fonts


def test_materials_text_fit_centered_lock_and_four_captures(monkeypatch):
    from production_zero.ui import research_specialization
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == "offscreen"
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(1600, 900)
    window.show()
    def settle():
        for _ in range(6):
            app.processEvents()
    settle()
    for timer in window.findChildren(QTimer):
        timer.stop()
    output = Path("artifacts/ui/research-final-refinement")
    output.mkdir(parents=True, exist_ok=True)
    calls = []
    original = research_specialization.draw_lock_warning_frame
    def observed(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)
    monkeypatch.setattr(research_specialization, "draw_lock_warning_frame", observed)
    try:
        grant_research_points(view._state, 20, "Visual QA")
        view._purchase("company.general.s1.major")
        view._purchase("company.general.s1.n1")
        settle()
        assert window.grab().save(str(output / "01-company.png"))
        view.select_tree("industry.agriculture")
        settle()
        view.scroll.verticalScrollBar().setValue(420)
        settle()
        assert window.grab().save(str(output / "02-agriculture.png"))
        assert view.canvas.grab(QRect(35, 520, view.canvas.width() - 70, 420)).save(str(output / "03-major-small.png"))
        slot = next(iter(view.canvas.specialization_buttons.values()))
        assert slot.property("researchState") == "locked"
        assert slot.size().toTuple() == (176, 184)
        assert slot.grab().save(str(output / "04-locked-specialization.png"))
        assert calls and all(call["enabled"] for call in calls)
        title_rect, lock_rect, state_rect = slot.locked_stack_layout()
        assert title_rect.united(state_rect).center().y() == slot.height() / 2
        assert all(rect.center().x() == slot.width() / 2 for rect in (title_rect, lock_rect, state_rect))
        assert title_rect.bottom() < lock_rect.top() < lock_rect.bottom() < state_rect.top()
        for button in view.canvas.buttons.values():
            for text, size, rect, wrap, role in button.text_blocks():
                font = QFont("Bahnschrift")
                font.setPixelSize(size)
                font.setWeight(QFont.Weight.Black if button.major or role in ("muted", "text") else QFont.Weight.Bold)
                flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                if wrap:
                    flags |= Qt.TextFlag.TextWordWrap
                bounds = QFontMetricsF(font).boundingRect(rect, flags, text)
                assert bounds.width() <= rect.width() + 1 and bounds.height() <= rect.height() + 1
        for text, size, rect, wrap in slot.text_blocks():
            font = QFont("Bahnschrift")
            font.setPixelSize(size)
            font.setWeight(QFont.Weight.Black)
            flags = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            if wrap:
                flags |= Qt.TextFlag.TextWordWrap
            bounds = QFontMetricsF(font).boundingRect(rect, flags, text)
            assert bounds.width() <= rect.width() + 1 and bounds.height() <= rect.height() + 1
        assert view.scroll.horizontalScrollBar().maximum() == 0
    finally:
        window.close()
        window.deleteLater()
        settle()
