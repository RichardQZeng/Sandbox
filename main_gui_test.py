import glob
import platform
import webbrowser
import faulthandler
import re

from PyQt5.QtCore import (Qt, QItemSelectionModel, QModelIndex, pyqtSignal,
                          QProcess, QSortFilterProxyModel, QRegExp, QStringListModel)
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QVBoxLayout, QMainWindow, QPushButton, QWidget, QTreeView,
    QAbstractItemView, QListWidgetItem, QPlainTextEdit, QListView, QGroupBox,
    QLineEdit, QSlider, QLabel, QProgressBar
)

from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon, QTextCursor, QFont

from bt_widgets import *
from bt_data import *

# A regular expression, to extract the % complete.
progress_re = re.compile("Total complete: (\d+)%")

bt = BTData()


def simple_percent_parser(output):
    """
    Matches lines using the progress_re regex,
    returning a single integer for the % progress.
    """
    m = progress_re.search(output)
    if m:
        pc_complete = m.group(1)
        return int(pc_complete)


class SearchProxyModel(QSortFilterProxyModel):

    def setFilterRegExp(self, pattern):
        if isinstance(pattern, str):
            pattern = QRegExp(pattern, Qt.CaseInsensitive, QRegExp.FixedString)
        super(SearchProxyModel, self).setFilterRegExp(pattern)

    def _accept_index(self, idx):
        if idx.isValid():
            text = idx.data(Qt.DisplayRole)
            if self.filterRegExp().indexIn(text) >= 0:
                return True
            for row in range(idx.model().rowCount(idx)):
                if self._accept_index(idx.model().index(row, 0, idx)):
                    return True
        return False

    def filterAcceptsRow(self, sourceRow, sourceParent):
        idx = self.sourceModel().index(sourceRow, 0, sourceParent)
        return self._accept_index(idx)


class BTTreeView(QWidget):
    tool_changed = pyqtSignal(str)  # tool selection changed

    def __init__(self, parent=None):
        super(BTTreeView, self).__init__(parent)

        # controls
        self.tool_search = QLineEdit()
        self.tool_search.setPlaceholderText('Search...')

        self.tags_model = SearchProxyModel()
        self.tree_model = QStandardItemModel()
        self.tags_model.setSourceModel(self.tree_model)
        self.tags_model.setDynamicSortFilter(True)
        self.tags_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.tree_view = QTreeView()
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.AscendingOrder)
        self.tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setRootIsDecorated(True)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setModel(self.tags_model)

        # layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tool_search)
        main_layout.addWidget(self.tree_view)
        self.setLayout(main_layout)

        # signals
        self.tool_search.textChanged.connect(self.search_text_changed)

        # init
        first_child = self.create_model()

        self.tree_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tree_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree_view.setFirstColumnSpanned(0, self.tree_view.rootIndex(), True)
        self.tree_view.setUniformRowHeights(True)

        self.tree_model.setHorizontalHeaderLabels(['Tools'])
        self.tree_sel_model = self.tree_view.selectionModel()
        self.tree_sel_model.selectionChanged.connect(self.tree_view_selection_changed)

        index = None
        # select recent tool
        if bt.recent_tool:
            index = self.get_tool_index(bt.recent_tool)
        else:
            # index_set = self.tree_model.index(0, 0)
            index = self.tree_model.indexFromItem(first_child)

        self.select_tool_by_index(index)
        self.tree_view.collapsed.connect(self.tree_item_collapsed)
        self.tree_view.expanded.connect(self.tree_item_expanded)

    def create_model(self):
        model = self.tree_view.model().sourceModel()
        first_child = self.add_tool_list_to_tree(bt.toolbox_list, bt.sorted_tools)
        self.tree_view.sortByColumn(0, Qt.AscendingOrder)

        return first_child

    def search_text_changed(self, text=None):
        self.tags_model.setFilterRegExp(self.tool_search.text())

        if len(self.tool_search.text()) >= 1 and self.tags_model.rowCount() > 0:
            self.tree_view.expandAll()
        else:
            self.tree_view.collapseAll()

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
        if len(new.indexes()) == 0:
            return

        selected = new.indexes()[0]
        source_index = self.tags_model.mapToSource(selected)
        item = self.tree_model.itemFromIndex(source_index)
        parent = item.parent()
        if not parent:
            return

        toolset = parent.text()
        tool = item.text()
        self.tool_changed.emit(tool)

    def tree_item_expanded(self, index):
        source_index = self.tags_model.mapToSource(index)
        item = self.tree_model.itemFromIndex(source_index)
        if item:
            if item.hasChildren():
                item.setIcon(QIcon('img/open.gif'))

    def tree_item_collapsed(self, index):
        source_index = self.tags_model.mapToSource(index)
        item = self.tree_model.itemFromIndex(source_index)
        if item:
            if item.hasChildren():
                item.setIcon(QIcon('img/close.gif'))

    def get_tool_index(self, tool_name):
        item = self.tree_model.findItems(tool_name, Qt.MatchExactly | Qt.MatchRecursive)
        if len(item) > 0:
            item = item[0]

        index = self.tree_model.indexFromItem(item)
        return index

    def select_tool_by_index(self, index):
        proxy_index = self.tags_model.mapFromSource(index)
        self.tree_sel_model.select(proxy_index, QItemSelectionModel.ClearAndSelect)
        self.tree_view.expand(proxy_index.parent())
        self.tree_sel_model.setCurrentIndex(proxy_index, QItemSelectionModel.Current)

    def select_tool_by_name(self, name):
        index = self.get_tool_index(name)
        self.select_tool_by_index(index)


