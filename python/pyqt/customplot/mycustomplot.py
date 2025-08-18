import numpy as np
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QFileDialog,
    QLabel,
)
from PyQt5.QtCore import Qt, QPointF, QMargins
from PyQt5.QtGui import QFont, QPen, QColor, QBrush
from QCustomPlot_PyQt5 import (
    QCustomPlot,
    QCP,
    QCPItemStraightLine,
    QCPItemText,
    QCPItemEllipse,
    QCPItemPosition,
)


class MyCustomPlot(QMainWindow):
    ZOOM_IN_FACTOR = 0.95
    ZOOM_OUT_FACTOR = 1.05

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.data_loaded = False
        self.x_data = None
        self.y_data = None
        self.current_index = None
        self.show_markers = False
        self.max_indicators = []
        self.max_points = []
        self.min_indicators = []
        self.min_points = []

    def setup_ui(self):
        self.setWindowTitle("My CustomPlot")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with 10%-90% split
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Control panel (10%)
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)

        self.file_label = QLabel("No file selected")
        self.select_btn = QPushButton("Select Data File")
        self.select_btn.clicked.connect(self.load_data_file)

        self.cursor_label = QLabel("Cursor: Not available")
        control_layout.addWidget(self.file_label)
        control_layout.addWidget(self.select_btn)
        control_layout.addWidget(self.cursor_label)

        # Plot area (90%)
        self.plot = QCustomPlot()
        self.plot.setInteractions(QCP.iRangeDrag | QCP.iRangeZoom)

        # Configure default interactions
        self.plot.axisRect().setRangeZoom(Qt.Horizontal)  # Default horizontal zoom
        self.plot.axisRect().setRangeDrag(Qt.Horizontal)  # Default horizontal drag

        # Connect signals
        self.plot.mouseWheel.connect(self.handle_mouse_wheel)
        self.plot.mouseDoubleClick.connect(self.handle_double_click)
        self.plot.mousePress.connect(self.handle_mouse_press)
        self.plot.mouseRelease.connect(self.handle_mouse_release)
        self.plot.mouseMove.connect(self.handle_mouse_move)

        # Initialize cursor lines
        self.init_cursor()

        # Set stretch factors
        main_layout.addWidget(control_widget, stretch=0)
        main_layout.addWidget(self.plot, stretch=9)

    def toggle_markers(self):
        """Toggle display of max and min value text markers"""
        self.show_markers = not self.show_markers

        self.clear_all_markers()

        if self.show_markers and self.data_loaded:
            max_val = np.max(self.y_data)
            min_val = np.min(self.y_data)
            max_indices = np.where(self.y_data == max_val)[0]
            min_indices = np.where(self.y_data == min_val)[0]

            for idx in max_indices:
                x, y = self.x_data[idx], self.y_data[idx]
                self.create_text_marker(x, y, f"Max: {y:.2f}", QColor(255, 0, 0))

            for idx in min_indices:
                x, y = self.x_data[idx], self.y_data[idx]
                self.create_text_marker(x, y, f"Min: {y:.2f}", QColor(0, 0, 255))

        self.plot.replot()

    def get_dynamic_marker_size(self):
        """Calculate marker size based on current view scale"""

        x_range = self.plot.xAxis.range().size()
        y_range = self.plot.yAxis.range().size()

        base_size = 0.008  # 0.8% of axis range

        avg_range = (x_range + y_range) / 2
        return base_size * avg_range

    def clear_all_markers(self):
        """Remove all existing text markers"""
        all_markers = [*self.max_indicators, *self.min_indicators]

        for marker in all_markers:
            try:
                self.plot.removeItem(marker)
            except (RuntimeError, AttributeError):
                continue

        self.max_indicators.clear()
        self.min_indicators.clear()

    def create_text_marker(self, x, y, text, color):
        """Create vertical text marker"""
        marker_size = self.get_dynamic_marker_size()
        text_offset = marker_size * 2.5

        indicator = QCPItemText(self.plot)
        indicator.setText(text)
        indicator.position.setType(QCPItemPosition.ptPlotCoords)

        indicator.setRotation(-90)
        indicator.setTextAlignment(Qt.AlignCenter)

        font = QFont()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(10)
        indicator.setFont(font)

        indicator.setPen(QPen(color))
        indicator.setBrush(QBrush(Qt.white))
        indicator.setPadding(QMargins(2, 1, 2, 1))

        x_pos = x
        y_pos = y

        if "Max" in text:
            # x_pos = x + text_offset
            y_pos = y + text_offset
        else:
            # x_pos = x - text_offset
            y_pos = y - text_offset

        indicator.position.setCoords(x_pos, y_pos)

        if "Max" in text:
            self.max_indicators.append(indicator)
        else:
            self.min_indicators.append(indicator)

    def init_cursor(self):
        """Initialize cursor lines and text labels"""
        # Create vertical cursor line (X)
        self.cursor_line_x = QCPItemStraightLine(self.plot)
        self.cursor_line_x.setPen(QPen(QColor(255, 100, 0), 1, Qt.DashLine))

        # Create horizontal cursor line (Y)
        self.cursor_line_y = QCPItemStraightLine(self.plot)
        self.cursor_line_y.setPen(QPen(QColor(255, 100, 0), 1, Qt.DashLine))

        # Create cursor text labels
        self.cursor_text_x = QCPItemText(self.plot)
        self.cursor_text_y = QCPItemText(self.plot)

        # Configure text labels
        self.cursor_text_x.setPositionAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.cursor_text_y.setPositionAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cursor_text_x.setText("")
        self.cursor_text_y.setText("")

        # Hide cursors initially
        self.cursor_line_x.setVisible(False)
        self.cursor_line_y.setVisible(False)
        self.cursor_text_x.setVisible(False)
        self.cursor_text_y.setVisible(False)

    def update_cursor(self, x, y):
        """Update cursor position and display data values"""
        if not self.data_loaded:
            return

        self.cursor_line_x.point1.setCoords(x, self.plot.yAxis.range().lower)
        self.cursor_line_x.point2.setCoords(x, self.plot.yAxis.range().upper)

        self.cursor_line_y.point1.setCoords(self.plot.xAxis.range().lower, y)
        self.cursor_line_y.point2.setCoords(self.plot.xAxis.range().upper, y)

        # self.cursor_text_x.setText(f"X={x:.2f}")
        # self.cursor_text_x.position.setCoords(x, self.plot.yAxis.range().upper)
        #
        # self.cursor_text_y.setText(f"Y={y:.2f}")
        # self.cursor_text_y.position.setCoords(self.plot.xAxis.range().lower, y)

        self.cursor_label.setText(
            f"Data Point: Index={self.current_index}, X={x:.2f}, Y={y:.2f}"
        )

        self.cursor_line_x.setVisible(True)
        self.cursor_line_y.setVisible(True)
        self.cursor_text_x.setVisible(True)
        self.cursor_text_y.setVisible(True)
        self.plot.replot()

    def handle_mouse_move(self, event):
        """Handle mouse movement to update cursor (only on data points)"""
        if not self.data_loaded:
            return

        mouse_x = self.plot.xAxis.pixelToCoord(event.pos().x())
        closest_index = np.argmin(np.abs(self.x_data - mouse_x))

        if 0 <= closest_index < len(self.x_data):
            x = self.x_data[closest_index]
            y = self.y_data[closest_index]
            self.current_index = closest_index
            self.update_cursor(x, y)

    def keyPressEvent(self, event):
        """Handle keyboard events for plot navigation"""
        if not self.data_loaded:
            return

        # Get current axis ranges
        x_range = self.plot.xAxis.range()
        y_range = self.plot.yAxis.range()
        x_size = x_range.size()
        y_size = y_range.size()

        # Calculate step size (10% of current range)
        x_step = x_size * 0.1
        y_step = y_size * 0.1

        # Handle arrow keys
        if event.key() == Qt.Key_Left:
            if event.modifiers() & Qt.ShiftModifier:
                self.plot.xAxis.scaleRange(MyCustomPlot.ZOOM_OUT_FACTOR, x_range.center())
            else:
                self.plot.xAxis.setRange(x_range.lower - x_step, x_range.upper - x_step)

        elif event.key() == Qt.Key_Right:
            if event.modifiers() & Qt.ShiftModifier:
                self.plot.xAxis.scaleRange(MyCustomPlot.ZOOM_IN_FACTOR, x_range.center())
            else:
                self.plot.xAxis.setRange(x_range.lower + x_step, x_range.upper + x_step)

        elif event.key() == Qt.Key_Up:
            if event.modifiers() & Qt.ShiftModifier:
                self.plot.yAxis.scaleRange(MyCustomPlot.ZOOM_IN_FACTOR, y_range.center())
            else:
                self.plot.yAxis.setRange(y_range.lower + y_step, y_range.upper + y_step)

        elif event.key() == Qt.Key_Down:
            if event.modifiers() & Qt.ShiftModifier:
                self.plot.yAxis.scaleRange(MyCustomPlot.ZOOM_OUT_FACTOR, y_range.center())
            else:
                self.plot.yAxis.setRange(y_range.lower - y_step, y_range.upper - y_step)

        # Handle other keys
        elif event.key() == Qt.Key_M:
            self.toggle_markers()
        elif event.key() == Qt.Key_Q:
            self.close()
            return
        else:
            return

        self.plot.replot()

    def handle_mouse_wheel(self, event):
        """Handle mouse wheel events for zooming"""
        if not self.data_loaded:
            return

        # Check Ctrl modifier
        if event.modifiers() & Qt.ControlModifier:
            # Vertical zoom when Ctrl is pressed
            self.plot.axisRect().setRangeZoom(Qt.Vertical)
        else:
            # Horizontal zoom by default
            self.plot.axisRect().setRangeZoom(Qt.Horizontal)

        # Update drag mode based on current Ctrl state
        if event.modifiers() & Qt.ControlModifier:
            self.plot.axisRect().setRangeDrag(Qt.Horizontal | Qt.Vertical)
        else:
            self.plot.axisRect().setRangeDrag(Qt.Horizontal)

    def handle_mouse_press(self, event):
        """Update drag mode when mouse is pressed"""
        if not self.data_loaded:
            return

        if event.modifiers() & Qt.ControlModifier:
            self.plot.axisRect().setRangeDrag(Qt.Horizontal | Qt.Vertical)
        else:
            self.plot.axisRect().setRangeDrag(Qt.Horizontal)

    def handle_mouse_release(self, event):
        """Reset to default drag mode when mouse is released"""
        if self.data_loaded:
            self.plot.axisRect().setRangeDrag(Qt.Horizontal)

    def handle_double_click(self, event):
        """Handle plot double click to reset view"""
        if event.button() == Qt.LeftButton and self.data_loaded:
            self.reset_view()

    def reset_view(self):
        """Reset plot view and update marker positions"""
        if self.data_loaded:
            self.plot.rescaleAxes()

            # if self.show_markers:
            #     self.clear_all_markers()
            #     self.toggle_markers()

            self.plot.axisRect().setRangeZoom(Qt.Horizontal)
            self.plot.axisRect().setRangeDrag(Qt.Horizontal)
            self.plot.replot()

    def load_data_file(self):
        """Open file dialog and load selected data file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", "Text Files (*.txt);;All Files (*)"
        )

        if not filename:
            return

        try:
            # Read file and skip comment lines
            with open(filename, "r") as f:
                lines = [line.strip() for line in f if not line.startswith("===")]

            # Convert to numpy array
            self.y_data = np.array([float(line) for line in lines if line])
            self.x_data = np.arange(len(self.y_data))
            self.data_loaded = True

            # Update UI
            self.file_label.setText(f"Loaded: {filename.split('/')[-1]}")
            self.plot_data()

        except Exception as e:
            self.file_label.setText(f"Error loading file: {str(e)}")
            self.data_loaded = False

    def plot_data(self):
        """Plot the loaded data"""
        self.plot.clearPlottables()
        self.show_markers = False
        self.clear_all_markers()

        # Create graph
        self.plot.addGraph()
        self.plot.graph(0).setData(self.x_data, self.y_data)
        self.plot.graph(0).setName("BLM Data")

        # Configure axes
        self.plot.xAxis.setLabel("Sample Index")
        self.plot.yAxis.setLabel("Value")

        # Auto-scale to show all data
        self.reset_view()


if __name__ == "__main__":
    app = QApplication([])
    window = MyCustomPlot()
    window.show()
    app.exec_()
