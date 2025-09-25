## Nordson EFD Python RS232 Driver

This repository contains a Python driver for interfacing with Nordson EFD devices via RS232 communication. The driver allows users to control and monitor various Nordson EFD equipment programmatically.

### Features

- Send and receive commands to Nordson EFD devices over RS232
- Easy-to-use Python API for device control
- Support for common Nordson EFD operations (dispense, pressure control, etc.)
- Error handling and checksum implementation
- Cross-platform compatibility (Windows, Linux, macOS)

### Installation

Utilize the NordsonEFD.py file in your project directory. Ensure you have the required dependencies installed.

Can publish to PyPI in the future for easier installation.

### Usage

```python
import NordsonEFD

nordson = NordsonEFD('/dev/ttyUSB0', 115200)

nordson.open()
nordson.pressure_set(50) # Set pressure to 50 psi
```

### Requirements

- Python 3
- pyserial

### License

This project is licensed under the MIT License.