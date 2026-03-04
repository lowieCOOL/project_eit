import serial
import re
import numpy as np
import time
import keyboard

left_held = False
right_held = False
BPM = 0

def init():
    global left_held, right_held, BPM
    ser = serial.Serial(port='COM7', baudrate=9600, timeout=0.5)
    if (ser.is_open):
        print("Connectie geslaagd")

        y_data = []
        avg_data = []
        peak_data = []
        BPM_data = []
        threshold_data = []

        detection_factor = 0.7
        window_size_average = 25  # Number of points to average
        window_size_peak = 25  # Number of points to average
        on_leading_edge = False
        waiting_above_threshold = False
        last_peak_time = 0
        last_beats = []
        
        # Example regex to capture the number after 'hartslag:'
        # It looks for 'hartslag:' followed by optional spaces and then digits
        pattern_hartslag = re.compile(r"hartslag:\s*(\d+)")
        pattern_laser1 = re.compile(r"laser1:\s*(\d+)")
        pattern_laser2 = re.compile(r"laser2:\s*(\d+)")

        def process_heartrate(line_str):
            match = pattern_hartslag.search(line_str)
            if match:
                val = int(match.group(1))
                y_data.append(val)
                
                # Calculate running average
                if len(y_data) >= window_size_average:
                    # Average of the last 'window_size' elements
                    current_avg = np.mean(y_data[-window_size_average:])
                    current_peak = np.max(y_data[-window_size_peak:])
                else:
                    # Average of whatever we have so far
                    current_avg = np.mean(y_data)
                    current_peak = np.max(y_data)
                
                avg_data.append(current_avg)
                peak_data.append(current_peak)

                threshold = (current_peak-current_avg) * detection_factor + current_avg
                threshold_data.append(threshold)

                time_since_last_peak = time.time() - last_peak_time
                if val > threshold:
                    if not waiting_above_threshold and not y_data[-2] - y_data[-1] > 0: # Check for leading edge
                        if on_leading_edge:
                            if time_since_last_peak < 2.5: # Minimum time between peaks (e.g., 500ms)
                                last_beats.append(time_since_last_peak)
                                if len(last_beats) > 5: # Keep only the last 5 beats
                                    last_beats.pop(0)
                            waiting_above_threshold = True
                            last_peak_time = time.time()
                            on_leading_edge = False
                    else:
                        on_leading_edge = True
                else:
                    waiting_above_threshold = False
                    if time_since_last_peak > 2.5: # Reset if too much time has passed without a new peak
                        last_beats = []
                if len(last_beats) > 0:
                    BPM = 60 / np.mean(last_beats) if last_beats else 0
                    BPM_data.append(BPM)
                    print(f"Current BPM: {BPM:.2f}")
                else:
                    BPM_data.append(0)
                return BPM_data[-1]
            return None

        def process_lasers(line_str):
            match1 = pattern_laser1.search(line_str)
            match2 = pattern_laser2.search(line_str)
            laser1_val, laser2_val = 0, 0
            if match1:
                laser1_val = int(match1.group(1))
            if match2:
                laser2_val = int(match2.group(1))
            laser1_pressed, laser2_pressed = False, False
            # print(f"Laser 1: {laser1_val}, Laser 2: {laser2_val}")
            if laser1_val > 150: # Example threshold for laser 1
                laser1_pressed = True
            if laser2_val > 300: # Example threshold for laser 2
                laser2_pressed = True
            # print(f"Laser 1: {'Pressed' if laser1_pressed else 'Not Pressed'}, Laser 2: {'Pressed' if laser2_pressed else 'Not Pressed'}")
            return laser1_pressed, laser2_pressed

        try:
            

            while True:
                if ser.in_waiting:
                    line_bytes = ser.readline()
                    try:
                        line_str = line_bytes.decode('utf-8').strip()
                        #print(line_str)
                        
                        # Check for the specific pattern
                        #process_heartrate(line_str)
                        left_pressed, right_pressed = process_lasers(line_str)

                        if left_pressed and not left_held:
                            keyboard.press('left')
                            left_held = True
                        elif not left_pressed and left_held:
                            keyboard.release('left')
                            left_held = False

                        if right_pressed and not right_held:
                            keyboard.press('right')
                            right_held = True
                        elif not right_pressed and right_held:
                            keyboard.release('right')
                            right_held = False

                    except ValueError:
                        pass # Skip if parsing fails
        except KeyboardInterrupt:
            print("Stopping plot")

        # while True:
        #     data = ser.readline().decode('utf-8')
        #     if data:
        #         print(data)
        #     text_input = input("Voer een commando in (of 'exit' om te stoppen): ")
        #     if text_input.lower() == 'exit':
        #         break
        #     ser.write(f'{text_input}\n'.encode('ascii'))
    else:
        print("Connectie gefaald")

    ser.close()

def getBPM():
    return BPM

def getPresses():
    return left_held, right_held
