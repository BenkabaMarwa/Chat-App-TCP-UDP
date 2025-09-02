from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import socket
import threading
import os
import time
import pyttsx3 

# Replace with the actual IP address of the server
address = "192.168.x.x"
TcpPort = 12345
UdpPort = 12346

class HoverLabel(QLabel):
    def __init__(self, text, engine, lock, parent=None):
        super(HoverLabel, self).__init__(text, parent)
        self.setMouseTracking(True)
        self.engine = engine
        self.lock = lock
        self.is_speaking = False

    def enterEvent(self, event):
        if not self.is_speaking:
            text = self.text()
            if text:
                self.is_speaking = True
                threading.Thread(target=self.speak, args=(text,), daemon=True).start()
        super(HoverLabel, self).enterEvent(event)

    def speak(self, text):
        with self.lock:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except RuntimeError:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 150)
                self.engine.say(text)
                self.engine.runAndWait()
            finally:
                self.is_speaking = False

    def leaveEvent(self, event):
        super(HoverLabel, self).leaveEvent(event)

class Client(QtWidgets.QMainWindow):
    def __init__(self):
        super(Client, self).__init__()
        uic.loadUi("TcpUdp.ui", self)

        self.scrollArea.setStyleSheet("background-color: rgb(232, 232, 232);")
        self.desactivateClient.hide()

        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        self.tts_lock = threading.Lock()

        self.client_active = False
        self.client_socket = None
        self.protocol = "TCP"
        self.handshake_done = False

        self.sendButton.clicked.connect(self.send_text_message)
        self.sendFileButton.clicked.connect(self.send_file_message)
        self.activateClient.clicked.connect(self.start_client)
        self.desactivateClient.clicked.connect(self.stop_client)

        self.activateServer.setEnabled(False)
        self.desactivateServer.setEnabled(False)

        self.socketTypes.clear()
        self.socketTypes.addItems(["TCP", "UDP"])
        self.socketTypes.currentTextChanged.connect(self.on_protocol_changed)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.scroll_content)

        self.scroll_content_client = QWidget()
        self.scroll_layout_client = QVBoxLayout(self.scroll_content_client)
        self.scrollArea_client.setWidgetResizable(True)
        self.scrollArea_client.setWidget(self.scroll_content_client)

        self.scroll_content_system = QWidget()
        self.scroll_layout_system = QVBoxLayout(self.scroll_content_system)
        self.scrollArea_system.setWidgetResizable(True)
        self.scrollArea_system.setWidget(self.scroll_content_system)

        self.update_button_states()

    def update_button_states(self):
        self.activateClient.setEnabled(not self.client_active)
        self.desactivateClient.setEnabled(self.client_active)
        self.sendButton.setEnabled(self.client_active)
        self.sendFileButton.setEnabled(self.client_active)
        self.MessagelineEdit.setEnabled(self.client_active)

    def on_protocol_changed(self, text):
        if text in ["TCP", "UDP"]:
            self.protocol = text
            self.log_and_display("System", f"Selected protocol: {self.protocol}", "text")
            if self.client_active:
                self.stop_client()
                self.start_client()

    def start_client(self):
        if not self.client_active:
            self.client_active = True
            self.handshake_done = False
            max_retries = 3
            retry_delay = 5  # seconds
            for attempt in range(max_retries):
                if self.protocol == "TCP":
                    try:
                        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        self.client_socket.settimeout(300)  # Increased timeout
                        self.client_socket.connect((address, TcpPort))
                        self.client_socket.send("SYN".encode('utf-8'))
                        self.log_and_display("Client", "Sent: SYN", "text")
                        syn_ack = self.client_socket.recv(4096).decode('utf-8')
                        self.log_and_display("Server", f"Received: {syn_ack}", "text")
                        self.client_socket.send("ACK".encode('utf-8'))
                        self.log_and_display("Client", "Sent: ACK", "text")
                        self.handshake_done = True
                        self.log_and_display("System", "Client started successfully (TCP)", "text")
                        break
                    except socket.timeout:
                        self.log_and_display("System", f"Connection timed out (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...", "text")
                        time.sleep(retry_delay)
                        if attempt == max_retries - 1:
                            self.log_and_display("System", "Failed to connect to TCP server after retries.", "text")
                            self.client_active = False
                    except Exception as e:
                        self.log_and_display("System", f"Error starting client (TCP): {e}", "text")
                        self.client_active = False
                        break
                else:  # UDP
                    try:
                        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        self.client_socket.settimeout(300)  # Increased timeout
                        self.log_and_display("System", "Client started successfully (UDP)", "text")
                        break
                    except Exception as e:
                        self.log_and_display("System", f"Error starting client (UDP): {e}", "text")
                        self.client_active = False
                        break
            self.update_button_states()
        else:
            self.log_and_display("System", "Client is already running", "text")

    def stop_client(self):
        if self.client_active:
            self.client_active = False
            self.handshake_done = False
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            time.sleep(1)
            self.log_and_display("System", "Client stopped successfully", "text")
            self.update_button_states()
        else:
            self.log_and_display("System", "Client is not active", "text")

    def send_to_server(self, message, msg_type):
        if not self.client_active:
            self.log_and_display("System", "Client is not active. Please start the client first.", "text")
            return
        if self.protocol == "TCP":
            self.send_to_server_tcp(message, msg_type)
        else:
            self.send_to_server_udp(message, msg_type)

    def send_to_server_tcp(self, message, msg_type):
        try:
            msg_type_bytes = msg_type.encode('utf-8')
            self.client_socket.sendall(len(msg_type_bytes).to_bytes(4, 'big') + msg_type_bytes)
            self.log_and_display("System", f"Sending message type: {msg_type}", "text")

            if msg_type == "TEXT":
                text_bytes = message.encode('utf-8')
                self.client_socket.sendall(len(text_bytes).to_bytes(4, 'big') + text_bytes)
                self.log_and_display("Client", f"Sent: {message}", "text")
            elif msg_type == "FILE":
                filename = os.path.basename(message)
                name_bytes = filename.encode('utf-8')
                self.client_socket.sendall(len(name_bytes).to_bytes(4, 'big') + name_bytes)
                self.log_and_display("Client", f"Sending file: {filename}", "file", file_path=message)

                file_size = os.path.getsize(message)
                self.client_socket.sendall(file_size.to_bytes(8, 'big'))

                with open(message, "rb") as f:
                    chunk_count = 0
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        self.client_socket.sendall(data)
                        chunk_count += 1
                        print(f"Sent chunk {chunk_count} of size {len(data)}")  # Debugging
                self.log_and_display("System", "File sent successfully", "text")

            resp_len_data = self.client_socket.recv(4)
            if not resp_len_data:
                self.log_and_display("System", "No response received from server", "text")
                return
            resp_len = int.from_bytes(resp_len_data, byteorder='big')
            response = self.client_socket.recv(resp_len).decode('utf-8')
            self.log_and_display("Server", response, "text")
        except socket.timeout:
            self.log_and_display("System", "Connection timed out", "text")
        except Exception as e:
            self.log_and_display("System", f"TCP Error: {e}", "text")

    def send_to_server_udp(self, message, msg_type):
        try:
            if msg_type == "TEXT":
                payload = f"TEXT|{message}".encode('utf-8')
                self.client_socket.sendto(payload, (address, UdpPort))
                self.log_and_display("Client", f"Sent text: {message}", "text")
            elif msg_type == "FILE":
                filename = os.path.basename(message)
                header = f"FILE|{filename}".encode('utf-8')
                self.client_socket.sendto(header, (address, UdpPort))
                self.log_and_display("Client", f"Sending file: {filename}", "file", file_path=message)

                with open(message, "rb") as f:
                    chunk_count = 0
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        self.client_socket.sendto(data, (address, UdpPort))
                        chunk_count += 1
                        print(f"Sent chunk {chunk_count} of size {len(data)}")  # Debugging
                eof_marker = b"EOF12345"
                self.client_socket.sendto(eof_marker, (address, UdpPort))
                print("Sent EOF")

            self.client_socket.settimeout(10)
            response, _ = self.client_socket.recvfrom(4096)
            self.log_and_display("Server", response.decode('utf-8'), "text")
        except socket.timeout:
            self.log_and_display("System", "Timeout: Server did not respond.", "text")
        except Exception as e:
            self.log_and_display("System", f"Error: {e}", "text")
        finally:
            self.client_socket.settimeout(None)

    def send_text_message(self):
        text = self.MessagelineEdit.text()
        if text.strip() == "":
            self.log_and_display("System", "Cannot send empty message", "text")
            return
        self.send_to_server(text, "TEXT")
        self.MessagelineEdit.clear()

    def send_file_message(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose File", "",
            "All Files (*);;Images (*.png *.jpg *.jpeg *.bmp);;PDF (*.pdf);;Video (*.mp4 *.avi *.mov)")
        if file_path:
            self.send_to_server(file_path, "FILE")

    def log_and_display(self, sender, message, msg_type, file_path=None):
        frame_color = "#55aaff" if sender == "Client" else "#808080" if sender == "Server" else "#ffaa00"
        alignment = Qt.AlignRight if sender == "Client" else Qt.AlignLeft if sender == "Server" else Qt.AlignCenter

        frame = QtWidgets.QFrame()
        frame.setMaximumWidth(700)
        frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        frame.setStyleSheet(f"""
            background-color: {frame_color};
            border-radius: 10px;
            margin: 5px;
            padding: 10px;
        """)
        layout = QtWidgets.QVBoxLayout(frame)

        label_sender = HoverLabel(sender, self.tts_engine, self.tts_lock)
        label_sender.setStyleSheet("font-weight: bold; font-size: 8pt; color: white; background-color: transparent;")
        label_sender.setAlignment(Qt.AlignCenter)
        label_sender.adjustSize()
        layout.addWidget(label_sender)

        if msg_type == "text":
            label_msg = HoverLabel(message, self.tts_engine, self.tts_lock)
            label_msg.setStyleSheet("font-size: 8pt; color: white; background-color: transparent;")
            label_msg.setWordWrap(True)
            label_msg.setAlignment(Qt.AlignCenter)
            label_msg.adjustSize()
            layout.addWidget(label_msg)
        elif msg_type == "file":
            if file_path and file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                img_label = QLabel()
                pixmap = QPixmap(file_path)
                scaled_pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(scaled_pixmap)
                img_label.setAlignment(Qt.AlignCenter)
                img_label.adjustSize()
                layout.addWidget(img_label)
                
                btn_open = QPushButton("Open Image")
                btn_open.setStyleSheet("font-size: 14pt; color: white; background-color: #4CAF50; border-radius: 5px;")
                btn_open.clicked.connect(lambda: self.open_file(file_path))
                btn_open.setFixedWidth(150)
                layout.addWidget(btn_open, alignment=Qt.AlignCenter)
            elif file_path and file_path.lower().endswith('.pdf'):
                btn = QPushButton("View PDF")
                btn.setStyleSheet("font-size: 14pt; color: white; background-color: #4CAF50; border-radius: 5px;")
                btn.clicked.connect(lambda: self.open_file(file_path))
                btn.setFixedWidth(150)
                layout.addWidget(btn, alignment=Qt.AlignCenter)
            elif file_path and file_path.lower().endswith(('.mp4', '.avi', '.mov')):
                btn = QPushButton("Play Video")
                btn.setStyleSheet("font-size: 14pt; color: white; background-color: #4CAF50; border-radius: 5px;")
                btn.clicked.connect(lambda: self.open_file(file_path))
                btn.setFixedWidth(150)
                layout.addWidget(btn, alignment=Qt.AlignCenter)
            else:
                label_msg = QLabel("Unsupported file type")
                label_msg.setStyleSheet("font-size: 8pt; color: white; background-color: transparent;")
                label_msg.adjustSize()
                layout.addWidget(label_msg)

        frame.adjustSize()

        if sender == "Client":
            self.scroll_layout_client.addWidget(frame, alignment=alignment)
            QTimer.singleShot(0, lambda: self.scrollArea_client.verticalScrollBar().setValue(
                self.scrollArea_client.verticalScrollBar().maximum()))
        elif sender == "Server":
            self.scroll_layout.addWidget(frame, alignment=alignment)
            QTimer.singleShot(0, lambda: self.scrollArea.verticalScrollBar().setValue(
                self.scrollArea.verticalScrollBar().maximum()))
        else:  # System
            self.scroll_layout_system.addWidget(frame, alignment=alignment)
            QTimer.singleShot(0, lambda: self.scrollArea_system.verticalScrollBar().setValue(
                self.scrollArea_system.verticalScrollBar().maximum()))

    def open_file(self, file_path):
        if os.path.exists(file_path):
            url = QUrl.fromLocalFile(file_path)
            if not QDesktopServices.openUrl(url):
                self.log_and_display("System", "Failed to open file. Ensure an appropriate application is installed.", "text")
        else:
            self.log_and_display("System", f"File not found: {file_path}", "text")

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = Client()
    window.show()
    sys.exit(app.exec_())
