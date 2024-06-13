from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QPushButton,
    QWidget,
    QTreeView,
    QAbstractItemView,
    QPlainTextEdit,
    QListView,
    QGroupBox,
    QLineEdit,
    QSlider,
    QLabel,
    QProgressBar,
    QToolTip
)

from qgis.gui import (
    QgsLayerTreeView,
    QgsMapCanvas,
    QgsMapToolPan,
    QgsMapToolZoom,
    QgsLayerTreeMapCanvasBridge
)

from qgis.PyQt.QtWidgets import(
    QAction,
    QMainWindow,
    QDockWidget
)

from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsRasterLayer,
    QgsVectorLayer,
    QgsApplication,
    QgsProject,
    QgsLayerTreeModel,

)

import sys
from PyQt5.QtWidgets import QApplication

rlayer = QgsRasterLayer(r"I:\BERATools\Surmont_New_AOI\Merged_CHM_2022.tif", "CHM")
vlayer = QgsVectorLayer(
    r"I:\BERATools\Surmont_New_AOI\seed_points_2022_v3.shp",
    "seed points",
    "ogr",
)


class MyWnd(QMainWindow):
    def __init__(self, layer):
        QMainWindow.__init__(self)

        self.setWindowTitle("Map Window")

        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)

        self.canvas.setExtent(layer.extent())
        self.canvas.setLayers([layer, rlayer])

        self.setCentralWidget(self.canvas)

        self.actionZoomIn = QAction("Zoom in", self)
        self.actionZoomOut = QAction("Zoom out", self)
        self.actionPan = QAction("Pan", self)

        self.actionZoomIn.setIcon(QgsApplication.getThemeIcon("mActionZoomIn.svg"))
        self.actionZoomOut.setIcon(QgsApplication.getThemeIcon("mActionZoomOut.svg"))
        self.actionPan.setIcon(QgsApplication.getThemeIcon("mActionPan.svg"))

        self.actionZoomIn.setCheckable(True)
        self.actionZoomOut.setCheckable(True)
        self.actionPan.setCheckable(True)

        self.actionZoomIn.triggered.connect(self.zoom_in)
        self.actionZoomOut.triggered.connect(self.zoom_out)
        self.actionPan.triggered.connect(self.pan)

        self.toolbar = self.addToolBar("Canvas actions")
        self.toolbar.addAction(self.actionZoomIn)
        self.toolbar.addAction(self.actionZoomOut)
        self.toolbar.addAction(self.actionPan)

        # create the map tools
        self.toolPan = QgsMapToolPan(self.canvas)
        self.toolPan.setAction(self.actionPan)
        self.toolZoomIn = QgsMapToolZoom(self.canvas, False)  # false = in
        self.toolZoomIn.setAction(self.actionZoomIn)
        self.toolZoomOut = QgsMapToolZoom(self.canvas, True)  # true = out
        self.toolZoomOut.setAction(self.actionZoomOut)

        # add widgets
        self.project = QgsProject.instance()
        self.project.addMapLayer(rlayer)
        self.project.addMapLayer(vlayer)
        self.project_rt = self.project.layerTreeRoot()

        self.bridge = QgsLayerTreeMapCanvasBridge(
            self.project_rt, self.canvas
        )
        self.bridge.setAutoSetupOnFirstLayer(False)

        self.model = QgsLayerTreeModel(self.project_rt)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeReorder)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility)

        dock = QDockWidget("Layers", self)
        self.view = QgsLayerTreeView(dock)
        self.view.setModel(self.model)

        dock.setWidget(self.view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        dock.update()

        self.pan()

    def zoom_in(self):
        self.canvas.setMapTool(self.toolZoomIn)

    def zoom_out(self):
        self.canvas.setMapTool(self.toolZoomOut)

    def pan(self):
        self.canvas.setMapTool(self.toolPan)


app = QApplication(sys.argv)
# qgs = QgsApplication([], True)
# QgsApplication.setPrefixPath("C:\OSGEO4~1\apps\qgis", True)
# QgsApplication.initQgis()

window = MyWnd(vlayer)
window.show()

app.exec()
# qgs.exec_()