class BTListView(QListView):
    tool_changed = pyqtSignal(str)

    def __init__(self, data_list=None, parent=None):
        super(BTListView, self).__init__(parent)

        self.slm = QStringListModel()  # model
        if data_list:
            self.slm.setStringList(data_list)

        self.setModel(self.slm)  # set model
        self.setFlow(QListView.TopToBottom)
        self.setBatchSize(5)

        self.clicked.connect(self.clicked_list)
        self.setLayoutMode(QListView.SinglePass)

    def clicked_list(self, model_index):
        self.tool_changed.emit(self.slm.data(model_index, Qt.DisplayRole))

    def set_data_list(self, data_list):
        self.slm.setStringList(data_list)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.title = 'BERA Tools'
        self.setWindowTitle(self.title)
        self.working_dir = bt.get_working_dir()
        self.tool_api = None
        self.tool_name = 'Centerline'
        self.recent_tool = bt.recent_tool
        if self.recent_tool:
            self.tool_name = self.recent_tool
            self.tool_api = bt.get_bera_tool_api(self.tool_name)

        self.update_procs(bt.get_max_cpu_cores())

        # QProcess run tools
        self.process = None

        # BERA tool list
        self.bera_tools = bt.bera_tools
        self.tools_list = bt.tools_list
        self.sorted_tools = bt.sorted_tools
        self.toolbox_list = bt.toolbox_list
        self.upper_toolboxes = bt.upper_toolboxes
        self.lower_toolboxes = bt.lower_toolboxes

        self.exe_path = path.dirname(path.abspath(__file__))
        bt.set_bera_dir(self.exe_path)

        # Tree view
        self.tree_view = BTTreeView()
        self.tree_view.tool_changed.connect(self.set_tool)

        # group box for tree view
        tree_box = QGroupBox()
        tree_box.setTitle('Tools available')
        tree_layout = QVBoxLayout()
        tree_layout.addWidget(self.tree_view)
        tree_box.setLayout(tree_layout)

        # QListWidget
        self.tool_history = BTListView()
        self.tool_history.set_data_list(bt.tool_history)
        self.tool_history.tool_changed.connect(self.set_tool)

        # group box
        tool_history_box = QGroupBox()
        tool_history_layout = QVBoxLayout()
        tool_history_layout.addWidget(self.tool_history)
        tool_history_box.setTitle('Tool history')
        tool_history_box.setLayout(tool_history_layout)

        # left layout
        page_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        self.left_layout.addWidget(tree_box)
        self.left_layout.addWidget(tool_history_box)

        # top buttons
        label = QLabel(f'{self.tool_name}')
        label.setFont(QFont('Consolas', 14))
        self.btn_advanced = QPushButton('Show Advanced Options')
        self.btn_advanced.setFixedWidth(180)
        btn_help = QPushButton('help')
        btn_code = QPushButton('Code')
        btn_help.setFixedWidth(250)
        btn_code.setFixedWidth(100)

        self.btn_layout_top = QHBoxLayout()
        self.btn_layout_top.setAlignment(Qt.AlignRight)
        self.btn_layout_top.addWidget(label)
        self.btn_layout_top.addStretch(1)
        self.btn_layout_top.addWidget(self.btn_advanced)
        self.btn_layout_top.addWidget(btn_code)

        # ToolWidgets
        tool_args = bt.get_bera_tool_args(self.tool_name)
        self.tool_widget = ToolWidgets(self.recent_tool, tool_args, bt.show_advanced)

        # bottom buttons
        label = QLabel('Use CPU Cores: ')
        slider = QSlider(Qt.Horizontal)
        btn_clear_args = QPushButton('Clear Arguments')
        btn_run = QPushButton('Run')
        btn_cancel = QPushButton('Cancel')
        btn_clear_args.setFixedWidth(150)
        slider.setFixedWidth(200)
        btn_run.setFixedWidth(120)
        btn_cancel.setFixedWidth(120)

        btn_layout_bottom = QHBoxLayout()
        btn_layout_bottom.setAlignment(Qt.AlignRight)
        btn_layout_bottom.addStretch(1)
        btn_layout_bottom.addWidget(btn_clear_args)
        btn_layout_bottom.addWidget(label)
        btn_layout_bottom.addWidget(slider)
        btn_layout_bottom.addWidget(btn_run)
        btn_layout_bottom.addWidget(btn_cancel)

        self.top_right_layout = QVBoxLayout()
        self.top_right_layout.addLayout(self.btn_layout_top)
        self.top_right_layout.addWidget(self.tool_widget)
        self.top_right_layout.addLayout(btn_layout_bottom)
        tool_widget_grp = QGroupBox('Tool')
        tool_widget_grp.setLayout(self.top_right_layout)

        # Text widget
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont('Consolas', 9))
        self.text_edit.setReadOnly(True)

        # progress bar
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar(self)
        self.progress_var = 0

        # progress layout
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)

        self.right_layout.addWidget(tool_widget_grp)
        self.right_layout.addWidget(self.text_edit)
        self.right_layout.addLayout(progress_layout)

        # main layouts
        page_layout.addLayout(self.left_layout, 3)
        page_layout.addLayout(self.right_layout, 7)

        # signals and slots
        self.btn_advanced.clicked.connect(self.show_advanced)
        btn_help.clicked.connect(self.show_help)
        btn_code.clicked.connect(self.view_code)
        btn_clear_args.clicked.connect(self.clear_args)
        btn_run.clicked.connect(self.start_process)
        btn_cancel.clicked.connect(self.stop_process)

        widget = QWidget(self)
        widget.setLayout(page_layout)
        self.setCentralWidget(widget)

    def set_tool(self, tool=None):
        if tool:
            self.tool_name = tool

        # tree view select tool
        # TODO use signal
        self.tree_view.select_tool_by_name(self.tool_name)

        self.tool_api = bt.get_bera_tool_api(self.tool_name)
        tool_args = bt.get_bera_tool_args(self.tool_name)

        # update tool label
        self.btn_layout_top.itemAt(0).widget().setText(self.tool_name)

        # update tool widget
        self.tool_widget = ToolWidgets(self.tool_name, tool_args, bt.show_advanced)
        widget = self.top_right_layout.itemAt(1).widget()
        self.top_right_layout.removeWidget(widget)
        self.top_right_layout.insertWidget(1, self.tool_widget)
        self.top_right_layout.update()

    def save_tool_parameter(self):
        # Retrieve tool parameters from GUI
        args = self.tool_widget.get_widgets_arguments()
        bt.load_saved_tool_info()
        bt.add_tool_history(self.tool_api, args)
        bt.save_tool_info()

        # update tool history list
        # TODO use signal
        bt.get_tool_history()
        self.tool_history.set_data_list(bt.tool_history)

    def get_current_tool_parameters(self):
        self.tool_api = bt.get_bera_tool_api(self.tool_name)
        return bt.get_bera_tool_params(self.tool_name)

    def get_current_tool_args(self):
        return bt.get_bera_tool_args(self.tool_name)

    def show_help(self):
        # open the user manual section for the current tool
        webbrowser.open_new_tab(self.get_current_tool_parameters()['tech_link'])

    def about(self):
        self.text_edit.clear()
        self.print_to_output(bt.about())

    def license(self):
        self.text_edit.clear()
        self.print_to_output(bt.license())

    def update_procs(self, value):
        max_procs = int(value)
        bt.set_max_procs(max_procs)

    def reset_tool(self):
        for widget in self.arg_scroll_frame.winfo_children():
            args = bt.get_bera_tool_params(self.tool_name)
            for param in args['parameters']:
                default_value = param['default_value']
                if widget.flag == param['flag']:
                    if type(widget) is OptionsInput:
                        widget.value = default_value
                    else:
                        widget.value.set(default_value)

    def print_to_output(self, text):
        self.text_edit.moveCursor(QTextCursor.End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(QTextCursor.End)

    def print_line_to_output(self, text, tag=None):
        self.text_edit.moveCursor(QTextCursor.End)
        self.text_edit.insertPlainText(text+'\n')
        self.text_edit.moveCursor(QTextCursor.End)

    def cancel_operation(self):
        bt.cancel_op = True
        self.print_line_to_output('------------------------------------')
        self.print_line_to_output("Tool operation cancelling...")
        self.progress_bar.update_idletasks()

    def show_advanced(self):
        if bt.show_advanced:
            bt.show_advanced = False
            self.btn_advanced.setText("Show Advanced Options")
        else:
            bt.show_advanced = True
            self.btn_advanced.setText("Hide Advanced Options")

        self.set_tool()

    def view_code(self):
        webbrowser.open_new_tab(self.get_current_tool_parameters()['tech_link'])

    def custom_callback(self, value):
        """
        A custom callback for dealing with tool output.
        """
        value = str(value)
        value.strip()
        if value != '':
            # remove esc string which origin is unknown
            rm_str = '\x1b[0m'
            if rm_str in value:
                value = value.replace(rm_str, '')

        if "%" in value:
            try:
                str_progress = extract_string_from_printout(value, '%')
                value = value.replace(str_progress, '').strip()  # remove progress string
                progress = float(str_progress.replace("%", "").strip())
                self.progress_bar.setValue(int(progress))
            except ValueError as e:
                print("custom_callback: Problem converting parsed data into number: ", e)
            except Exception as e:
                print(e)
        elif 'PROGRESS_LABEL' in value:
            str_label = extract_string_from_printout(value, 'PROGRESS_LABEL')
            value = value.replace(str_label, '').strip()  # remove progress string
            value = value.replace('"', '')
            str_label = str_label.replace("PROGRESS_LABEL", "").strip()
            self.progress_label.setText(str_label)

        if value != '':
            self.print_line_to_output(value)

        self.update()  # this is needed for cancelling and updating the progress bar

    def message(self, s):
        self.text_edit.appendPlainText(s)

    def clear_args(self):
        self.tool_widget.clear_args()

    def start_process(self):
        bt.set_working_dir(self.working_dir)

        args = self.tool_widget.get_widgets_arguments()
        if not args:
            print('Please check the parameters.')
            return

        self.print_line_to_output("")
        self.print_line_to_output(f'Staring tool {self.tool_name} ... \n')
        self.print_line_to_output(bt.ascii_art)
        self.print_line_to_output("Tool arguments:")
        self.print_line_to_output(json.dumps(args, indent=4))
        self.print_line_to_output("")

        bt.recent_tool = self.tool_name
        self.save_tool_parameter()

        # Run the tool and check the return value for an error
        for key in args.keys():
            if type(args[key]) is not str:
                args[key] = str(args[key])

        # disable button
        # self.run_button.config(text='Running', state='disabled')
        tool_type, tool_args = bt.run_tool(self.tool_api, args, self.custom_callback)

        if self.process is None:  # No process running.
            self.message("Executing process")
            self.process = QProcess()  # Keep a reference to the QProcess (e.g. on self) while it's running.
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.readyReadStandardError.connect(self.handle_stderr)
            self.process.stateChanged.connect(self.handle_state)
            self.process.finished.connect(self.process_finished)  # Clean up once complete.
            self.process.start(tool_type, tool_args)

        while self.process is not None:
            sys.stdout.flush()
            if bt.cancel_op:
                bt.cancel_op = False
                self.process.terminate()

            else:
                break

    def stop_process(self):
        bt.cancel_op = True
        if self.process:
            self.process.kill()

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        # Extract progress if it is in the data.
        progress = simple_percent_parser(stderr)
        if progress:
            self.progress_bar.setValue(progress)
        self.message(stderr)

    def handle_stdout(self):
        # data = self.p.readAllStandardOutput()
        line = self.process.readLine()
        line = bytes(line).decode("utf8")

        # process line output
        sys.stdout.flush()
        self.custom_callback(line)

        # self.message(line)

    def handle_state(self, state):
        states = {
            QProcess.NotRunning: 'Not running',
            QProcess.Starting: 'Starting',
            QProcess.Running: 'Running',
        }
        state_name = states[state]
        self.message(f"State changed: {state_name}")

    def process_finished(self):
        self.message("Process finished.")
        self.process = None
        self.progress_bar.setValue(0)
        self.progress_label.setText("")


# start @ the beginning
faulthandler.enable()

app = QApplication(sys.argv)

window = MainWindow()
window.setMinimumSize(1024, 768)
window.show()

app.exec()
