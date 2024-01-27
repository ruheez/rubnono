import concurrent.futures
import subprocess
import time
import ipaddress

COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"

MAX_RETRIES = 3


def reconnect(ip):
  disconnect_command = ["adb", "disconnect", f"{ip}:5555"]
  subprocess.run(disconnect_command,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE)

  retries = 0
  while retries < MAX_RETRIES:
    connect_command = ["adb", "connect", f"{ip}:5555"]
    result = subprocess.run(connect_command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode == 0:
      break
    else:
      retries += 1
      print(f"การเชื่อมต่อล้มเหลว. กำลังลองใหม่... ({retries}/{MAX_RETRIES})")
      time.sleep(2)  # รอเวลาสักครู่ก่อนลองใหม่

  if retries == MAX_RETRIES:
    print(
        f"{COLOR_RED}เกิดข้อผิดพลาดในการเชื่อมต่อ {ip} ไปยัง ADB{COLOR_RESET}")


def execute_adb_command(ip):
  reconnect(ip)

  adb_command_open_browser = [
      "adb", "-s", f"{ip}:5555", "shell", "am", "start", "-a",
      "android.intent.action.VIEW", "-d", "https://movievip.pages.dev/home"
  ]

  try:
    subprocess.run(adb_command_open_browser, check=True)
    print(f"{COLOR_CYAN}Successfully opened browser for {ip}{COLOR_RESET}")
    print(f"{COLOR_CYAN}Starting: {adb_command_open_browser}{COLOR_RESET}")

    time.sleep(5)  # รอเวลา 5 วินาทีหลังจากเปิดบราวเซอร์

    # ดึงข้อมูลขนาดจอ (screen dimensions)
    adb_command_get_screen_size = [
        "adb", "-s", f"{ip}:5555", "shell", "wm", "size"
    ]
    result = subprocess.run(adb_command_get_screen_size,
                            stdout=subprocess.PIPE)
    screen_size = result.stdout.decode("utf-8").strip().split()[-1]
    screen_width, screen_height = map(int, screen_size.split("x"))

    # คำนวณตำแหน่ง x, y ที่กลางจอ
    center_x = screen_width // 2
    center_y = screen_height // 2

    adb_command_click_center = [
        "adb", "-s", f"{ip}:5555", "shell", "input", "tap",
        str(center_x),
        str(center_y)
    ]

    # คลิกที่กลางจอ
    subprocess.run(adb_command_click_center, check=True)
    print(f"{COLOR_GREEN}Successfully clicked center for {ip}{COLOR_RESET}")
    print(f"{COLOR_CYAN}Starting: {adb_command_click_center}{COLOR_RESET}")

  except subprocess.CalledProcessError as e:
    print(f"{COLOR_RED}Error executing command for {ip}: {e}{COLOR_RESET}")


def connect_to_adb(ip_group):
  with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(execute_adb_command, ip) for ip in ip_group]

    for future in concurrent.futures.as_completed(futures):
      try:
        future.result()
      except Exception as e:
        print(f"{COLOR_RED}Error in connect_to_adb: {e}{COLOR_RESET}")


def load_ips(file_path):
  with open(file_path, 'r') as file:
    ips = [line.strip() for line in file.readlines()]

  formatted_ips = []
  for ip in ips:
    if '/' in ip:  # ตรวจสอบว่าไอพีเป็น CIDR หรือไม่
      ip_network = ipaddress.IPv4Network(ip, strict=False)
      formatted_ips.extend([str(ip) for ip in ip_network.hosts()])
    elif '-' in ip:
      start_ip, end_ip = ip.split('-')
      # แยกช่วงไอพีเป็นไอพีเริ่มต้นและสิ้นสุด
      start_ip_obj = ipaddress.IPv4Address(start_ip)
      end_ip_obj = ipaddress.IPv4Address(end_ip)
      # เพิ่มไอพีทุกตัวในช่วงไปยังลิสต์
      current_ip_obj = start_ip_obj
      while current_ip_obj <= end_ip_obj:
        formatted_ips.append(str(current_ip_obj))
        current_ip_obj += 1
    else:
      formatted_ips.append(ip)

  return formatted_ips


def main():
  ip_files = ['IP.txt']

  all_ips = []
  for ip_file in ip_files:
    ips = load_ips(ip_file)
    all_ips.extend(ips)

  grouped_ips = [all_ips[i:i + 2000] for i in range(0, len(all_ips), 2000)]

  with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(connect_to_adb, ip_group) for ip_group in grouped_ips
    ]

    for future in concurrent.futures.as_completed(futures):
      future.result()


if __name__ == '__main__':
  main()
