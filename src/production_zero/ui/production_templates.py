"""Shared industrial template confirmation and input handling."""
from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QDialog, QGridLayout
from production_zero.ui.release_dialogs import IndustrialDialog, inform
from production_zero.ui.game_ui import GameButton, Accent
from production_zero.core.production_templates import quote_templates, PurchaseTemplates


def paste_dialog(view, templates, kind, unit_id, line_id):
    try:
        unit,free,total,plans=quote_templates(view._state,view._definitions,templates,kind,unit_id,line_id)
    except (ValueError,KeyError) as error:
        inform(view,'Paste machines',str(error));return
    problems=[]
    if len(free)<len(templates):problems.append('Not enough free slots.')
    if view._state.cash.amount<total:problems.append('Insufficient cash.')
    names='\n'.join(f'{definition.name} · MK1 Common' for _,definition,_,_ in plans)
    noun='machine' if len(templates)==1 else 'machines'
    d=IndustrialDialog('Paste machines',f'{len(templates)} new {noun}\n{names}\n\nFree slots required: {len(templates)} · Available: {len(free)}\nTotal purchase price: ${total:,.2f}\n'+ '\n'.join(problems),view,accept_text='YES – BUY')
    d.accept_button.setEnabled(not problems)
    if d.exec()==QDialog.DialogCode.Accepted:
        try:
            view._command_bus.dispatch(PurchaseTemplates(templates,kind,unit_id,line_id,view._definitions,total))
        except (ValueError,KeyError) as error:inform(view,'Paste machines',str(error))
        view.refresh_view() if hasattr(view,'refresh_view') else view.refresh()


def line_menu(view, copy, paste, has_template):
    d=IndustrialDialog('Line actions','Copy the installed machines or buy new MK1 machines from a template.',view)
    d.accept_button.hide();grid=QGridLayout()
    for i,(label,callback) in enumerate((('COPY LINE',copy),('PASTE MACHINES',paste))):
        button=GameButton(label,variant='primary');button.setMinimumSize(230,48)
        if i==1:button.setEnabled(has_template)
        def run(callback=callback):d.accept();callback()
        button.clicked.connect(run);grid.addWidget(button,0,i)
    d.layout().itemAt(0).widget().layout().insertLayout(2,grid);d.exec()


class TemplateShortcuts(QObject):
    def __init__(self,view,copy,paste):
        super().__init__(view);self.view=view;self.copy=copy;self.paste=paste
        # Unhandled card/line key events bubble to their board. Text editors
        # keep their native shortcuts, and the application owns no view filters.
        view.installEventFilter(self)

    def eventFilter(self,obj,event):
        if event.type()!=QEvent.Type.KeyPress or not self.view.isVisible():return False
        focus=QApplication.focusWidget()
        if focus is None or not (focus is self.view or self.view.isAncestorOf(focus)):return False
        ancestor=focus
        while ancestor is not None and ancestor is not self.view:
            if isinstance(ancestor,(QLineEdit,QTextEdit,QPlainTextEdit,QAbstractSpinBox)):return False
            ancestor=ancestor.parentWidget()
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() in (Qt.Key.Key_C,Qt.Key.Key_V):
            (self.copy if event.key()==Qt.Key.Key_C else self.paste)();return True
        return False
