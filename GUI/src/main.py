import sys
import serial
import serial.tools.list_ports
import threading

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, \
    QTableWidgetItem, QLineEdit, QLabel, QGridLayout, QPushButton, QMainWindow, QGroupBox, QDesktopWidget, QMessageBox
from PyQt5.QtCore import QTimer, Qt, QDateTime


def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description:
            return port.device
    return None


class CANMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.can_tx_table = None
        self.table_width = None
        self.column_width = None
        self.send_button = None
        self.byte_inputs = None
        self.id_input = None
        self.id_label = None
        self.can_tx_layout = None
        self.form_label = None
        self.can_rx_table = None
        self.central_widget = None
        self.init_GUI()
        self.ser = None
        self.can_rx_data = {}
        self.can_tx_data = []
        self.connect_serial()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_table)
        self.timer.start(500)

    def init_GUI(self):
        self.setWindowTitle("CAN-USB")
        self.setWindowIcon(QIcon("../img/icon.png"))
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        screen = QDesktopWidget().screenGeometry()
        screen_width = screen.width()
        screen_height = screen.height()

        self.column_width = 38
        self.table_width = 10 * self.column_width

        window_width = self.table_width + 580
        window_height = 500
        x_pos = (screen_width - window_width) // 2
        y_pos = (screen_height - window_height) // 2

        self.setGeometry(x_pos, y_pos, window_width, window_height)

        main_layout = QGridLayout()
        self.central_widget.setLayout(main_layout)

        can_rx_groupbox = self.create_can_rx_groupbox
        can_tx_groupbox = self.create_can_tx_groupbox
        can_tx_table_groupbox = self.create_can_tx_table_groupbox()

        main_layout.addWidget(can_rx_groupbox, 0, 0, 10, 1)
        main_layout.addWidget(can_tx_groupbox, 0, 1, 3, 1)
        main_layout.addWidget(can_tx_table_groupbox, 3, 1, 7, 1)

        self.setLayout(main_layout)

    @property
    def create_can_rx_groupbox(self):
        can_rx_groupbox = QGroupBox("CAN monitor")
        can_rx_layout = QGridLayout()
        can_rx_groupbox.setLayout(can_rx_layout)

        self.can_rx_table = QTableWidget()
        self.can_rx_table.setColumnCount(10)
        self.can_rx_table.setHorizontalHeaderLabels(["ID"] + [f"Byte {i + 1}" for i in range(8)] + ["Count"])

        for i in range(9):
            self.can_rx_table.setColumnWidth(i, self.column_width)

        self.can_rx_table.setColumnWidth(9, 80)
        self.can_rx_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        can_rx_layout.addWidget(self.can_rx_table)

        return can_rx_groupbox

    @property
    def create_can_tx_groupbox(self):
        can_tx_groupbox = QGroupBox("Frame setup")
        can_tx_layout = QGridLayout()
        can_tx_groupbox.setLayout(can_tx_layout)

        self.form_label = QLabel("Setup CAN frame to be sent (ID and bytes(1-8), e.g. 123, 11, 22, 33, 44, ...):")

        self.id_label = QLabel("ID")
        self.id_label.setAlignment(Qt.AlignCenter)

        self.id_input = QLineEdit()
        self.id_input.setFixedWidth(30)

        self.send_button = QPushButton("Send CAN frame")
        self.send_button.clicked.connect(self.send_can_message)

        self.byte_inputs = []
        for i in range(8):
            byte_label = QLabel(f"Byte {i + 1}")
            byte_label.setAlignment(Qt.AlignCenter)
            byte_input = QLineEdit()
            byte_input.setFixedWidth(30)
            self.byte_inputs.append(byte_input)
            can_tx_layout.addWidget(byte_label, 1, i + 1)
            can_tx_layout.addWidget(byte_input, 2, i + 1)

        can_tx_layout.addWidget(self.form_label, 0, 0, 1, 9)
        can_tx_layout.addWidget(self.id_label, 1, 0, 1, 1)
        can_tx_layout.addWidget(self.id_input, 2, 0, 1, 1)
        can_tx_layout.addWidget(self.send_button, 3, 0, 2, 9)

        return can_tx_groupbox

    def create_can_tx_table_groupbox(self):
        can_tx_groupbox = QGroupBox("CAN frames sent")
        can_tx_layout = QGridLayout()
        can_tx_groupbox.setLayout(can_tx_layout)

        self.can_tx_table = QTableWidget()
        self.can_tx_table.setColumnCount(10)
        self.can_tx_table.setHorizontalHeaderLabels(["ID"] + [f"Byte {i + 1}" for i in range(8)] + ["Timestamp"])

        for i in range(10):
            self.can_tx_table.setColumnWidth(i, self.column_width)

        self.can_tx_table.setColumnWidth(9, 80)
        can_tx_layout.addWidget(self.can_tx_table)

        return can_tx_groupbox

    def send_can_message(self):
        can_id = self.id_input.text().strip() # Copy data from the form

        # Check if user typed any ID
        if not can_id:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("ID is required!")
            msg.setInformativeText("Please enter any ID before sending.")
            msg.setWindowTitle("Error")
            msg.exec_()
            return

        if not can_id.startswith("0x"):
            can_id = "0x" + can_id

        # Check if the list has 8 bytes
        data_bytes = [byte.text().strip() for byte in self.byte_inputs]

        # Fill empty cells with 00
        data_bytes = [byte if byte else "00" for byte in data_bytes]

        # Fill last empty cells with 00
        data_bytes.extend(["00"] * (8 - len(data_bytes)))

        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss:ms")

        message = f"{can_id} " + " ".join(data_bytes)

        if self.ser and self.ser.is_open:
            self.ser.write((message + '\n').encode())

        self.can_tx_data.append([can_id] + data_bytes + [timestamp])
        self.update_sent_messages_table()

        self.id_input.clear()
        for byte_input in self.byte_inputs:
            byte_input.clear()

    def update_sent_messages_table(self):
        self.can_tx_table.setRowCount(0)

        for message in self.can_tx_data:
            row_position = self.can_tx_table.rowCount()
            self.can_tx_table.insertRow(row_position)
            for col, value in enumerate(message):
                self.can_tx_table.setItem(row_position, col, QTableWidgetItem(value))

            self.can_tx_table.scrollToBottom()

    def connect_serial(self):
        arduino_port = find_arduino_port()
        if arduino_port:
            try:
                self.ser = serial.Serial(arduino_port, 115200, timeout=1)
                self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
                self.serial_thread.start()
            except Exception as e:
                print(f"Failed to connect to Arduino: {e}")
        else:
            print("No Arduino found")

    def read_serial(self):
        while True:
            if self.ser and self.ser.is_open:
                line = self.ser.readline().decode(errors='ignore').strip()
                if line and line.startswith("Received: ID 0x"):
                    self.process_can_message(line)

    def process_can_message(self, message):
        parts = message.split()
        can_id = parts[2]
        data_bytes = parts[4:]

        if can_id not in self.can_rx_data:
            row_position = self.can_rx_table.rowCount()
            self.can_rx_table.insertRow(row_position)
            self.can_rx_data[can_id] = {'row_position': row_position, 'count': 1}
            self.can_rx_table.setItem(row_position, 0, QTableWidgetItem(can_id))
        else:
            row_position = self.can_rx_data[can_id]['row_position']
            self.can_rx_data[can_id]['count'] += 1

        for i in range(min(len(data_bytes), 8)):
            self.can_rx_table.setItem(row_position, i + 1, QTableWidgetItem(data_bytes[i]))

        self.can_rx_table.setItem(row_position, 9, QTableWidgetItem(str(self.can_rx_data[can_id]['count'])))

    def update_table(self):
        self.can_rx_table.viewport().update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CANMonitor()
    window.show()
    sys.exit(app.exec_())
