import numpy as np
from np2srzip.np2srzip import np2srzip

# ---------------- Test Case 1: Small dataset ----------------
num_samples = 100
num_digital = 4
num_analog = 2
samplerate = 500_000
sr_file = "test_case1.sr"

logic = np.random.randint(0, 2, (num_samples, num_digital), dtype=np.uint8)
analog = np.column_stack([
    np.sin(2 * np.pi * 5 * np.linspace(0, 1, num_samples)),
    np.linspace(0, 1, num_samples)
]).astype(np.float32)

np2srzip(
    logic, analog, sr_file, samplerate,
    chunk_size=50,
    digital_names=[f"D{i}" for i in range(num_digital)],
    analog_names=["A0", "A1"]
)

print(f"Test Case 1 saved to {sr_file}")

# ---------------- Test Case 2: Medium dataset with 8 digital, 3 analog ----------------
num_samples = 500
num_digital = 8
num_analog = 3
sr_file = "test_case2.sr"

logic = np.random.randint(0, 2, (num_samples, num_digital), dtype=np.uint8)
analog = np.column_stack([
    np.sin(2 * np.pi * 10 * np.linspace(0, 1, num_samples)),
    np.linspace(-1, 1, num_samples),
    np.random.rand(num_samples)
]).astype(np.float32)

np2srzip(
    logic, analog, sr_file, samplerate,
    chunk_size=200,
    digital_names=[f"D{i}" for i in range(num_digital)],
    analog_names=["V", "I", "Noise"]
)

print(f"Test Case 2 saved to {sr_file}")

# ---------------- Test Case 3: Large dataset with 16 digital, 5 analog ----------------
num_samples = 2000
num_digital = 16
num_analog = 5
sr_file = "test_case3.sr"

logic = np.random.randint(0, 2, (num_samples, num_digital), dtype=np.uint8)
t = np.linspace(0, 1, num_samples)
analog = np.column_stack([
    np.sin(2*np.pi*5*t),
    np.cos(2*np.pi*3*t),
    np.linspace(0, 1, num_samples),
    np.random.rand(num_samples),
    np.sin(2*np.pi*20*t)
]).astype(np.float32)

np2srzip(
    logic, analog, sr_file, samplerate,
    chunk_size=500,
    digital_names=[f"D{i}" for i in range(num_digital)],
    analog_names=["A0","A1","A2","A3","A4"]
)

print(f"Test Case 3 saved to {sr_file}")

# ---------------- Test Case 4: Digital only ----------------
num_samples = 100
num_digital = 6
num_analog = 0
sr_file = "test_case4.sr"

logic = np.random.randint(0, 2, (num_samples, num_digital), dtype=np.uint8)
analog = None

np2srzip(
    logic, analog, sr_file, samplerate,
    chunk_size=50,
    digital_names=[f"D{i}" for i in range(num_digital)],
    analog_names=None
)

print(f"Test Case 4 saved to {sr_file}")

# ---------------- Test Case 5: Analog only ----------------
num_samples = 120
num_digital = 0
num_analog = 2
sr_file = "test_case5.sr"

logic = None
analog = np.column_stack([
    np.linspace(0, 1, num_samples),
    np.sin(2*np.pi*2*np.linspace(0, 1, num_samples))
]).astype(np.float32)

np2srzip(
    logic, analog, sr_file, samplerate,
    chunk_size=60,
    digital_names=None,
    analog_names=["A0","A1"]
)

print(f"Test Case 5 saved to {sr_file}")
