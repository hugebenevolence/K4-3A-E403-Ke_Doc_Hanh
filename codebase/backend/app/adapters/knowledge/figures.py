"""Nhận ra HÌNH trên slide: ảnh chụp, sơ đồ vẽ bằng nét, cùng nhãn chữ bên trong.

Vì sao cần: slide bài giảng AI truyền đạt nhiều ý bằng sơ đồ — vòng tròn lồng
nhau "AI ⊃ ML ⊃ Deep learning ⊃ LLM", vòng lặp của agent, ảnh minh hoạ phân bố
xác suất. Bộ tách chỉ đọc chữ thì bỏ sót cả hình, còn nhãn chữ trong sơ đồ vỡ
thành hàng chục ô tí hon ("LLM GPT · Claude · Kimi", "1 2 3 4") — học viên chọn
vùng thì ra một đống ô vụn, không chọn được "cái sơ đồ".

Hai loại hình, hai cách nhận:
- Ảnh raster: PDF cho sẵn khung, lấy thẳng.
- Sơ đồ vẽ bằng nét vector: phải tự gom. Khó ở chỗ khung nền của ô chữ cũng
  là nét vẽ. Đo trên bộ slide của khoá: khung ô chữ luôn là hình chữ nhật (bo
  góc = đúng 4 đoạn thẳng + 32 đoạn cong, hoặc chữ nhật thường) và CÓ chữ bên
  trong. Bỏ những khung đó và mọi nét nằm lọt trong chúng (icon trong ô), phần
  còn lại gom theo độ gần nhau; cụm đủ lớn là một hình.

Hàm lõi nhận dữ liệu thuần (khung + dòng chữ), không đụng tới PyMuPDF, để test
được mà không cần file slide thật (data pack không commit được).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

Box = tuple[float, float, float, float]

MIN_RASTER_SIDE = 60.0
"""Ảnh nhỏ hơn ngần này điểm là logo/icon, không phải hình minh hoạ."""

MIN_VECTOR_AREA_RATIO = 0.06
"""Cụm nét vẽ chiếm ít hơn ngần này diện tích trang là mũi tên, gạch trang trí."""

CLUSTER_GAP = 18.0
"""Nét vẽ cách nhau trong ngần này điểm thì thuộc cùng một sơ đồ."""

BACKGROUND_RATIO = 0.9
"""Nét vẽ phủ quá ngần này diện tích trang là nền trang."""


@dataclass(frozen=True)
class Shape:
    bbox: Box
    kind: str  # "image" | "rect" (có dáng khung ô) | "path" (mọi nét khác)


@dataclass(frozen=True)
class FigureRegion:
    bbox: Box
    raster: bool
    labels: tuple[int, ...]  # chỉ số các dòng chữ là nhãn của hình


def _area(b: Box) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _center(b: Box) -> tuple[float, float]:
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def _inside(point: tuple[float, float], b: Box) -> bool:
    return b[0] <= point[0] <= b[2] and b[1] <= point[1] <= b[3]


def _contains(outer: Box, inner: Box) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def _near(a: Box, b: Box, gap: float) -> bool:
    return a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and b[1] - gap <= a[3]


def _union(boxes: Sequence[Box]) -> Box:
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def find_figures(
    shapes: Sequence[Shape],
    lines: Sequence[tuple[str, Box]],
    page_size: tuple[float, float],
) -> list[FigureRegion]:
    """Các hình trên một trang, kèm nhãn chữ nằm trong từng hình."""
    page_area = page_size[0] * page_size[1]
    centers = [_center(box) for _, box in lines]

    # Khung ô chữ: có dáng chữ nhật VÀ có chữ bên trong. Khung chữ nhật rỗng thì
    # vẫn có thể là một phần của sơ đồ (ô trống, thanh ngang), nên không bỏ.
    cards = [
        s.bbox
        for s in shapes
        if s.kind == "rect" and _area(s.bbox) < BACKGROUND_RATIO * page_area
        and any(_inside(c, s.bbox) for c in centers)
    ]

    # Ảnh phủ gần kín trang là NỀN, không phải hình — cùng luật với nét vẽ ở
    # dưới. Có bộ slide xuất mỗi trang thành đúng một ảnh (hoặc đặt ảnh nền tràn
    # trang rồi viết chữ lên): coi nó là hình thì mọi dòng chữ trên trang thành
    # "nhãn trong hình", và trang không còn ô chữ nào để chọn giảng. Đo trên 28
    # bộ slide: 91 ảnh phủ ≥ 97% trang, còn ảnh lớn nhất của d1 (timeline, trang
    # 5–9) chỉ phủ 0,66 — ngưỡng này không chạm tới nó.
    rasters = [
        s.bbox
        for s in shapes
        if s.kind == "image"
        and s.bbox[2] - s.bbox[0] >= MIN_RASTER_SIDE
        and s.bbox[3] - s.bbox[1] >= MIN_RASTER_SIDE
        and _area(s.bbox) < BACKGROUND_RATIO * page_area
    ]

    strokes = [
        s.bbox
        for s in shapes
        if s.kind in ("rect", "path")
        and _area(s.bbox) < BACKGROUND_RATIO * page_area
        and s.bbox not in cards
        and not any(_contains(card, s.bbox) for card in cards)
    ]

    # Gom cụm: nét nào gần một nét trong cụm thì vào cụm đó (lặp tới khi ổn định).
    clusters: list[list[Box]] = []
    for box in strokes:
        joined = [c for c in clusters if any(_near(box, other, CLUSTER_GAP) for other in c)]
        merged = [box] + [b for c in joined for b in c]
        clusters = [c for c in clusters if c not in joined] + [merged]

    vectors = [
        bbox
        for c in clusters
        if _area(bbox := _union(c)) >= MIN_VECTOR_AREA_RATIO * page_area
        # Ảnh raster đã là hình rồi; cụm nét đè lên ảnh thường là khung viền ảnh.
        and not any(_near(bbox, r, 0) for r in rasters)
    ]

    regions = []
    for bbox, raster in [*((b, True) for b in rasters), *((b, False) for b in vectors)]:
        # Nhãn của hình: chữ nằm trong khung hình nhưng KHÔNG nằm trong một ô chữ
        # — ô chữ đặt cạnh sơ đồ vẫn là ô chữ riêng, không bị nuốt vào hình.
        labels = tuple(
            i
            for i, center in enumerate(centers)
            if _inside(center, bbox) and not any(_inside(center, card) for card in cards)
        )
        regions.append(FigureRegion(bbox=bbox, raster=raster, labels=labels))
    return regions
