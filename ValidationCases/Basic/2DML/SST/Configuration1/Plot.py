import os
import matplotlib.pyplot as plt
import numpy as np

def main():
    print("[INFO] Running enhanced mock Plot.py with experimental data")

    # Generate synthetic x values
    x = np.linspace(0, 10, 100)

    # Simulated data (e.g., SU2 results)
    simulated = np.sin(x)

    # Experimental data with slight noise
    experimental = np.sin(x) + np.random.normal(0, 0.05, size=x.shape)

    # Plot both
    plt.figure(figsize=(10, 5))
    plt.plot(x, simulated, label="Simulated (SU2)", linestyle='-', color='blue')
    plt.plot(x, experimental, label="Experimental", linestyle='--', color='orange')
    plt.title("Mock Validation: Simulated vs Experimental Data")
    plt.xlabel("x")
    plt.ylabel("Velocity Magnitude")
    plt.legend()
    plt.grid(True)

    # Save plot in 'plots' folder
    output_dir = os.path.join(os.getcwd(), "plots")
    os.makedirs(output_dir, exist_ok=True)

    plot_path = os.path.join(output_dir, "validation_plot.png")
    plt.savefig(plot_path)
    print(f"[INFO] Plot saved to {plot_path}")

if __name__ == "__main__":
    main()
