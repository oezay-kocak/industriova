"""Lossless cache of the exact existing Qt SmoothTransformation UI variants.

Writes one additional source asset; never overwrites a resource original. The
existing resources/*.png packaging glob already includes it. No Windows build.
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from production_zero.ui.resource_art import RESOURCE_RASTER_ASSETS,RESOURCE_ASSET_DIR,UI_RASTER_SIZES,UI_RASTER_COLUMNS

ids=tuple(sorted(RESOURCE_RASTER_ASSETS));rows=(len(ids)+UI_RASTER_COLUMNS-1)//UI_RASTER_COLUMNS
atlas=QImage(UI_RASTER_COLUMNS*max(UI_RASTER_SIZES),rows*sum(UI_RASTER_SIZES),QImage.Format.Format_ARGB32)
atlas.fill(Qt.GlobalColor.transparent);destination=atlas.bits();stride=atlas.bytesPerLine();hashes={}
for index,rid in enumerate(ids):
    path=RESOURCE_RASTER_ASSETS[rid];hashes[rid]=hashlib.sha256(path.read_bytes()).hexdigest();original=QImage(str(path))
    offset=0
    for size in UI_RASTER_SIZES:
        scaled=original.scaled(size,size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_ARGB32)
        assert scaled.width()==size and scaled.height()==size
        source=scaled.constBits();source_stride=scaled.bytesPerLine();x=(index%UI_RASTER_COLUMNS)*size;y=offset+(index//UI_RASTER_COLUMNS)*size
        for line in range(size):
            begin=(y+line)*stride+x*4
            destination[begin:begin+size*4]=source[line*source_stride:line*source_stride+size*4]
        offset+=rows*size
del destination
atlas.setText('resource_ids','\n'.join(ids));atlas.setText('raster_sizes',','.join(map(str,UI_RASTER_SIZES)))
atlas.setText('source_sha256',json.dumps(hashes,sort_keys=True));atlas.setText('method','Qt KeepAspectRatio SmoothTransformation; original ARGB32 pixels')
path=RESOURCE_ASSET_DIR/'ui_raster_atlas.png';assert atlas.save(str(path),'PNG')
print(path, path.stat().st_size, 'bytes;',atlas.width()*atlas.height()*4,'decoded bytes')
