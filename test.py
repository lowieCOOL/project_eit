import serial
import matplotlib.pyplot as plt
import re
import numpy as np
import time

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
    # Create two lines: one for raw data, one for the running average
    line_raw, = ax1.plot([], [], label='Raw Hartslag', alpha=0.5)
    line_avg, = ax1.plot([], [], label=f'Running Avg ({window_size_average})', color='red', linewidth=2)
    line_peak, = ax1.plot([], [], label=f'Peak ({window_size_peak})', color='green', linewidth=2)
    line_threshold, = ax1.plot([], [], label=f'Threshold', color='orange', linewidth=2)
    line_BPM, = ax2.plot([], [], label=f'BPM ({window_size_peak})', color='blue', linewidth=2)

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

    y_data = []
    avg_data = []
    peak_data = []
    BPM_data = []
    threshold_data = []

    detection_factor = 0.7
    on_leading_edge = False
    waiting_above_threshold = False
    last_peak_time = 0
    last_beats = []

    # Example regex to capture the number after 'hartslag:'
    # It looks for 'hartslag:' followed by optional spaces and then digits
    pattern = re.compile(r"hartslag:\s*(\d+)")

    try:
        # Assuming 'ser' is your serial connection object
        # ser = serial.Serial('COM3', 9600) 
        
        while True:
            if ser.in_waiting:
                line_bytes = ser.readline()
                try:
                    line_str = line_bytes.decode('utf-8').strip()
                    
                    # Check for the specific pattern
                    match = pattern.search(line_str)
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

                        # Update plot data for both lines
                        x_axis = range(len(y_data))
                        line_raw.set_data(x_axis, y_data)
                        line_avg.set_data(x_axis, avg_data)
                        line_peak.set_data(x_axis, peak_data)
                        line_BPM.set_data(x_axis, BPM_data)
                        line_threshold.set_data(x_axis, threshold_data)
                        
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