import numpy as np
import pyqtgraph as pg
from .config import PHASES

COLORS = ("#6BA3F2", "#62D9BE", "#E6B85A", "#B899F1")

def plot_widget(title="Normalized lip opening"):
    plot = pg.PlotWidget(title=title)
    plot.setBackground("#101C29")
    plot.showGrid(x=True, y=True, alpha=.15)
    plot.setLabel("left", "Normalized lip opening", units="ratio")
    plot.getAxis("left").enableAutoSIPrefix(False)
    plot.setLabel("bottom", "Source time", units="s")
    return plot


def plot_data(rows):
    return ([r["source_t"] for r in rows],
            [r["opening"] if r["valid"] and r.get("opening") is not None else np.nan for r in rows])


def show_session(plot, rows):
    plot.clear()
    x, y = plot_data(rows)
    plot.plot(x, y, pen=pg.mkPen("#62D9BE", width=2), connect="finite", name="Filtered opening")
    for phase, color in zip(PHASES, COLORS):
        subset = [r["source_t"] for r in rows if r["phase"] == phase]
        if subset:
            region = pg.LinearRegionItem((min(subset), max(subset)), movable=False,
                                         brush=pg.mkBrush(color + "18"), pen=pg.mkPen(None))
            region.setZValue(-10)
            plot.addItem(region)
    return x, y
