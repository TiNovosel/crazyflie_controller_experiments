"""
Simple example that connects to the first Crazyflie found, logs the Stabilizer
and plots it in real-time. After 10s the application disconnects and exits.

This example utilizes the SyncCrazyflie and SyncLogger classes.
"""
import logging
import time
import threading
from collections import deque
import numpy as np

# Set matplotlib backend before importing pyplot
import matplotlib
matplotlib.use('macosx')  # Use macosx backend for better macOS compatibility

import matplotlib.pyplot as plt
import matplotlib.animation as animation

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils import uri_helper

uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

# Data storage for plotting
timestamps = deque(maxlen=1000)
roll_data = deque(maxlen=1000)
pitch_data = deque(maxlen=1000)
yaw_data = deque(maxlen=1000)

# Threading lock for data access
data_lock = threading.Lock()

# Debug counter and control
data_count = 0
running = True

def animate(frame):
    """Animation function for real-time plotting with linear interpolation"""
    global data_count
    with data_lock:
        if len(timestamps) > 2:
            # Convert to relative time in seconds
            start_time = timestamps[0]
            times = np.array([(t - start_time) / 1000.0 for t in timestamps])
            
            # Use all available data for plotting
            times_plot = times
            roll_plot = list(roll_data)
            pitch_plot = list(pitch_data)
            yaw_plot = list(yaw_data)
            
            # Clear previous plots
            ax1.clear()
            ax2.clear()
            ax3.clear()
            
            # Plot roll with interpolation
            ax1.plot(times_plot, roll_plot, 'r-', linewidth=2, alpha=0.8)
            ax1.set_ylabel('Roll (deg)')
            ax1.set_title(f'Real-time Attitude Data (Received: {data_count} points)')
            ax1.grid(True, alpha=0.3)
            
            # Plot pitch with interpolation
            ax2.plot(times_plot, pitch_plot, 'g-', linewidth=2, alpha=0.8)
            ax2.set_ylabel('Pitch (deg)')
            ax2.grid(True, alpha=0.3)
            
            # Plot yaw with interpolation
            ax3.plot(times_plot, yaw_plot, 'b-', linewidth=2, alpha=0.8)
            ax3.set_ylabel('Yaw (deg)')
            ax3.set_xlabel('Time (s)')
            ax3.grid(True, alpha=0.3)
            
            # Set consistent y-axis limits with some margin
            all_data = roll_plot + pitch_plot + yaw_plot
            if all_data:
                y_min, y_max = min(all_data), max(all_data)
                margin = (y_max - y_min) * 0.2 if y_max != y_min else 2
                ax1.set_ylim(y_min - margin, y_max + margin)
                ax2.set_ylim(y_min - margin, y_max + margin)
                ax3.set_ylim(y_min - margin, y_max + margin)
                
            # Set x-axis to show the entire time range
            if len(times_plot) > 0:
                x_min = 0
                x_max = times_plot[-1] + 0.5  # Add small margin at the end
                ax1.set_xlim(x_min, x_max)
                ax2.set_xlim(x_min, x_max)
                ax3.set_xlim(x_min, x_max)
        else:
            # Show placeholder if no data
            ax1.clear()
            ax2.clear()
            ax3.clear()
            
            ax1.text(0.5, 0.5, 'Waiting for data...', ha='center', va='center', transform=ax1.transAxes)
            ax2.text(0.5, 0.5, 'Waiting for data...', ha='center', va='center', transform=ax2.transAxes)
            ax3.text(0.5, 0.5, 'Waiting for data...', ha='center', va='center', transform=ax3.transAxes)
            
            ax1.set_title(f'Real-time Attitude Data (Received: {data_count} points)')
            ax1.set_ylabel('Roll (deg)')
            ax2.set_ylabel('Pitch (deg)')
            ax3.set_ylabel('Yaw (deg)')
            ax3.set_xlabel('Time (s)')
    
    # Force redraw
    fig.canvas.draw()
    fig.canvas.flush_events()

def data_collection_thread():
    """Thread for collecting data from the Crazyflie"""
    global data_count, running
    
    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
    lg_stab.add_variable('stabilizer.roll', 'float')
    lg_stab.add_variable('stabilizer.pitch', 'float')
    lg_stab.add_variable('stabilizer.yaw', 'float')

    cf = Crazyflie(rw_cache='./cache')
    try:
        with SyncCrazyflie(uri, cf=cf) as scf:
            print("Connected to Crazyflie!")
            
            with SyncLogger(scf, lg_stab) as logger:
                endTime = time.time() + 60  # Changed from 10 to 60 seconds

                for log_entry in logger:
                    if not running:
                        break
                        
                    timestamp = log_entry[0]
                    data = log_entry[1]
                    logconf_name = log_entry[2]

                    # Store data for plotting
                    with data_lock:
                        timestamps.append(timestamp)
                        roll_data.append(data['stabilizer.roll'])
                        pitch_data.append(data['stabilizer.pitch'])
                        yaw_data.append(data['stabilizer.yaw'])
                        data_count += 1

                    print(f'[{timestamp}][{logconf_name}]: {data}')

                    if time.time() > endTime:
                        break
    except Exception as e:
        print(f"Error connecting to Crazyflie: {e}")
        print("Check if your drone is powered on and the URI is correct.")

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()
    
    print(f"Trying to connect to: {uri}")
    print("Make sure your Crazyflie is powered on and in range!")

    # Setup matplotlib for real-time plotting
    plt.ion()  # Turn on interactive mode
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8))
    fig.suptitle('Crazyflie Real-time Attitude Data', fontsize=16)
    
    # Setup animation with faster updates
    ani = animation.FuncAnimation(fig, animate, interval=30, blit=False, save_count=100)
    plt.tight_layout()
    
    # Force the window to be visible
    plt.show(block=False)
    plt.pause(0.1)  # Small pause to ensure window is drawn

    # Start data collection in separate thread
    data_thread = threading.Thread(target=data_collection_thread)
    data_thread.start()
    
    try:
        # Keep the main thread alive for plotting
        while running and data_thread.is_alive():
            plt.pause(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
        running = False
    
    # Wait for data thread to finish
    data_thread.join()
    
    # Keep the plot open for a few seconds after logging ends
    print(f"Total data points received: {data_count}")
    time.sleep(3)
    plt.close()