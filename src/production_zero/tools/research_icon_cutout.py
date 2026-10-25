"""Deterministic exterior-only alpha mask; never changes source RGB pixels."""
from collections import deque
import argparse
import hashlib
import json
from pathlib import Path
from PySide6.QtGui import QImage, QPainter, QColor


def cutout(source, destination, qa_directory):
    original = QImage(str(source)).convertToFormat(QImage.Format.Format_RGBA8888)
    if original.isNull():
        raise ValueError(f"Cannot read {source}")
    width, height = original.width(), original.height()
    pixels = bytes(original.constBits())
    count = width * height
    # The original background is a light, near-neutral checkerboard. Only
    # border-connected pixels are removed; enclosed steel highlights survive.
    eligible = bytearray(count)
    for index in range(count):
        r, g, b = pixels[index * 4:index * 4 + 3]
        eligible[index] = min(r, g, b) >= 170 and max(r, g, b) - min(r, g, b) <= 25
    exterior = bytearray(count)
    queue = deque()
    def add(index):
        if eligible[index] and not exterior[index]:
            exterior[index] = 1
            queue.append(index)
    for x in range(width):
        add(x)
        add((height - 1) * width + x)
    for y in range(height):
        add(y * width)
        add(y * width + width - 1)
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        if x:
            add(index - 1)
        if x + 1 < width:
            add(index + 1)
        if y:
            add(index - width)
        if y + 1 < height:
            add(index + width)
    result = original.copy()
    data = result.bits()
    for index, remove in enumerate(exterior):
        if remove:
            data[index * 4 + 3] = 0
    assert 0 < sum(exterior) < count
    assert all(result.pixelColor(x, y).alpha() == 0
               for x, y in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)))
    assert result.pixelColor(width // 2, height // 2).alpha() == 255
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert result.save(str(destination))
    reread = QImage(str(destination)).convertToFormat(QImage.Format.Format_RGBA8888)
    actual = bytes(reread.constBits())
    assert reread.size() == original.size()
    assert destination.read_bytes()[25] == 6  # PNG IHDR color type: RGBA.
    assert all(actual[offset:offset + 3] == pixels[offset:offset + 3] for offset in range(0, len(pixels), 4))
    qa_directory.mkdir(parents=True, exist_ok=True)
    for name, color in (("dark", "#14171a"), ("light", "#f5f3ee")):
        preview = QImage(width, height, QImage.Format.Format_RGB32)
        preview.fill(QColor(color))
        painter = QPainter(preview)
        painter.drawImage(0, 0, result)
        painter.end()
        assert preview.save(str(qa_directory / f"cutout-on-{name}.png"))
    report = dict(source=str(source), asset=str(destination), width=width, height=height,
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  transparent_pixels=sum(exterior), opaque_pixels=count - sum(exterior),
                  changed_rgb_pixels=0, resampled=False, png_color_type="RGBA",
                  corner_alpha=[0, 0, 0, 0], center_alpha=255,
                  mask="border-connected near-neutral RGB >=170, spread <=25")
    (qa_directory / "alpha-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    cutout(args.source, root / "src/production_zero/assets/ui/research_generic.png",
           root / "artifacts/ui/research-generic-icon")
