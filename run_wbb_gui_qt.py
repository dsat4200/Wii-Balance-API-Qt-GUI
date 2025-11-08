import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem
)
from PyQt6.QtCore import Qt, QPointF, QThread
from PyQt6.QtGui import QFont, QColor, QPen, QBrush, QPainter
from WiiBalanceBoard_qt import WiiBalanceBoard # Import the Qt-enabled API

class CoMWidget(QGraphicsView):
    """
    A custom widget to display the Center of Mass,
    replacing the tkinter canvas.
    """
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        # --- FIX 1: Force a square aspect ratio to prevent distortion ---
        self.scene.setSceneRect(-100, -100, 200, 200) 
        self.setFixedSize(202, 202)
        
        # Set gray background and remove scrollbars
        self.setBackgroundBrush(QColor(240, 240, 240))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Draw crosshairs
        self.scene.addLine(-100, 0, 100, 0, QPen(Qt.GlobalColor.lightGray, 1, Qt.PenStyle.DashLine))
        self.scene.addLine(0, -100, 0, 100, QPen(Qt.GlobalColor.lightGray, 1, Qt.PenStyle.DashLine))
        
        # Draw labels
        font = QFont("Helvetica", 9)
        top_label = self.scene.addText("Top (+Y)", font)
        top_label.setPos(-top_label.boundingRect().width() / 2, -100)
        
        bottom_label = self.scene.addText("Bottom (-Y)", font)
        bottom_label.setPos(-bottom_label.boundingRect().width() / 2, 90)

        left_label = self.scene.addText("L\n(-X)", font)
        left_label.setPos(-98, -left_label.boundingRect().height() / 2)
        
        right_label = self.scene.addText("R\n(+X)", font)
        right_label.setPos(98 - right_label.boundingRect().width(), -right_label.boundingRect().height() / 2)
        
        # --- Create pressure dots ---
        pressure_brush = QBrush(QColor(0, 0, 255, 120)) # Semi-transparent blue
        pressure_pen = QPen(QColor(0, 0, 255, 180), 1)
        min_r = self._map_weight_to_radius(0)
        
        # Top-Left dot
        self.tl_dot = self.scene.addEllipse(0, 0, min_r * 2, min_r * 2, pressure_pen, pressure_brush)
        self.tl_dot.setPos(-90, -90) # Y is negative-up
        
        # Top-Right dot
        self.tr_dot = self.scene.addEllipse(0, 0, min_r * 2, min_r * 2, pressure_pen, pressure_brush)
        self.tr_dot.setPos(90, -90)
        
        # Bottom-Left dot
        self.bl_dot = self.scene.addEllipse(0, 0, min_r * 2, min_r * 2, pressure_pen, pressure_brush)
        self.bl_dot.setPos(-90, 90)
        
        # Bottom-Right dot
        self.br_dot = self.scene.addEllipse(0, 0, min_r * 2, min_r * 2, pressure_pen, pressure_brush)
        self.br_dot.setPos(90, 90)

        # --- FIX 2: Made the dot smaller (4x4) ---
        self.com_dot = QGraphicsEllipseItem(-2, -2, 4, 4) # Was 6x6
        self.com_dot.setBrush(QBrush(Qt.GlobalColor.red))
        self.com_dot.setPen(QPen(Qt.GlobalColor.red))
        self.scene.addItem(self.com_dot)
        
        # --- FIX: Remove fitInView from __init__ ---
        # We will call this in resizeEvent instead
        # self.fitInView(self.scene.sceneRect()) 
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

    def _map_weight_to_radius(self, weight):
        """Helper to map a weight (kg) to a circle radius (px)."""
        min_weight = 0.5  # kg to start showing
        max_weight = 80.0 # kg to be max size (was 20.0)
        min_radius = 3    # px
        max_radius = 25   # px
        
        if weight <= min_weight: return min_radius
        if weight >= max_weight: return max_radius
        
        percent = (weight - min_weight) / (max_weight - min_weight)
        radius = min_radius + (percent * (max_radius - min_radius))
        return radius

    def resizeEvent(self, event):
        """
        Called when the widget is resized. This ensures the scene
        always fits the view and keeps its 1:1 aspect ratio,
        preventing the rectangular distortion you are seeing.
        """
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        super().resizeEvent(event)

    def update_dot(self, x, y, quadrants):
        """
        Updates the dot position and corner pressure circles.
        x and y range from -1.0 to +1.0.
        Scene coordinates range from -100 to +100.
        """
        # Y is inverted: +1.0 (Top) in data is -100 in scene
        # --- FIX 3: Clamp range to 90% to keep dot from going off-edge ---
        canvas_x = x * 90 
        canvas_y = y * -90
        self.com_dot.setPos(canvas_x, canvas_y)
        
        # Update quadrant pressure circles
        tl_r = self._map_weight_to_radius(quadrants['top_left'])
        tr_r = self._map_weight_to_radius(quadrants['top_right'])
        bl_r = self._map_weight_to_radius(quadrants['bottom_left'])
        br_r = self._map_weight_to_radius(quadrants['bottom_right'])
        
        # setRect(x, y, w, h) - x/y are relative to the item's *position*
        # We set pos() in __init__, so we just need to update the rect
        # from (-r, -r) to (r, r) to keep it centered on its position.
        self.tl_dot.setRect(-tl_r, -tl_r, tl_r * 2, tl_r * 2)
        self.tr_dot.setRect(-tr_r, -tr_r, tr_r * 2, tr_r * 2)
        self.bl_dot.setRect(-bl_r, -bl_r, bl_r * 2, bl_r * 2)
        self.br_dot.setRect(-br_r, -br_r, br_r * 2, br_r * 2)

