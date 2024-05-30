import sys

from PyQt5.QtCore import Qt, QItemSelectionModel, QModelIndex
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
    def __init__(self, parent=None):
        super(BTTreeView, self).__init__(parent)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(['Tools'])
        self.setModel(self.tree_model)
        self.setUniformRowHeights(True)




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")

        # Tree view
        self.tree_view = BTTreeView()

        parent = None
        child = None
        first_child = None
        for i in range(3):
            parent = QStandardItem(QIcon('img/close.gif'), f'Toolset description {i}')
            for j in range(3):
                child = QStandardItem(QIcon('img/tool.gif'), 'Tool name {}'.format(i*3+j))
                if i == 0 and j == 0:
                    first_child = child

                parent.appendRow([child])
            self.tree_view.tree_model.appendRow(parent)

        # expand third container
        self.tree_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree_view.setFirstColumnSpanned(0, self.tree_view.rootIndex(), True)
        self.tree_view.collapsed.connect(self.tree_item_collapsed)
        self.tree_view.expanded.connect(self.tree_item_expanded)

        self.tree_sel_model = self.tree_view.selectionModel()
        index_set = self.tree_view.tree_model.index(0, 0)
        index_child = self.tree_view.tree_model.indexFromItem(first_child)
        self.tree_sel_model.select(index_child, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.tree_view.expand(index_set)
        self.tree_sel_model.selectionChanged.connect(self.tree_view_selection_changed)

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
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
    
        pagelayout.addLayout(left_layout, 3)
        pagelayout.addLayout(right_layout, 7)

        left_layout.addWidget(tree_box)
        left_layout.addWidget(tool_search_box)

        right_layout.addWidget(self.tool_widget)
        right_layout.addLayout(button_layout)
        right_layout.addWidget(text_widget)

        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

    def set_tool(self, tool):
        self.tool_widget = ToolWidgets(tool)

    def tree_view_selection_changed(self, new, old):
        selected = new.indexes()[0]
        item = self.tree_view.tree_model.itemFromIndex(selected)
        parent = item.parent()
        if not parent:
            return

        toolset = parent.text()
        tool = item.text()
        self.set_tool(tool)

    def tree_item_expanded(self, index):
        item = self.tree_view.tree_model.itemFromIndex(index)
        item.setIcon(QIcon('img/open.gif'))

    def tree_item_collapsed(self, index):
        item = self.tree_view.tree_model.itemFromIndex(index)
        item.setIcon(QIcon('img/close.gif'))


app = QApplication(sys.argv)

window = MainWindow()
window.setMinimumSize(1024, 768)
window.show()

app.exec()