import json
import mimetypes
import socket
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

# Налаштування констант
HTTP_PORT = 3000
SOCKET_PORT = 5000
SOCKET_HOST = '127.0.0.1'
STORAGE_DIR = Path('storage')
DATA_FILE = STORAGE_DIR / 'data.json'

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url_path = urllib.parse.urlparse(self.path).path
        
        # Маршрутизація сторінок
        if url_path == '/':
            self.send_html_file('index.html')
        elif url_path == '/message.html':
            self.send_html_file('message.html')
        else:
            # Обробка статичних файлів (style.css, logo.png тощо)
            file_path = Path(url_path.lstrip('/'))
            if file_path.exists() and file_path.is_file():
                self.send_static_file(file_path)
            else:
                self.send_html_file('error.html', 404)

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Відправка даних на UDP Socket-сервер
            self.send_to_socket(post_data)
            
            # Перенаправлення назад на сторінку з формою
            self.send_response(302)
            self.send_header('Location', '/message.html')
            self.end_headers()
        else:
            self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

    def send_static_file(self, filepath):
        self.send_response(200)
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type:
            self.send_header('Content-type', mime_type)
        self.end_headers()
        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())

    def send_to_socket(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, (SOCKET_HOST, SOCKET_PORT))

def run_http_server():
    server_address = ('', HTTP_PORT)
    httpd = HTTPServer(server_address, HttpHandler)
    print(f"HTTP сервер запущено на порту {HTTP_PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

def run_socket_server():
    # Створення папки та файлу, якщо їх немає
    STORAGE_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists() or DATA_FILE.stat().st_size == 0:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((SOCKET_HOST, SOCKET_PORT))
        print(f"Socket сервер (UDP) запущено на порту {SOCKET_PORT}...")
        
        while True:
            data, _ = sock.recvfrom(4096)
            parse_and_save_data(data)

def parse_and_save_data(raw_data):
    # Декодування та парсинг даних з форми (url-encoded format)
    decoded_data = urllib.parse.unquote_plus(raw_data.decode('utf-8'))
    data_dict = dict(item.split('=') for item in decoded_data.split('&'))
    
    # Формування нового запису
    timestamp = str(datetime.now())
    new_entry = {
        timestamp: {
            "username": data_dict.get("username", ""),
            "message": data_dict.get("message", "")
        }
    }
    
    # Збереження у JSON файл
    try:
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            file_data = json.load(f)
            file_data.update(new_entry)
            f.seek(0)
            json.dump(file_data, f, ensure_ascii=False, indent=2)
            f.truncate()
    except Exception as e:
        print(f"Помилка запису у файл: {e}")

if __name__ == '__main__':
    # Запуск серверів у різних потоках
    http_thread = Thread(target=run_http_server, daemon=True)
    socket_thread = Thread(target=run_socket_server, daemon=True)
    
    http_thread.start()
    socket_thread.start()
    
    # Очікування завершення (тримає головний потік активним)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nСервери зупинено.")
