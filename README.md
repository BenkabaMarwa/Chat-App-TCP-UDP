# 📡 Chat App (TCP & UDP)

A simple **client-server chat application** built with **Python**, **PyQt5**, and **Sockets**.  
It supports **TCP and UDP communication**, **file transfer**, and a clean **chat-like interface**.

---

## 🚀 Features
- 🔗 **TCP & UDP modes** (selectable from the UI)
- 💬 **Send & receive text messages**
- 📂 **Send & receive files** (images, PDFs, videos, etc.)
- 🎨 **Modern PyQt5 interface** (`scr/TcpUdp.ui`)
- 📁 **Received files saved automatically** in `src/received_files/`

---

## 🛠️ Requirements
- Python **3.x**
- [PyQt5](https://pypi.org/project/PyQt5/)

Install dependencies:
```bash
pip install PyQt5
```

---

▶️ How to Run
1️⃣ Start the Server
```bash
python Server.py
```
2️⃣ Start the Client
```bash
python Client.py
```

3️⃣ Select Protocol

From the dropdown menu, choose TCP or UDP.

4️⃣ Start Chatting

Type and send messages.

Transfer files between client and server.
