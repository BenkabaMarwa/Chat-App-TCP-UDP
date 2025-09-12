from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import socket
import threading
import os
import time
import pyttsx3
import pyautogui

address = "0.0.0.0"  # Bind to all interfaces
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

class Server(QtWidgets.QMainWindow):
    update_signal = pyqtSignal(str, str, str, str)  # (sender, message, msg_type, file_path)

    def __init__(self):
        super(Server, self).__init__()
        uic.loadUi("TcpUdp.ui", self)

        self.desactivateServer.hide()
        self.scrollArea_client.setStyleSheet("background-color: rgb(232, 232, 232);")

        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        self.tts_lock = threading.Lock()

        self.server_active = False
        self.server_thread = None
        self.server_socket = None
        self.protocol = "TCP"
        self.clients = []

        self.activateServer.clicked.connect(self.start_server)
        self.desactivateServer.clicked.connect(self.stop_server)

        self.activateClient.setEnabled(False)
        self.desactivateClient.setEnabled(False)
        self.sendButton.setEnabled(False)
        self.sendFileButton.setEnabled(False)
        self.MessagelineEdit.setEnabled(False)

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

        self.update_signal.connect(self.update_display)
        self.update_button_states()

    def update_button_states(self):
        self.activateServer.setEnabled(not self.server_active)
        self.desactivateServer.setEnabled(self.server_active)

    def on_protocol_changed(self, text):
        if text in ["TCP", "UDP"]:
            self.protocol = text
            self.log_and_display("System", f"Selected protocol: {self.protocol}", "text")
            if self.server_active:
                self.stop_server()
                self.start_server()

    def start_server(self):
        if not self.server_active:
            self.server_active = True
            self.server_thread = threading.Thread(target=self.run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            self.log_and_display("System", "Server started successfully", "text")
            self.update_button_states()
        else:
            self.log_and_display("System", "Server is already running", "text")

    def stop_server(self):
        if self.server_active:
            self.server_active = False
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            for client in self.clients:
                client.close()
            self.clients.clear()
            time.sleep(1)
            self.log_and_display("System", "Server stopped successfully", "text")
            self.update_button_states()
        else:
            self.log_and_display("System", "Server is not active", "text")

    def run_server(self):
        if self.protocol == "TCP":
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self.server_socket.bind((address, TcpPort))
                self.server_socket.listen(5)
                self.server_socket.settimeout(300)  # Increased timeout
                self.log_and_display("System", "Server listening on port 12345 (TCP)", "text")

                while self.server_active:
                    try:
                        client_socket, addr = self.server_socket.accept()
                        self.clients.append(client_socket)
                        threading.Thread(target=self.handle_client_tcp, args=(client_socket, addr)).start()
                    except socket.timeout:
                        if self.server_active:
                            self.log_and_display("System", "TCP server timeout after 300 seconds", "text")
                    except Exception as e:
                        if self.server_active:
                            self.log_and_display("System", f"Error accepting clients (TCP): {e}", "text")
                        break
            except Exception as e:
                self.log_and_display("System", f"Error starting server (TCP): {e}", "text")
                self.server_active = False
                self.update_button_states()
            finally:
                if self.server_socket:
                    self.server_socket.close()
                    self.server_socket = None
        else:  # UDP
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self.server_socket.bind((address, UdpPort))
                self.server_socket.settimeout(300)  # Increased timeout
                self.log_and_display("System", "Server listening on port 12346 (UDP)", "text")

                while self.server_active:
                    try:
                        data, addr = self.server_socket.recvfrom(4096)
                        threading.Thread(target=self.handle_client_udp, args=(data, addr)).start()
                    except socket.timeout:
                        if self.server_active:
                            self.log_and_display("System", "UDP server timeout after 300 seconds", "text")
                    except Exception as e:
                        if self.server_active:
                            self.log_and_display("System", f"Error receiving data (UDP): {e}", "text")
                        break
            except Exception as e:
                self.log_and_display("System", f"Error starting server (UDP): {e}", "text")
                self.server_active = False
                self.update_button_states()
            finally:
                if self.server_socket:
                    self.server_socket.close()
                    self.server_socket = None

    def handle_client_tcp(self, client_socket, addr):
        try:
            x = pyautogui.confirm(f"Accept connection from {addr}?")
            if x != "OK":
                client_socket.close()
                return
            syn = client_socket.recv(4096).decode('utf-8')
            self.log_and_display("Client", f"Received: {syn}", "text")
            client_socket.send("SYN-ACK".encode('utf-8'))
            self.log_and_display("Server", "Sent: SYN-ACK", "text")
            ack = client_socket.recv(4096).decode('utf-8')
            self.log_and_display("Client", f"Received: {ack}", "text")

            while True:
                type_len_data = client_socket.recv(4)
                if not type_len_data:
                    break
                type_len = int.from_bytes(type_len_data, byteorder='big')
                msg_type = client_socket.recv(type_len).decode('utf-8')
                self.log_and_display("System", f"Message type: {msg_type}", "text")

                if msg_type == "TEXT":
                    text_len = int.from_bytes(client_socket.recv(4), byteorder='big')
                    message = client_socket.recv(text_len).decode('utf-8')
                    self.log_and_display("Client", f"Message: {message}", "text")
                    response = f"Received text: {message}"
                    client_socket.sendall(len(response).to_bytes(4, 'big') + response.encode('utf-8'))
                elif msg_type == "FILE":
                    name_len = int.from_bytes(client_socket.recv(4), byteorder='big')
                    file_name = client_socket.recv(name_len).decode('utf-8')
                    received_path = os.path.join("received_files", file_name)
                    try:
                        os.makedirs("received_files", exist_ok=True)
                        print(f"Directory 'received_files' created or already exists")
                    except Exception as e:
                        self.log_and_display("System", f"Error creating directory: {e}", "text")
                        break
                    file_size = int.from_bytes(client_socket.recv(8), byteorder='big')
                    self.log_and_display("Client", f"Receiving file: {file_name} ({file_size} bytes)", "file", file_path=received_path)
                    received = 0
                    with open(received_path, "wb") as f:
                        while received < file_size:
                            data = client_socket.recv(min(4096, file_size - received))
                            if not data:
                                self.log_and_display("System", "Incomplete file data received", "text")
                                break
                            f.write(data)
                            received += len(data)
                            print(f"Received {received}/{file_size} bytes")  # Debugging
                    self.log_and_display("System", f"File saved: {received_path}", "text")
                    response = f"Received file: {file_name} ({received} bytes)"
                    client_socket.sendall(len(response).to_bytes(4, 'big') + response.encode('utf-8'))
        except ConnectionResetError:
            self.log_and_display("System", f"Client {addr} disconnected abruptly", "text")
        except Exception as e:
            self.log_and_display("System", f"TCP Error: {e}", "text")
        finally:
            client_socket.close()
            if client_socket in self.clients:
                self.clients.remove(client_socket)

    def handle_client_udp(self, data, addr):
        try:
            if b'|' in data:
                header, payload = data.split(b'|', 1)
                msg_type = header.decode('utf-8')
                self.log_and_display("System", f"Message type: {msg_type}", "text")

                if msg_type == "TEXT":
                    message = payload.decode('utf-8')
                    self.log_and_display("Client", f"Text: {message}", "text")
                    response = f"Received text: {message}"
                    self.server_socket.sendto(response.encode('utf-8'), addr)
                elif msg_type == "FILE":
                    filename = payload.decode('utf-8')
                    received_path = os.path.join("received_files", filename)
                    try:
                        os.makedirs("received_files", exist_ok=True)
                        print(f"Directory 'received_files' created or already exists")
                    except Exception as e:
                        self.log_and_display("System", f"Error creating directory: {e}", "text")
                        return
                    self.log_and_display("Client", f"Receiving file: {filename}", "file", file_path=received_path)
                    with open(received_path, "wb") as f:
                        self.server_socket.settimeout(5)
                        while True:
                            try:
                                chunk, _ = self.server_socket.recvfrom(4096)
                                if chunk == b"EOF12345":
                                    break
                                f.write(chunk)
                                print(f"Received chunk of size {len(chunk)}")  # Debugging
                            except socket.timeout:
                                self.log_and_display("System", "File transfer timeout", "text")
                                break
                    self.log_and_display("System", f"File saved: {received_path}", "text")
                    response = f"Received file: {filename}"
                    self.server_socket.sendto(response.encode('utf-8'), addr)
                else:
                    self.log_and_display("System", "Invalid message type", "text")
            else:
                self.log_and_display("System", "Invalid message format (missing '|')", "text")
        except socket.timeout:
            self.log_and_display("System", "Timeout waiting for data", "text")
        except Exception as e:
            self.log_and_display("System", f"Error: {e}", "text")
        finally:
            self.server_socket.settimeout(None)

    def log_and_display(self, sender, message, msg_type, file_path=None):
        self.update_signal.emit(sender, message, msg_type, file_path if file_path else "")

    def update_display(self, sender, message, msg_type, file_path):
        frame_color = "#808080" if sender == "Client" else "#55aaff" if sender == "Server" else "#ffaa00"
        alignment = Qt.AlignLeft if sender == "Server" else Qt.AlignRight if sender == "Client" else Qt.AlignCenter

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
    window = Server()
    window.show()
    sys.exit(app.exec_())

