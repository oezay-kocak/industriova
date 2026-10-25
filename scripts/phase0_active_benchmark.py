"""Existing active-card workload, with the verified Windows font setup."""
from phase0_benchmark import OUT,register_fonts
from PySide6.QtWidgets import QApplication
from release_benchmark import run
app=QApplication([])
register_fonts(app)
run(OUT/'active-card-baseline.json')
