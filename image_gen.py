import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_environment_map():
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_facecolor('white')

    # 1. Map node numbers to (x, y) coordinates based on the reference image
    # Grid is 5x5. 
    # Col 1 (left) = x=0, Col 5 (right) = x=4
    # Row 1 (bottom) = y=0, Row 5 (top) = y=4
    coords = {}
    for n in range(1, 26):
        x = 4 - ((n - 1) // 5)
        y = (n - 1) % 5
        coords[n] = (x, y)

    # 2. Draw dashed grey grid lines
    for i in range(5):
        ax.plot([0, 4], [i, i], color='lightgray', linestyle='--', linewidth=1, zorder=1) # Horizontal
        ax.plot([i, i], [0, 4], color='lightgray', linestyle='--', linewidth=1, zorder=1) # Vertical

    # 3. Draw the new green path (1 -> 4 -> 19 -> 16 -> 1)
    path_nodes = [1, 4, 19, 16, 1]
    path_x = [coords[n][0] for n in path_nodes]
    path_y = [coords[n][1] for n in path_nodes]
    ax.plot(path_x, path_y, color='lime', linewidth=4, zorder=2)

    # 4. Draw directional arrows alongside the path to indicate traversal (Bold & Red)
    arrow_kwargs = dict(head_width=0.12, head_length=0.18, fc='red', ec='red', linewidth=3, zorder=4)
    # 1 -> 4 (Upward, offset left to be inside the square)
    ax.arrow(3.8, 1.2, 0, 0.6, **arrow_kwargs)
    # 4 -> 19 (Leftward, offset down to be inside the square)
    ax.arrow(2.8, 2.8, -0.6, 0, **arrow_kwargs)
    # 19 -> 16 (Downward, offset right to be inside the square)
    ax.arrow(1.2, 1.8, 0, -0.6, **arrow_kwargs)
    # 16 -> 1 (Rightward, offset up to be inside the square)
    ax.arrow(2.2, 0.2, 0.6, 0, **arrow_kwargs)

    # 5. Draw ArUco Markers and Node Numbers
    for n, (x, y) in coords.items():
        # Generate a stable random 4x4 binary pattern for each ArUco marker
        np.random.seed(n) 
        pattern = np.random.choice([0, 1], size=(4, 4))
        
        # Draw the 4x4 pattern
        ax.imshow(pattern, cmap='gray', extent=[x-0.1, x+0.1, y-0.1, y+0.1], zorder=3, interpolation='nearest')
        
        # Add a thick black border to complete the ArUco look
        border = patches.Rectangle((x-0.12, y-0.12), 0.24, 0.24, linewidth=2, edgecolor='black', facecolor='none', zorder=4)
        ax.add_patch(border)
        
        # Add bold node numbers slightly above the markers
        ax.text(x, y + 0.2, str(n), ha='center', va='bottom', fontweight='bold', fontsize=12, zorder=5)

    # 6. Draw a top-down mobile robot (Differential Drive) at Node 1 (4, 0)
    rx, ry = coords[1]
    
    # Robot Chassis
    chassis = patches.Rectangle((rx - 0.2, ry - 0.3), 0.4, 0.6, facecolor='darkgray', edgecolor='black', linewidth=1.5, zorder=6)
    ax.add_patch(chassis)
    
    # Left Wheel (Shifted rearward to emphasize North direction)
    l_wheel = patches.Rectangle((rx - 0.25, ry - 0.25), 0.05, 0.3, facecolor='black', zorder=7)
    ax.add_patch(l_wheel)
    
    # Right Wheel (Shifted rearward to emphasize North direction)
    r_wheel = patches.Rectangle((rx + 0.2, ry - 0.25), 0.05, 0.3, facecolor='black', zorder=7)
    ax.add_patch(r_wheel)
    
    # LiDAR / Heading indicator (Shifted up to the North edge)
    lidar = patches.Circle((rx, ry + 0.2), 0.08, facecolor='black', zorder=8)
    ax.add_patch(lidar)

    # 7. Add "Start" and "Stop" text at Node 1 (Bold & Red)
    ax.text(rx, ry - 0.45, 'Start', ha='center', va='top', fontweight='bold', color='red', fontsize=14, zorder=9)
    ax.text(rx + 0.35, ry, 'Stop', ha='left', va='center', fontweight='bold', color='red', fontsize=14, zorder=9)

    # 8. Formatting and Export
    ax.set_xlim(-0.5, 5.0) # Expanded slightly to fit the "Stop" text on the right
    ax.set_ylim(-0.8, 4.8)
    ax.axis('off') # Hide standard matplotlib axes

    # Save as high-quality PNG
    plt.savefig('thesis_environment.png', dpi=300, bbox_inches='tight', pad_inches=0.1)
    print("Image successfully generated and saved as 'thesis_environment.png'")

if __name__ == "__main__":
    generate_environment_map()