# Chat App (TCP & UDP)

A simple **client-server chat application** built with **Python**, **PyQt5**, and **Sockets**.  
It supports **TCP and UDP communication**, **file transfer**, and even **text-to-speech (TTS)** playback when hovering over messages.

---

## 🚀 Features
- 🔗 **TCP & UDP modes** (selectable from UI)
- 🤝 **TCP 3-way handshake** (SYN → SYN-ACK → ACK)
- 💬 **Send & receive text messages**
- 📂 **Send & receive files** (images, PDFs, videos)
- 🗣️ **Text-to-speech** on hover (using `pyttsx3`)
- 🎨 **Modern PyQt5 interface** (`Tcp.ui`)
- 📂 **Received files saved automatically** in `received_files/`

---

## 🛠️ Requirements
- Python 3.x
- [PyQt5](https://pypi.org/project/PyQt5/)
- [pyttsx3](https://pypi.org/project/pyttsx3/)
- [pyautogui](https://pypi.org/project/PyAutoGUI/)

Install dependencies:
```bash
pip install PyQt5 pyttsx3 pyautogui


How to Run
1️⃣ Start the Server
python Server.py

2️⃣ Start the Client
python Client.py

3️⃣ Select Protocol

Choose TCP or UDP from the dropdown.

Activate client/server.

Start chatting and transferring files.