class BalanceBoardApp(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()
        self.init_board()

    def init_ui(self):
        self.setWindowTitle("Wii Balance Board Monitor (PyQt6)")
        self.setGeometry(100, 100, 400, 550)
        
        # --- Layouts ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # --- Total Weight Labels ---
        total_weight_header = QLabel("Total Weight")
        total_weight_header.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        total_weight_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.total_weight_label = QLabel("--.- kg")
        self.total_weight_label.setFont(QFont("Helvetica", 28, QFont.Weight.Bold))
        self.total_weight_label.setStyleSheet("color: #007ACC;")
        self.total_weight_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- Quadrant Labels ---
        quad_layout = QHBoxLayout()
        quad_frame = QFrame()
        quad_frame.setLayout(quad_layout)
        
        self.tl_label = QLabel("TL: --.- kg")
        self.tr_label = QLabel("TR: --.- kg")
        self.bl_label = QLabel("BL: --.- kg")
        self.br_label = QLabel("BR: --.- kg")
        
        for label in [self.tl_label, self.tr_label, self.bl_label, self.br_label]:
            label.setFont(QFont("Helvetica", 12))
            label.setMinimumWidth(100)

        # Arrange in a 2x2 grid style within the HBox
        v_layout_left = QVBoxLayout()
        v_layout_left.addWidget(self.tl_label)
        v_layout_left.addWidget(self.bl_label)
        
        v_layout_right = QVBoxLayout()
        v_layout_right.addWidget(self.tr_label)
        v_layout_right.addWidget(self.br_label)
        
        quad_layout.addLayout(v_layout_left)
        quad_layout.addLayout(v_layout_right)

        # --- Center of Mass ---
        com_header = QLabel("Center of Mass")
        com_header.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        com_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.com_widget = CoMWidget()
        com_widget_layout = QHBoxLayout()
        com_widget_layout.addStretch()
        com_widget_layout.addWidget(self.com_widget)
        com_widget_layout.addStretch()

        # --- Tare Button ---
        self.tare_button = QPushButton("Tare (Zero)")
        self.tare_button.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.tare_button.setEnabled(False)
        self.tare_button.setMinimumHeight(40)
        
        # --- Status Bar ---
        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Helvetica", 10))
        self.status_label.setStyleSheet("border-top: 1px solid #CCC; padding: 5px;")
        
        # --- Add widgets to main layout ---
        main_layout.addWidget(total_weight_header)
        main_layout.addWidget(self.total_weight_label)
        main_layout.addWidget(quad_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(com_header)
        main_layout.addLayout(com_widget_layout)
        main_layout.addStretch() # Pushes button and status bar down
        main_layout.addWidget(self.tare_button)
        main_layout.addWidget(self.status_label)

    def init_board(self):
        """Create the thread and the board worker object."""
        self.processing_thread = QThread()
        self.board = WiiBalanceBoard(self.config)
        
        # Move the board object to the thread
        self.board.moveToThread(self.processing_thread)
        
        # --- Connect signals from board to GUI slots ---
        self.board.data_received.connect(self.update_gui)
        self.board.status_update.connect(self.set_status)
        self.board.error_occurred.connect(self.handle_error)
        
        self.board.ready_to_tare.connect(lambda: self.tare_button.setEnabled(True))
        self.board.tare_complete.connect(self.on_tare_complete)
        
        # --- Connect thread signals ---
        # When thread starts, tell the board to start its loop
        self.processing_thread.started.connect(self.board.start_processing_loop)
        # When thread is done, clean it up
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)
        self.board.finished.connect(self.processing_thread.quit) # Ensure thread quits if board finishes
        
        # --- Connect GUI signals to board slots ---
        self.tare_button.clicked.connect(self.on_tare_click)
        
        # Start the thread
        self.processing_thread.start()

    # --- GUI Slots ---
    
    def update_gui(self, data):
        """Slot to update all GUI elements with new data."""
        self.total_weight_label.setText(f"{data['total_kg']:.2f} kg")
        self.tr_label.setText(f"TR: {data['quadrants_kg']['top_right']:.2f} kg")
        self.tl_label.setText(f"TL: {data['quadrants_kg']['top_left']:.2f} kg")
        self.br_label.setText(f"BR: {data['quadrants_kg']['bottom_right']:.2f} kg")
        self.bl_label.setText(f"BL: {data['quadrants_kg']['bottom_left']:.2f} kg")
        
        x, y = data['center_of_mass']
        quadrants = data['quadrants_kg']
        self.com_widget.update_dot(x, y, quadrants)

    def set_status(self, text):
        """Slot to update the status bar."""
        self.status_label.setText(text)

    def handle_error(self, text):
        """Slot to show an error. Disables tare button."""
        self.set_status(text)
        self.tare_button.setEnabled(False)

    def on_tare_click(self):
        """Slot for when the tare button is clicked."""
        self.set_status("🔵 Taring... Please step OFF the board.")
        self.tare_button.setEnabled(False)
        # This call is queued and executed in the board's thread
        self.board.perform_tare() 

    def on_tare_complete(self, success):
        """Slot for when the board signals tare is complete."""
        if success:
            self.set_status("✅ Ready! Please step ON the board.")
        else:
            self.set_status("❌ Tare failed. No data. Try again.")
        self.tare_button.setEnabled(True)

    def closeEvent(self, event):
        """Overrides the window close event to safely shut down the thread."""
        print("Closing application...")
        if self.processing_thread.isRunning():
            self.board.stop_processing() # Tell the loop to stop
            self.processing_thread.quit()    # Ask the thread to exit
            self.processing_thread.wait(3000) # Wait up to 3 sec
        event.accept()

def load_config():
    """Loads the config.json file."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("config.json not found, using defaults.")
        return {
            "tare_duration_sec": 3.0,
            "polling_rate_hz": 30,
            "averaging_samples": 5
        }
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

if __name__ == "__main__":
    config = load_config()
    
    app = QApplication(sys.argv)
    window = BalanceBoardApp(config)
    window.show()
    sys.exit(app.exec())