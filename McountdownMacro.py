import threading
import time
import datetime
import pytz
import FreeSimpleGUI as sg
import pyautogui
import pygetwindow as gw

DEFAULT_TARGET_DATE = "2025-12-25 00:00:00"
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_INTERVAL_SECS = 300

TIMEZONE_LIST = sorted(pytz.all_timezones)

def calculate_pretty_countdown(target_dt, tz_name):
    try:
        tzobj = pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        return "Unknown TZ", -1

    now = datetime.datetime.now(tzobj)
    
    if target_dt.tzinfo is None:
        target_local = tzobj.localize(target_dt)
    else:
        target_local = target_dt.astimezone(tzobj)
        
    delta = target_local - now
    secs = int(delta.total_seconds())
    
    if secs <= 0:
        return "Passed", secs
    
    days = secs // 86400
    hours = (secs % 86400) // 3600
    minutes = (secs % 3600) // 60
    seconds = secs % 60
    
    pretty = f"{days}d {hours}h {minutes}m {seconds}s"
    return pretty, secs

def format_multi_countdown(target_dt, selected_timezones):
    output_parts = []
    
    for tz_name in selected_timezones:
        pretty, secs = calculate_pretty_countdown(target_dt, tz_name)
        
        tz_short = tz_name.split('/')[-1].replace('_', ' ')
        
        if secs > 0:
            output_parts.append(f"({tz_short}: {pretty})")
        
    return " | ".join(output_parts) if output_parts else "Countdown Passed for all zones."

def format_countdown_to_next_send(remaining_seconds):
    
    if remaining_seconds <= 0:
        return "NOW"
    
    secs = remaining_seconds
    
    if secs >= 86400:
        days = secs // 86400
        return f"{days}d {int((secs % 86400) / 3600)}h"
    elif secs >= 3600:
        hours = secs // 3600
        return f"{hours}h {int((secs % 3600) / 60)}m"
    elif secs >= 60:
        minutes = secs // 60
        return f"{minutes}m {secs % 60}s"
    else:
        return f"{secs}s"

def find_and_focus_minecraft(window_title_part="Minecraft"):
    try:
        mc_window = gw.getWindowsWithTitle(window_title_part)
        if not mc_window:
            raise RuntimeError(f"No window found with title containing '{window_title_part}'.")
            
        mc_window[0].activate()
        return True
    except Exception as e:
        return False

next_send_timestamp = 0 

def worker_bot_loop(target_dt, selected_timezones, interval_seconds, enable_movement, custom_message_template):
    global next_send_timestamp
    
    log("Bot thread starting...")
    window_title_part = "Minecraft"

    while not bot_stop.is_set():
        try:
            next_send_timestamp = time.time() + interval_seconds

            if not find_and_focus_minecraft(window_title_part):
                log("Minecraft window not found/focused. Skipping action.")
                time.sleep(5)
                continue

            time_remaining_string = format_multi_countdown(target_dt, selected_timezones)
            next_send_string = format_countdown_to_next_send(interval_seconds) 

            message_template = custom_message_template
            
            message_template = message_template.replace("[remaining time]", time_remaining_string)
            message_template = message_template.replace("[next message]", next_send_string)
                
            message = message_template

            pyautogui.press("t")
            time.sleep(0.2)
            pyautogui.typewrite(message)
            pyautogui.press("enter")
            log(f"Sent chat: {message}")

            if enable_movement:
                time.sleep(1)
                pyautogui.keyDown('w')
                time.sleep(0.5)
                pyautogui.keyUp('w')
                
                pyautogui.keyDown('s')
                time.sleep(0.5)
                pyautogui.keyUp('s')
                log("Performed AFK movement (W/S).")
            else:
                log("AFK movement is disabled.")
            
            sleep_duration = next_send_timestamp - time.time()
            if sleep_duration > 0:
                slept = 0
                while slept < sleep_duration and not bot_stop.is_set():
                    time.sleep(1)
                    slept += 1

        except Exception as ex:
            log("Bot loop error: " + str(ex))
            time.sleep(5)
            
    log("Bot thread stopping.")
    next_send_timestamp = 0

sg.theme("DarkBlue14")

