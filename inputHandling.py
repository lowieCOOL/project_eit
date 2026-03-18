import serial
import re
import numpy as np
import time
import keyboard

left_held = False
right_held = False
BPM = 0
hoogte = 0
port = 'COM11'  # Update this to your actual port
baudrate = 9600
setpoint = 0

def init(logging=False):
    global left_held, right_held, BPM, hoogte, setpoint
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
    set_setpoint = 0
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
        pattern_hogote = re.compile(r"hoogte:\s*(\d+)")

        def process_heartrate(line_str, on_leading_edge, waiting_above_threshold, last_peak_time, last_beats):
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
                if val > threshold and (peak_data[-1] - avg_data[-1]) > 80: # Check for leading edge
                    if waiting_above_threshold or y_data[-1] - y_data[-2] < 0: # Check for leading edge
                        pass
                        #on_leading_edge = True
                    else:
                        if on_leading_edge:
                            if time_since_last_peak < 2.5: # Minimum time between peaks
                                last_beats.append(time_since_last_peak)
                                if len(last_beats) > 5: # Keep only the last 5 beats
                                    last_beats.pop(0)
                            waiting_above_threshold = True
                            last_peak_time = time.time()
                            on_leading_edge = False
                else:
                    waiting_above_threshold = False
                    on_leading_edge = True
                    if time_since_last_peak > 2.5: # Reset if too much time has passed without a new peak
                        last_beats = []
                    # else:
                    #     if on_leading_edge: # Only count as a beat if we were on a leading edge
                    #         last_beats.append(time_since_last_peak)
                    #         if len(last_beats) > 5: # Keep only the last 5 beats
                    #             last_beats.pop(0)
                    #         last_peak_time = time.time()
                    #         beat_indices.append(len(y_data) - 1)
                    #         beat_values.append(val)
                    #         on_leading_edge = False
                if len(last_beats) > 0:
                    BPM = 60 / np.mean(last_beats) if last_beats else 0
                    BPM_data.append(BPM)
                    # print(f"Current BPM: {BPM:.2f}")
                else:
                    BPM = 0
                    BPM_data.append(0)
                return BPM, on_leading_edge, waiting_above_threshold, last_peak_time, last_beats
            return 0, on_leading_edge, waiting_above_threshold, last_peak_time, last_beats

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
            if laser1_val < 100: # Example threshold for laser 1
                laser1_pressed = True
            if laser2_val < 200: # Example threshold for laser 2
                laser2_pressed = True
            # print(f"Laser 1: {'Pressed' if laser1_pressed else 'Not Pressed'}, Laser 2: {'Pressed' if laser2_pressed else 'Not Pressed'}")
            return laser1_pressed, laser2_pressed
        
        def process_hoogte(line_str):
            match = pattern_hogote.search(line_str)
            if match:
                val = int(match.group(1))
                # print(f"Hoogte: {val}")
                return val
            return 0

        try:
            

            while True:
                if ser.in_waiting:
                    line_bytes = ser.readline()
                    try:
                        line_str = line_bytes.decode('utf-8').strip()
                        #print(line_str)
                        
                        # Check for the specific pattern
                        BPM, on_leading_edge, waiting_above_threshold, last_peak_time, last_beats = process_heartrate(line_str, on_leading_edge, waiting_above_threshold, last_peak_time, last_beats)
                        left_pressed, right_pressed = process_lasers(line_str)
                        temp_hoogte = process_hoogte(line_str)
                        if temp_hoogte > 0:
                            hoogte = temp_hoogte

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

                        if set_setpoint != setpoint:
                            set_setpoint = setpoint
                            ser.write(f's{int(setpoint)}\n'.encode('ascii'))
                            # print(f"Tube setpoint updated to: {setpoint}")

                        if logging:
                            print(f"Heart Rate: {BPM:.2f} BPM, Laser 1: {'Pressed' if left_pressed else 'Not Pressed'}, Laser 2: {'Pressed' if right_pressed else 'Not Pressed'}")

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

def sendSetpoint(value):
    global setpoint
    setpoint = value
    # print(f"Setpoint updated to: {setpoint}")

def getBPM():
    return BPM

def getPresses():
    return left_held, right_held

def getHoogte():
    return hoogte

if __name__ == "__main__":
    init(logging=True)