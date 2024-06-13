import sys
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
    QToolTip,
    QAction,
    QMainWindow,
    QDockWidget,
    QDialog
)

from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor

from qgis.gui import (
    QgsLayerTreeView,
    QgsMapCanvas,
    QgsMapToolPan,
    QgsMapToolZoom,
    QgsLayerTreeMapCanvasBridge
)

from qgis.core import (
    edit,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsApplication,
    QgsProject,
    QgsLayerTreeModel,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY
)


class MapCanvas(QMainWindow):
    def __init__(self, layers):
        QMainWindow.__init__(self)

        self.setWindowTitle("Map Window")

        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)

        self.canvas.setExtent(layers[0].extent())
        self.canvas.setLayers(layers)

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

        self.project.addMapLayer(self.create_new_layer())

        self.pan()

    def zoom_in(self):
        self.canvas.setMapTool(self.toolZoomIn)

    def zoom_out(self):
        self.canvas.setMapTool(self.toolZoomOut)

    def pan(self):
        self.canvas.setMapTool(self.toolPan)

    def create_new_layer(self):
        vl = QgsVectorLayer("Point", "temp", "memory")

        pr = vl.dataProvider()
        pr.addAttributes([QgsField("name", QVariant.String),
                          QgsField("age", QVariant.Int),
                          QgsField("size", QVariant.Double)])
        vl.updateFields()

        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(10, 10)))
        f.setAttributes(["Ada L.", 2, 0.3])
        pr.addFeature(f)
        vl.updateExtents()
        QgsProject.instance().addMapLayer(vl)

        print("No. fields:", len(pr.fields()))
        print("No. features:", pr.featureCount())
        e = vl.extent()
        print("Extent:", e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum())

        for f in vl.getFeatures():
            print("Feature:", f.id(), f.attributes(), f.geometry().asPoint())

        my_field_name = 'new field'
        my_field_value = 'Hello world!'

        with edit(vl):
            vl.addAttribute(QgsField(my_field_name, QVariant.String))
            vl.updateFields()
            for f in vl.getFeatures():
                f[my_field_name] = my_field_value
                vl.updateFeature(f)

        return vl

    def set_layer_style(self, layer, style=None):
        symbol = layer.renderer().symbol()
        symbol.setWidth(2)
        symbol.setColor(QColor("red"))


app = QApplication(sys.argv)
# qgs = QgsApplication([], True)
# QgsApplication.setPrefixPath("C:\OSGEO4~1\apps\qgis", True)
# QgsApplication.initQgis()

rlayer = QgsRasterLayer(r"I:\BERATools\Surmont_New_AOI\Merged_CHM_2022.tif", "CHM")
vlayer = QgsVectorLayer(
    r"I:\BERATools\Surmont_New_AOI\seed_points_2022_v3.shp",
    "seed points",
    "ogr",
)

window = MapCanvas([vlayer, rlayer])
window.show()

app.exec()
# qgs.exec_()
