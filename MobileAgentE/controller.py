import os
import time
import subprocess
from PIL import Image
from time import sleep

def get_screenshot(adb_path):
    command = adb_path + " shell rm /sdcard/screenshot.png"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    time.sleep(0.5)
    command = adb_path + " shell screencap -p /sdcard/screenshot.png"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    time.sleep(0.5)
    command = adb_path + " pull /sdcard/screenshot.png ./screenshot"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    image_path = "./screenshot/screenshot.png"
    save_path = "./screenshot/screenshot.jpg"
    image = Image.open(image_path)
    image.convert("RGB").save(save_path, "JPEG")
    os.remove(image_path)

def start_recording(adb_path):
    print("Remove existing screenrecord.mp4")
    command = adb_path + " shell rm /sdcard/screenrecord.mp4"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    print("Start!")
    # Use subprocess.Popen to allow terminating the recording process later
    command = adb_path + " shell screenrecord /sdcard/screenrecord.mp4"
    process = subprocess.Popen(command, shell=True)
    return process

def end_recording(adb_path, output_recording_path):
    print("正在停止录制...")
    # 发送 SIGINT 信号优雅地停止 screenrecord 进程
    stop_command = adb_path + " shell pkill -SIGINT screenrecord"
    subprocess.run(stop_command, capture_output=True, text=True, shell=True)
    sleep(1)  # 留出一些时间确保录制已停止

    print("正在从设备拉取录制文件...")
    pull_command = f"{adb_path} pull /sdcard/screenrecord.mp4 {output_recording_path}"
    subprocess.run(pull_command, capture_output=True, text=True, shell=True)
    print(f"录制已保存到 {output_recording_path}")


def save_screenshot_to_file(adb_path, file_path="screenshot.png"):
    """
    使用 ADB 从 Android 设备捕获截图，保存到本地，并从设备中删除截图。

    参数:
        adb_path (str): adb 可执行文件的路径。

    返回:
        str: 保存的截图路径，失败时抛出异常。
    """
    # 定义截图的本地文件名
    local_file = file_path

    if os.path.dirname(local_file) != "":
        os.makedirs(os.path.dirname(local_file), exist_ok=True)

    # 定义 Android 设备上的临时文件路径
    device_file = "/sdcard/screenshot.png"
    
    try:
        # print("\tRemoving existing screenshot from the Android device...")
        command = adb_path + " shell rm /sdcard/screenshot.png"
        subprocess.run(command, capture_output=True, text=True, shell=True)
        time.sleep(0.5)

        # Capture the screenshot on the device
        # print("\tCapturing screenshot on the Android device...")
        result = subprocess.run(f"{adb_path} shell screencap -p {device_file}", capture_output=True, text=True, shell=True)
        time.sleep(0.5)
        if result.returncode != 0:
            raise RuntimeError(f"Error: Failed to capture screenshot on the device. {result.stderr}")
        
        # Pull the screenshot to the local computer
        # print("\tTransferring screenshot to local computer...")
        result = subprocess.run(f"{adb_path} pull {device_file} {local_file}", capture_output=True, text=True, shell=True)
        time.sleep(0.5)
        if result.returncode != 0:
            raise RuntimeError(f"Error: Failed to transfer screenshot to local computer. {result.stderr}")
        
        # Remove the screenshot from the device
        # print("\tRemoving screenshot from the Android device...")
        result = subprocess.run(f"{adb_path} shell rm {device_file}", capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            raise RuntimeError(f"Error: Failed to remove screenshot from the device. {result.stderr}")
        
        print(f"\tAtomic Operation Screenshot saved to {local_file}")
        return local_file
    
    except Exception as e:
        print(str(e))
        return None


def tap(adb_path, x, y):
    command = adb_path + f" shell input tap {x} {y}"
    subprocess.run(command, capture_output=True, text=True, shell=True)


def type(adb_path, text):
    text = text.replace("\\n", "_").replace("\n", "_")
    for char in text:
        if char == ' ':
            command = adb_path + f" shell input text %s"
            subprocess.run(command, capture_output=True, text=True, shell=True)
        elif char == '_':
            command = adb_path + f" shell input keyevent 66"
            subprocess.run(command, capture_output=True, text=True, shell=True)
        elif 'a' <= char <= 'z' or 'A' <= char <= 'Z' or char.isdigit():
            command = adb_path + f" shell input text {char}"
            subprocess.run(command, capture_output=True, text=True, shell=True)
        elif char in '-.,!?@\'°/:;()':
            command = adb_path + f" shell input text \"{char}\""
            subprocess.run(command, capture_output=True, text=True, shell=True)
        else:
            command = adb_path + f" shell am broadcast -a ADB_INPUT_TEXT --es msg \"{char}\""
            subprocess.run(command, capture_output=True, text=True, shell=True)

def enter(adb_path):
    command = adb_path + f" shell input keyevent KEYCODE_ENTER"
    subprocess.run(command, capture_output=True, text=True, shell=True)

def swipe(adb_path, x1, y1, x2, y2):
    command = adb_path + f" shell input swipe {x1} {y1} {x2} {y2} 500"
    subprocess.run(command, capture_output=True, text=True, shell=True)


def back(adb_path):
    command = adb_path + f" shell input keyevent 4"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    
    
def home(adb_path):
    # command = adb_path + f" shell am start -a android.intent.action.MAIN -c android.intent.category.HOME"
    command = adb_path + f" shell input keyevent KEYCODE_HOME"
    subprocess.run(command, capture_output=True, text=True, shell=True)

def switch_app(adb_path):
    command = adb_path + f" shell input keyevent KEYCODE_APP_SWITCH"
    subprocess.run(command, capture_output=True, text=True, shell=True)
