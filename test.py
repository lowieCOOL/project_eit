import serial
import matplotlib.pyplot as plt
import re
import numpy as np
import time
import keyboard
import scipy

ser = serial.Serial(port='COM7', baudrate=9600, timeout=0.5)
if (ser.is_open):
    print("Connectie geslaagd")
    print(ser.readline().decode('utf-8'))
    ser.write(f's500\n'.encode('ascii'))
    print(ser)

    # Setup the plot
    plt.ion()
    fig, (ax1, ax2) = plt.subplots(2)

    window_size_average = 25  # Number of points to average
    window_size_peak = 25  # Number of points to average
    line_raw, = ax1.plot([], [], label=None, alpha=0.5) #'Raw Hartslag'
    line_avg, = ax1.plot([], [], label=None, color='red', linewidth=2) #f'Running Avg ({window_size_average})'
    line_peak, = ax1.plot([], [], label=None, color='green', linewidth=2) #f'Peak ({window_size_peak})'
    line_threshold, = ax1.plot([], [], label=None, color='orange', linewidth=2) #f'Threshold'
    #line_BPM, = ax2.plot([], [], label=f'BPM ({window_size_peak})', color='blue', linewidth=2)
    beat_scatter = ax1.scatter([], [], color='red', zorder=5, label=None, s=30) #'Beat Detected'

    ax1.set_title("Real-time Hartslag Monitoring")
    ax1.set_xlabel("Sample")
    ax1.set_ylabel("Hartslag")
    ax1.set_ylim(0, 1024)
    ax1.legend()
    ax1.grid(True)

    ax2.set_title("Real-time BPM Monitoring")
    ax2.set_xlabel("Sample")
    ax2.set_ylabel("BPM")
    ax2.set_ylim(0, 200)
    ax2.legend()
    ax2.grid(True)

    time_data = []
    y_data = []
    avg_data = []
    peak_data = []
    BPM_data = []
    threshold_data = []
    beat_indices = []
    beat_values = []

    detection_factor = 0.7
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
        global on_leading_edge, waiting_above_threshold, last_peak_time, last_beats, BPM
        match = pattern_hartslag.search(line_str)
        if match:
            val = int(match.group(1))
            time_data.append(time.time())
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

            if len(y_data) > 10:
                peaks, _ = scipy.signal.find_peaks(y_data, height=threshold, distance=15)
                if len(peaks) > 0:
                    beat_indices.extend(peaks)
                    beat_values.extend([y_data[i] for i in peaks])

            # Update plot data for both lines
            x_axis = range(len(y_data))
            line_raw.set_data(x_axis, y_data)
            line_avg.set_data(x_axis, avg_data)
            line_peak.set_data(x_axis, peak_data)
            #line_BPM.set_data(x_axis, BPM_data)
            line_threshold.set_data(x_axis, threshold_data)
            beat_scatter.set_offsets(np.c_[beat_indices, beat_values] if beat_indices else np.empty((0, 2)))
            
            # Adjust view
            ax1.relim()
            ax1.autoscale_view(scaley=False)
            ax2.relim()
            ax2.autoscale_view(scaley=False)
            
            # Scroll window (show last 50 points)
            if len(y_data) > 50:
                    ax1.set_xlim(len(y_data)-50, len(y_data))
                    ax2.set_xlim(len(y_data)-50, len(y_data))

            plt.pause(0.001)

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
        # Assuming 'ser' is your serial connection object
        # ser = serial.Serial('COM3', 9600) 
        
        left_held = False
        right_held = False

        while True:
            if ser.in_waiting:
                line_bytes = ser.readline()
                try:
                    line_str = line_bytes.decode('utf-8').strip()
                    #print(line_str)
                    
                    # Check for the specific pattern
                    process_heartrate(line_str)
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