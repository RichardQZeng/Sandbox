import sys

from PyQt5.QtCore import Qt, QItemSelectionModel, QModelIndex, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QPushButton,
    QWidget,
    QTreeView,
    QAbstractItemView,
    QListWidgetItem,
    QTextEdit,
    QListWidget,
    QGroupBox,
    QLineEdit,
    QSlider,
    QLabel
)

from PyQt5.QtGui import *
from bt_widgets import ToolWidgets
from beratools_main import *

bt = BeraTools()


class BTTreeView(QTreeView):
    tool_changed = pyqtSignal(str)  # tool selection changed

    def __init__(self, parent=None):
        super(BTTreeView, self).__init__(parent)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(['Tools'])
        self.setModel(self.tree_model)
        self.setUniformRowHeights(True)

        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setFirstColumnSpanned(0, self.rootIndex(), True)

        first_child = self.add_tool_list_to_tree(bt.toolbox_list, bt.sorted_tools)

        self.tree_sel_model = self.selectionModel()
        index_set = self.tree_model.index(0, 0)
        index_child = self.tree_model.indexFromItem(first_child)
        self.tree_sel_model.select(index_child, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.expand(index_set)
        self.tree_sel_model.selectionChanged.connect(self.tree_view_selection_changed)

        self.collapsed.connect(self.tree_item_collapsed)
        self.expanded.connect(self.tree_item_expanded)

    def add_tool_list_to_tree(self, toolbox_list, sorted_tools):
        first_child = None
        for i, toolbox in enumerate(toolbox_list):
            parent = QStandardItem(QIcon('img/close.gif'), toolbox)
            for j, tool in enumerate(sorted_tools[i]):
                child = QStandardItem(QIcon('img/tool.gif'), tool)
                if i == 0 and j == 0:
                    first_child = child

                parent.appendRow([child])
            self.tree_model.appendRow(parent)

        return first_child

    def tree_view_selection_changed(self, new, old):
        selected = new.indexes()[0]
        item = self.tree_model.itemFromIndex(selected)
        parent = item.parent()
        if not parent:
            return

        toolset = parent.text()
        tool = item.text()
        # self.set_tool(tool)
        self.tool_changed.emit(tool)

    def tree_item_expanded(self, index):
        item = self.tree_model.itemFromIndex(index)
        item.setIcon(QIcon('img/open.gif'))

    def tree_item_collapsed(self, index):
        item = self.tree_model.itemFromIndex(index)
        item.setIcon(QIcon('img/close.gif'))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")

        # Tree view
        self.tree_view = BTTreeView()
        self.tree_view.tool_changed.connect(self.set_tool)

        # group box for tree view
        tree_box = QGroupBox()
        tree_box.setTitle('Tools available')
        tree_layout = QHBoxLayout()
        tree_layout.addWidget(self.tree_view)
        tree_box.setLayout(tree_layout)

        # QListWidget
        list_widget = QListWidget()

        QListWidgetItem("Geeks", list_widget)
        QListWidgetItem("For", list_widget)
        QListWidgetItem("Geeks", list_widget)

        listWidgetItem = QListWidgetItem("GeeksForGeeks")
        list_widget.addItem(listWidgetItem)

        # group box
        tool_search_box = QGroupBox()
        tool_search_layout = QVBoxLayout()
        tool_search = QLineEdit()
        tool_search.setPlaceholderText('Search tool ...')
        tool_search_layout.addWidget(tool_search)
        tool_search_layout.addWidget(list_widget)
        tool_search_box.setTitle('Tool history')
        tool_search_box.setLayout(tool_search_layout)

        # ToolWidgets
        self.tool_widget = ToolWidgets('Raster Line Attributes')

        # Text widget
        text_widget = QTextEdit()

        # buttons
        label = QLabel('Use CPU Cores: ')
        slider = QSlider(Qt.Horizontal)
        slider.setFixedWidth(300)
        button_layout = QHBoxLayout()
        button_run = QPushButton('Run')
        button_cancel = QPushButton('Cancel')
        button_run.setFixedWidth(150)
        button_cancel.setFixedWidth(150)
        button_layout.setAlignment(Qt.AlignRight)

        button_layout.addStretch(1)
        button_layout.addWidget(label)
        button_layout.addWidget(slider)
        button_layout.addWidget(button_run)
        button_layout.addWidget(button_cancel)

        pagelayout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
    
        pagelayout.addLayout(self.left_layout, 3)
        pagelayout.addLayout(self.right_layout, 7)

        self.left_layout.addWidget(tree_box)
        self.left_layout.addWidget(tool_search_box)

        self.right_layout.addWidget(self.tool_widget)
        self.right_layout.addLayout(button_layout)
        self.right_layout.addWidget(text_widget)

        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

    def set_tool(self, tool):
        self.tool_widget = ToolWidgets(tool)
        widget = self.right_layout.itemAt(0).widget()
        self.right_layout.removeWidget(widget)
        self.right_layout.insertWidget(0, self.tool_widget)
        self.right_layout.update()


app = QApplication(sys.argv)

window = MainWindow()
window.setMinimumSize(1024, 768)
window.show()

app.exec()