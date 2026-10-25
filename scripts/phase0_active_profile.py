"""Profile the existing large active-card fixture without changing that tool."""
import inspect
from phase0_benchmark import OUT,register_fonts,profile
from PySide6.QtWidgets import QApplication
import release_benchmark
app=QApplication([]);register_fonts(app)
original=release_benchmark.measure
def measured(action,repetitions=7):
    closure=inspect.getclosurevars(action).nonlocals
    host=closure.get('host');widgets=closure.get('widgets')
    if host is not None and host.layout().count()==500:profile('active-render500',action)
    if widgets is not None and len(widgets)==500:profile('active-refresh500',action)
    return original(action,repetitions)
release_benchmark.measure=measured
release_benchmark.run(OUT/'active-profile-recheck.json')
