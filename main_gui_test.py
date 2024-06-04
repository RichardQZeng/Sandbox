import threading
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

from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon

from bt_widgets import *
from beratools_main import *

# A regular expression, to extract the % complete.
progress_re = re.compile("Total complete: (\d+)%")

bt = BeraTools()


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
        self.tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.tree_model.setHorizontalHeaderLabels(['Tools'])
        self.tree_view.setUniformRowHeights(True)

        self.tree_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree_view.setFirstColumnSpanned(0, self.tree_view.rootIndex(), True)

        self.tree_sel_model = self.tree_view.selectionModel()
        self.tree_sel_model.selectionChanged.connect(self.tree_view_selection_changed)

        index = None
        if bt.recent_tool:
            # select recent tool
            index = self.select_tool(bt.recent_tool)
        else:
            # index_set = self.tree_model.index(0, 0)
            index = self.tree_model.indexFromItem(first_child)

        proxy_index = self.tags_model.mapFromSource(index)
        self.tree_sel_model.select(proxy_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.tree_view.expand(proxy_index.parent())
        self.tree_sel_model.setCurrentIndex(proxy_index, QItemSelectionModel.Current)

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
            item.setIcon(QIcon('img/open.gif'))

    def tree_item_collapsed(self, index):
        source_index = self.tags_model.mapToSource(index)
        item = self.tree_model.itemFromIndex(source_index)
        if item:
            item.setIcon(QIcon('img/close.gif'))

    def select_tool(self, tool_name):
        item = self.tree_model.findItems(tool_name, Qt.MatchExactly | Qt.MatchRecursive)
        if len(item) > 0:
            item = item[0]

        index = self.tree_model.indexFromItem(item)
        # self.tree_sel_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        # self.tree_view.expand(index.parent())

        return index


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

        max_cores = bt.get_max_cpu_cores()
        if bt.get_max_procs() <= 0:
            bt.set_max_procs(max_cores)

        # QProcess run tools
        self.p = None

        # BERA tool list
        if platform.system() == 'Windows':
            self.ext = '.exe'
        else:
            self.ext = ''

        exe_name = "BERA_tools{}".format(self.ext)
        self.bera_tools = bt.bera_tools
        self.tools_list = bt.tools_list
        self.sorted_tools = bt.sorted_tools
        self.toolbox_list = bt.toolbox_list
        self.upper_toolboxes = bt.upper_toolboxes
        self.lower_toolboxes = bt.lower_toolboxes

        self.exe_path = path.dirname(path.abspath(__file__))
        os.chdir(self.exe_path)
        for filename in glob.iglob('**/*', recursive=True):
            if filename.endswith(exe_name):
                self.exe_path = path.dirname(path.abspath(filename))
                break

        bt.set_bera_dir(self.exe_path)

        # Tree view
        self.tree_view = BTTreeView()
        self.tree_view.tool_changed.connect(self.set_tool)
        # self.tree_view.tree_sel_model.selectionChanged.connect(self.set_tool)

        # group box for tree view
        tree_box = QGroupBox()
        tree_box.setTitle('Tools available')
        tree_layout = QVBoxLayout()
        tree_layout.addWidget(self.tree_view)
        tree_box.setLayout(tree_layout)

        # QListWidget
        tool_history = BTListView()
        tool_history.set_data_list(['Centerline'])
        tool_history.tool_changed.connect(self.set_tool)

        # group box
        tool_history_box = QGroupBox()
        tool_history_layout = QVBoxLayout()
        tool_history_layout.addWidget(tool_history)
        tool_history_box.setTitle('Tool history')
        tool_history_box.setLayout(tool_history_layout)

        # ToolWidgets
        tool_args = bt.get_bera_tool_args(self.tool_name)
        self.tool_widget = ToolWidgets(self.recent_tool, tool_args)

        # Text widget
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)

        # progress bar
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar(self)
        self.progress_var = 0

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

        # progress layout
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)

        page_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
    
        page_layout.addLayout(self.left_layout, 3)
        page_layout.addLayout(self.right_layout, 7)

        self.left_layout.addWidget(tree_box)
        self.left_layout.addWidget(tool_history_box)

        self.right_layout.addWidget(self.tool_widget)
        self.right_layout.addLayout(button_layout)
        self.right_layout.addWidget(self.text_edit)
        self.right_layout.addLayout(progress_layout)

        # signals and slots
        # self.button_run.clicked.connect(self.start_run_tool_thread)
        button_run.clicked.connect(self.start_process)
        button_cancel.clicked.connect(self.stop_process)

        widget = QWidget(self)
        widget.setLayout(page_layout)
        self.setCentralWidget(widget)

    def set_tool(self, tool=None):
        if tool:
            self.tool_name = tool

        self.tool_api = bt.get_bera_tool_api(self.tool_name)
        tool_args = bt.get_bera_tool_args(self.tool_name)
        self.tool_widget = ToolWidgets(self.tool_name, tool_args)
        widget = self.right_layout.itemAt(0).widget()
        self.right_layout.removeWidget(widget)
        self.right_layout.insertWidget(0, self.tool_widget)
        self.right_layout.update()

    def update_selected_bera_tool(self):
        selected_item = -1
        for toolbox in self.bera_tools['toolbox']:
            for item in toolbox['tools']:
                if item['name']:
                    if item == self.tool_name:  # update selected_item it tool found
                        selected_item = len(self.tools_list) - 1

        if selected_item == -1:  # set self.tool_name as default tool
            selected_item = 0
            self.tool_name = self.tools_list[0]

    def save_tool_parameter(self):
        data_path = bt.get_data_folder()
        json_file = Path(data_path).joinpath('saved_tool_parameters.json')

        # Retrieve tool parameters from GUI
        args = self.tool_widget.get_widgets_arguments()

        tool_params = {}
        if json_file.exists():
            with open(json_file, 'r') as open_file:
                data = json.load(open_file)
                if data:
                    tool_params = data

        with open(json_file, 'w') as new_file:
            tool_params[self.tool_api] = args
            json.dump(tool_params, new_file, indent=4)

    def get_current_tool_parameters(self):
        self.tool_api = bt.get_bera_tool_api(self.tool_name)
        return bt.get_bera_tool_parameters(self.tool_name)

    def get_current_tool_args(self):
        return bt.get_bera_tool_args(self.tool_name)

    def update_search_tool_info(self, event):
        """
        read selection when tool selected from search results then call self.update_tool_help
        """
        selection = self.search_results_listbox.curselection()
        self.tool_name = self.search_results_listbox.get(selection[0])

        self.set_tool()
        if self.search_tool_selected:
            print("Index {} selected".format(self.search_tool_selected[0]))

    def update_toolbox_icon(self, event):
        cur_item = self.tool_tree.focus()
        dict_tool = self.tool_tree.item(cur_item)  # retrieve the toolbox name
        self.toolbox_name = dict_tool.get('text').replace("  ", "")  # delete the space between the icon and text
        self.toolbox_open = dict_tool.get('open')  # retrieve whether the toolbox is open or not
        if self.toolbox_open:  # set image accordingly
            self.tool_tree.item(self.toolbox_name, image=self.open_toolbox_icon)
        else:
            self.tool_tree.item(self.toolbox_name, image=self.closed_toolbox_icon)

    def update_search(self, event):
        self.search_list = []
        self.search_string = self.search_text.get().lower()
        self.search_results_listbox.delete(0, 'end')  # empty the search results
        num_results = 0
        for tool in self.tools_list:  # search tool names
            tool_lower = tool.lower()
            # search string found within tool name
            if tool_lower.find(self.search_string) != (-1):
                num_results = num_results + 1
                # tool added to listbox and to search results string
                self.search_results_listbox.insert(num_results, tool)
                self.search_list.append(tool)
        index = 0

        # update label to show tools found
        self.search_frame.config(text="{} Tools Found".format(len(self.search_list)))

    def tool_help_button(self):
        # open the user manual section for the current tool
        webbrowser.open_new_tab(self.get_current_tool_parameters()['tech_link'])

    def add_tools_to_treeview(self):
        # Add toolboxes and tools to treeview
        index = 0
        for toolbox in self.lower_toolboxes:
            if toolbox.find('/') != (-1):  # toolboxes
                self.tool_tree.insert(toolbox[:toolbox.find('/')], 0, text="  " + toolbox[toolbox.find('/') + 1:],
                                      iid=toolbox[toolbox.find('/') + 1:], tags='toolbox',
                                      image=self.closed_toolbox_icon)
                for tool in self.sorted_tools[index]:  # add tools within toolbox
                    self.tool_tree.insert(toolbox[toolbox.find('/') + 1:], 'end', text="  " + tool,
                                          tags='tool', iid=tool, image=self.tool_icon)
            else:  # sub toolboxes
                self.tool_tree.insert('', 'end', text="  " + toolbox, iid=toolbox, tags='toolbox',
                                      image=self.closed_toolbox_icon)
                for tool in self.sorted_tools[index]:  # add tools within sub toolbox
                    self.tool_tree.insert(toolbox, 'end', text="  " + tool, iid=tool, tags='tool', image=self.tool_icon)
            index = index + 1

    def add_recent_tool_to_search(self):
        if bt.recent_tool:
            self.search_results_listbox.delete(0, 'end')
            self.search_list.append(bt.recent_tool)
            self.search_results_listbox.insert(END, bt.recent_tool)

            self.search_frame.config(text='Recent used tool')
            self.tool_name = self.search_results_listbox.get(0)

    #########################################################
    #               Functions (original)
    def about(self):
        self.out_text.delete('1.0', tk.END)
        self.print_to_output(bt.about())

    def license(self):
        self.out_text.delete('1.0', tk.END)
        self.print_to_output(bt.license())

    def set_directory(self):
        try:
            self.working_dir = filedialog.askdirectory(initialdir=self.working_dir)
            bt.set_working_dir(self.working_dir)
        except:
            messagebox.showinfo("Warning", "Could not set the working directory.")

    def set_procs(self):
        try:
            max_cpu_cores = bt.get_max_cpu_cores()
            max_procs = askinteger(
                title="Max CPU cores used",
                prompt="Set the number of processors to be used (maximum: {}, -1: all):".format(max_cpu_cores),
                parent=self, initialvalue=bt.get_max_procs(), minvalue=-1, maxvalue=max_cpu_cores)
            if max_procs:
                self.update_procs(max_procs)
                self.mpc_scale.set(max_procs)
        except:
            messagebox.showinfo("Warning", "Could not set the number of processors.")

    def update_procs(self, value):
        self.__max_procs = int(value)
        bt.set_max_procs(self.__max_procs)

    def reset_tool(self):
        for widget in self.arg_scroll_frame.winfo_children():
            args = bt.get_bera_tool_parameters(self.tool_name)
            for param in args['parameters']:
                default_value = param['default_value']
                if widget.flag == param['flag']:
                    if type(widget) is OptionsInput:
                        widget.value = default_value
                    else:
                        widget.value.set(default_value)

    def start_run_tool_thread(self):
        t = threading.Thread(target=self.run_tool, args=())
        t.daemon = True
        t.start()

    def run_tool(self):
        bt.set_working_dir(self.working_dir)

        args = self.tool_widget.get_widgets_arguments()
        if not args:
            print('Please check the parameters.')
            return

        self.print_line_to_output("")
        self.print_line_to_output(f'Staring tool {self.tool_name} ...')
        self.print_line_to_output(bt.ascii_art)
        self.print_line_to_output("Tool arguments:")
        self.print_line_to_output(json.dumps(args, indent=4))
        self.print_line_to_output("")
        self.save_tool_parameter()
        bt.recent_tool = self.tool_name
        bt.save_recent_tool()

        # Run the tool and check the return value for an error
        for key in args.keys():
            if type(args[key]) is not str:
                args[key] = str(args[key])

        # disable button
        # self.run_button.config(text='Running', state='disabled')
        if bt.run_tool_bt(self.tool_api, args, self.custom_callback) == 1:
            print("Error running {}".format(self.tool_name))
            # restore Run button
            # self.run_button.config(text='Run', state='enable')
        else:
            self.progress_var = 0
            self.progress_label.setText('Progress:')
            self.progress_bar.update()
            # restore Run button
            # self.run_button.config(text='Run', state='enable')

        return

    def print_to_output(self, text):
        self.text_edit.moveCursor(QTextCursor.End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(QTextCursor.End)

    def print_line_to_output(self, text, tag=None):
        self.text_edit.moveCursor(QTextCursor.End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(QTextCursor.End)

    def cancel_operation(self):
        bt.cancel_op = True
        self.print_line_to_output('------------------------------------')
        self.print_line_to_output("Tool operation cancelling...")
        self.progress_bar.update_idletasks()

    def show_advanced(self):
        if not self.show_advanced_button or len(self.arg_scroll_frame.winfo_children()) <= 0:
            return

        if bt.show_advanced:
            bt.show_advanced = False
        else:
            bt.show_advanced = True

        if bt.show_advanced:
            self.show_advanced_button.config(text="Hide Advanced Options")
            self.save_tool_parameter()
            self.set_tool()
        else:
            self.show_advanced_button.config(text="Show Advanced Options")
            for widget in self.arg_scroll_frame.winfo_children():
                if widget.optional:
                    widget.grid_forget()

    def view_code(self):
        webbrowser.open_new_tab(self.get_current_tool_parameters()['tech_link'])

    def update_args_box(self):
        s = ""
        self.current_tool_lbl['text'] = "Current Tool: {}".format(
            self.tool_name)

        # self.spacer['width'] = width=(35-len(self.tool_name))
        # for item in bt.tool_help(self.tool_name).splitlines():
        for item in bt.get_bera_tool_info(self.tool_name).splitlines():
            if item.startswith("-"):
                k = item.split(" ")
                if "--" in k[1]:
                    value = k[1].replace(",", "")
                else:
                    value = k[0].replace(",", "")

                if "flag" in item.lower():
                    s = s + value + " "
                else:
                    if "file" in item.lower():
                        s = s + value + "='{}' "
                    else:
                        s = s + value + "={} "

        # self.args_value.set(s.strip())

    def custom_callback(self, value):
        """
        A custom callback for dealing with tool output.
        """
        value = str(value)

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

    def select_all(self, event):
        self.out_text.tag_add(tk.SEL, "1.0", tk.END)
        self.out_text.mark_set(tk.INSERT, "1.0")
        self.out_text.see(tk.INSERT)
        return 'break'

    def message(self, s):
        self.text_edit.appendPlainText(s)

    def start_process(self):
        # self.run_tool()
        # return

        bt.set_working_dir(self.working_dir)

        args = self.tool_widget.get_widgets_arguments()
        if not args:
            print('Please check the parameters.')
            return

        self.print_line_to_output("")
        self.print_line_to_output(f'Staring tool {self.tool_name} ...')
        self.print_line_to_output(bt.ascii_art)
        self.print_line_to_output("Tool arguments:")
        self.print_line_to_output(json.dumps(args, indent=4))
        self.print_line_to_output("")
        self.save_tool_parameter()
        bt.recent_tool = self.tool_name
        bt.save_recent_tool()

        # Run the tool and check the return value for an error
        for key in args.keys():
            if type(args[key]) is not str:
                args[key] = str(args[key])

        # disable button
        # self.run_button.config(text='Running', state='disabled')
        tool_type, tool_args = bt.run_tool_bt_qt(self.tool_api, args, self.custom_callback)

        if self.p is None:  # No process running.
            self.message("Executing process")
            self.p = QProcess()  # Keep a reference to the QProcess (e.g. on self) while it's running.
            self.p.readyReadStandardOutput.connect(self.handle_stdout)
            self.p.readyReadStandardError.connect(self.handle_stderr)
            self.p.stateChanged.connect(self.handle_state)
            self.p.finished.connect(self.process_finished)  # Clean up once complete.
            # self.p.start("python", ['dummy_script.py'])
            self.p.start(tool_type, tool_args)

        while self.p is not None:
            sys.stdout.flush()
            if bt.cancel_op:
                bt.cancel_op = False
                self.p.terminate()

            else:
                break

    def stop_process(self):
        bt.cancel_op = True
        if self.p:
            self.p.kill()

    def handle_stderr(self):
        data = self.p.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        # Extract progress if it is in the data.
        progress = simple_percent_parser(stderr)
        if progress:
            self.progress_bar.setValue(progress)
        self.message(stderr)

    def handle_stdout(self):
        data = self.p.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.message(stdout)

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
        self.p = None


# start @ the beginning
faulthandler.enable()

app = QApplication(sys.argv)

window = MainWindow()
window.setMinimumSize(1024, 768)
window.show()

app.exec()