layout = [
    [sg.Text("Minecraft Countdown Macro", font=("Helvetica",16))],
    [sg.Text("This version requires Minecraft to be focused and logged in.")],
    [sg.HorizontalSeparator()],
    [sg.Text("Target Date (YYYY-MM-DD HH:MM:SS)"), 
     sg.Input(DEFAULT_TARGET_DATE, key="-TARGET-", size=(25,1))],
    
    [sg.Text("Timezones (CTRL+Click for multiple)"), 
     sg.Listbox(TIMEZONE_LIST, default_values=[DEFAULT_TIMEZONE], 
                key="-TZ-", size=(30, 8), select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE),
     sg.Column([
         [sg.Text("Interval secs")],
         [sg.Input(DEFAULT_INTERVAL_SECS, key="-INTERVAL-", size=(8,1))]
     ], vertical_alignment='top')],
    
    [sg.Text("Custom Message (Placeholders: [remaining time], [next message])"), 
     sg.Input("It's almost Christmas! [remaining time] left! Next message in: [next message]", key="-CUSTOM_MESSAGE-", size=(60,1))],
    
    [sg.Checkbox("Enable AFK Movement (W/S)", key="-MOVEMENT_TOGGLE-", default=True)],
    [sg.Text("Next message in: "), 
     sg.Text("", key="-NEXT_SEND_TIME-", size=(20,1), font=("Helvetica", 12, "bold"))],
     
    [sg.Button("Start Macro", key="-START-", button_color=('white', 'green')), 
     sg.Button("Stop Macro", key="-STOP-", button_color=('white', 'red')),
     sg.Button("Test Movement", key="-TEST_MOVE-", button_color=('white', 'blue'))],
    [sg.Multiline("", size=(80,12), key="-LOG-", autoscroll=True, disabled=True)]
]

window = sg.Window("MC Countdown Macro — PyAutoGUI", layout, finalize=True)

bot_thread = None
bot_stop = threading.Event()

def log(msg):
    window["-LOG-"].update(msg + "\n", append=True)

while True:
    event, values = window.read(timeout=100) 
    
    if event == sg.WIN_CLOSED:
        bot_stop.set()
        break
        
    if bot_thread and bot_thread.is_alive() and next_send_timestamp > 0:
        time_left = int(next_send_timestamp - time.time())
        formatted_time = format_countdown_to_next_send(max(0, time_left))
        window["-NEXT_SEND_TIME-"].update(formatted_time)
    elif next_send_timestamp == 0:
        window["-NEXT_SEND_TIME-"].update("Stopped")
        
    if event == "-START-":
        if bot_thread and bot_thread.is_alive():
            sg.popup_ok("Bot is already running.")
            continue
            
        date_text = values["-TARGET-"].strip()
        selected_timezones = values["-TZ-"]
        custom_message_template = values["-CUSTOM_MESSAGE-"] 
        
        if not selected_timezones:
            sg.popup("Please select at least one timezone.")
            continue
            
        try:
            interval = int(values["-INTERVAL-"].strip())
        except ValueError:
            sg.popup("Interval must be a whole number.")
            continue
            
        enable_movement = values["-MOVEMENT_TOGGLE-"] 

        try:
            target_dt = datetime.datetime.strptime(date_text, "%Y-%m-%d %H:%M:%S")
        except Exception:
            sg.popup("Invalid date format. Use YYYY-MM-DD HH:MM:SS")
            continue
        
        bot_stop.clear()
        next_send_timestamp = time.time() 
        bot_thread = threading.Thread(target=worker_bot_loop, 
                                      args=(target_dt, selected_timezones, interval, enable_movement, custom_message_template), 
                                      daemon=True)
        bot_thread.start()
        log("Macro started. Ensure Minecraft window is visible and active!")

    if event == "-STOP-":
        bot_stop.set()
        log("Stop requested for macro.")

    if event == "-TEST_MOVE-":
        if find_and_focus_minecraft():
            pyautogui.keyDown('w')
            time.sleep(0.5)
            pyautogui.keyUp('w')
            pyautogui.keyDown('s')
            time.sleep(0.5)
            pyautogui.keyUp('s')
            log("Test movement (W/S) successful.")
        else:
            sg.popup("Failed to find or focus Minecraft window. Check your title!")

window.close()
