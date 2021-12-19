import PySimpleGUI as sg

import os
import psutil
import subprocess
import sys
import threading

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def wget_thread(window: sg.Window, sp: subprocess.Popen, tnum: int):
    global running
    running = True
    for line in sp.stdout:
        oline = line.decode().rstrip()
        print(line)
        window.write_event_value('-WGET-THREAD-OUT-', oline)
        if running == False:
            kill(sp.pid)
            break
    if running:
        window.write_event_value('-WGET-THREAD-DONE-', f'==== THEAD {tnum} DONE ====')
    else:
        window.write_event_value('-WGET-THREAD-KILLED-', f'==== THEAD {tnum} KILLED ====')
        
def fetch_next_url(curr):
    url = urls[curr].strip()
    if 'Single' in values['-MODE-']:
        args = []
    else:
        args = ['-r']
    args = args + ['--no-cookies', '--adjust-extension', '-v', '-H', '-E', '-k', '-K', '-p',
                   '-N', '-np', '-e robots=off', '--html-extension', f'-P {values["-OUTPUT-DIR-"]}']
    args = [wget] + args + [f'"{url}"']
    print(args)
    window['-OUT-'].print(f'==== Starting {urls[curr]} ====')
    sp = sg.execute_command_subprocess(args[0], *args[1:], wait=False, stdin=subprocess.PIPE, pipe_output=True, merge_stderr_with_stdout=True)
    threading.Thread(target=wget_thread, args=(window, sp, curr), daemon=True).start()

layout = [
    [sg.Text('Starter URLs, one per line')],
    [sg.Multiline(expand_x=True, expand_y=True, key='-URLS-')],
    [sg.Text('Mode:'), sg.Combo(('Single page(s)', 'Recursively spider site(s)'), default_value='Single page(s)', key='-MODE-', readonly=True)],
    [sg.Text('Output folder:'), sg.Input('C:/Temp', key='-OUTPUT-DIR-'), sg.FolderBrowse(initial_folder='C:/Temp')],
    [sg.Multiline(size=120, expand_x=True, expand_y=True, key='-OUT-')],
    [sg.Button('RUN', key='-RUN-', button_color='white on red'), sg.Text(key='-FILE-', expand_x=True, justification='left'), sg.Push()]
]

window = sg.Window('GUI for wget', layout, finalize=True, resizable=True, size=(800, 400))
wget = resource_path('wget.exe')
curr_url = -1
urls = []
count = 0
running = False

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    if (event == '-RUN-') and (curr_url == -1):
        # Start from beginning of list
        window['-OUT-'].update('')
        urls = values['-URLS-'].replace('\n\n', '\n').split('\n')
        count = len(urls)
        os.chdir(values['-OUTPUT-DIR-'])
        curr_url = 0
        sg.one_line_progress_meter("Progress on starter URLs...", 0, count, keep_on_top=True)
        window['-RUN-'].update('STOP')
        fetch_next_url(curr_url)
    elif (event == '-RUN-') and (curr_url >= 0):
        # Stop button pressed while running
        window['-OUT-'].print(f'\n==== Stopping fetching process ====\n', colors='red on white')
        sg.one_line_progress_meter_cancel()
        running = False
        curr_url = -1
    elif event == '-WGET-THREAD-OUT-':
        # Show something is happening
        if running:
            if not sg.one_line_progress_meter("Progress on starter URL list...", curr_url, count, keep_on_top=True):
                # Cancel button pressed while running
                window['-OUT-'].print(f'\n==== Stopping fetching process ====\n', colors='red on white')
                running = False
                curr_url = -1
            else:
                line = values['-WGET-THREAD-OUT-']
                if 'Saving to' in line:
                    # Show current file being saved
                    window['-FILE-'].update(line)
    elif event == '-WGET-THREAD-DONE-':
        window['-OUT-'].print(f'==== Finished {urls[curr_url]} ====')
        curr_url += 1
        if (curr_url < count) and running:
            # Part way through list so start next one
            fetch_next_url(curr_url)
        else:
            window['-OUT-'].print(f'==== Finished all URLs ====')
            sg.one_line_progress_meter_cancel()
            curr_url = -1
            window['-RUN-'].update('RUN')
            window['-FILE-'].update('')
            running = False
    elif event == '-WGET-THREAD-KILLED-':
        window['-OUT-'].print(f'==== Stopped fetching all URLs ====')
        curr_url = -1
        window['-RUN-'].update('RUN')
        window['-FILE-'].update('')
        running = False

window.close()
