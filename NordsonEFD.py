import serial

vlevels = {1:'FATAL',2:'IMPORTANT',3:'INFO',4:'VERBOSE'}
vlevel = 4
def vprint(string, level):
    if level <= vlevel:
        print(f'[{vlevels[level]}] {string}')

def send_write_command(fn):
    '''Function wrapper to handle communication for sending write commands'''
    def dec_outter(fn):
        def dec_inner(self, *args, **kwargs):
            command = fn(self,*args, **kwargs)
            self.send_enq()
            response = self.recieve_packet()  # Read ACK/NAK
            if response == b'\x06':  # ACK
                vprint("ACK received, sending command",4)
                self.send_data(command)
                response = self.recieve_packet()
                if response == self.commands['Success']:
                    vprint("Success Command (A0) recieved",4)
                    self.send_eot()
                    print(f"SENT: {command} Successfully.",4)
                elif response == self.commands['Error']:
                    vprint(f"Error Command (A2) recieved after command: {response}",2)
                    self.send_eot()
                else:
                    vprint(f"Unexpected response after command: {response}",2)
                    self.send_nak()
            else:
                vprint(f"NAK received or no response: {response}",2)
                self.send_nak()
            return command
        return dec_inner
    return dec_outter(fn)

class NordsonEFD:
    def __init__(self, port, baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None

    def open(self):
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            if self.serial_connection.is_open:
                vprint(f"Serial port {self.port} opened successfully.", 2)
            else:
                vprint(f"Failed to open serial port {self.port}.", 1)
        except serial.SerialException as e:
            print(f"Error opening serial port {self.port}: {e}")

    def close(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            vprint(f"Serial port {self.port} closed.",2)

    def send_data(self, data):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.write(data.encode())
            print(f"Sent data: {data}")
        else:
            print("Serial port is not open. Cannot send data.")

    def recieve_packet(self):
        if self.serial_connection and self.serial_connection.is_open:
            packet = self.serial_connection.read_until(b'\x03')  # Read until ETX
            vprint(f"Received packet: {packet}",4)
            return packet
        else:
            vprint("Serial port is not open. Cannot receive packet.",3)
            return None
    
    def send_eot(self):
        eot = b'\x04'  # EOT
        self.send_data(eot)
        vprint("Sent EOT",4)
    
    def send_enq(self):
        enq = b'\x05'  # ENQ
        self.send_data(enq)
        vprint("Sent ENQ",4)

    def send_ack(self):
        ack = b'\x06'  # ACK
        self.send_data(ack)
        vprint("Sent ACK",4)

    def send_nak(self):
        nak = b'\x15'  # NAK
        self.send_data(nak)
        vprint("Sent NAK",4)

    def receive_data(self, size=1024):
        # if self.serial_connection and self.serial_connection.is_open:
        #     data = self.serial_connection.read(size)
        #     print(f"Received data: {data.decode()}")
        #     return data.decode()
        # else:
        #     print("Serial port is not open. Cannot receive data.")
        #     return None
        return b'\x0205D000196\x03'  # Mocked data for testing purposes
    
    commands = {
    'Memory Change': b'CH  ',
    'Timed Mode': b'TT  ',
    'Steady Mode': b'MT  ',
    'Time/Steady Toggle': b'TM  ',
    'Pressure Set': b'PS  ',
    'Vacuum Set': b'VS  ',
    'Time Set': b'DS  ',
    'Pressure Unit Set': b'E6  ',
    'Vacuum Unit Set': b'E7  ',
    'Set the Real Time Clock': b'EB  ',
    'Set the Real Time Date': b'EC  ',
    'Dispense': b'DI  ',
    'Success': b'\x0202A02D\x03',
    'Error': b'\x0202A22B\x03',
    }

    def compute_checksum(self, message_bytes):
        checksum = 0
        for byte in message_bytes:
            # print(hex(byte))
            checksum = checksum - byte
        return bytes(hex(0xFFFF + checksum + 1).upper()[-2:], 'ascii')
    

    def construct_message(self, command, data=""):
        if command in self.commands:
            cmd = self.commands[command]
            num_bytes = bytes(f"{len(cmd) + len(data):02X}","ascii")  # Calculate number of bytes in command + data
            checksum = self.compute_checksum(num_bytes + cmd + bytes(data, 'ascii'))

            message = b'\x02' + num_bytes + cmd + bytes(data, 'ascii') + checksum + b'\x03'  # Append carriage return and newline

            vprint(f"Constructed message: {message}",4)
            vprint(f"Message in raw bytes: {" ".join(f'0x{n:02x}' for n in message)}",4)

            return message
        else:
            raise ValueError("Invalid command")
        
    def read_response(self):
        response = nordson.receive_data()

        # Handle specific responses
        if response == self.commands['Success']:
            print("Success Command (A0) recieved")
            return 'A0', ""
        elif response == self.commands['Error']:
            print("Error Command (A2) recieved")
            return 'A2', ""
        
        if response:
            vprint(f"Response: {response}",4)

            # Check for valid start and end bytes
            if response[0] != 0x02 or response[-1] != 0x03:
                vprint(f"Invalid response format for message {response}.",2)
                return None
            vprint("Valid start and end bytes.",4)

            # Extract and verify checksum
            received_checksum = response[-3:-1]
            recieved_data = response[1:-3]

            calculated_checksum = self.compute_checksum(recieved_data)
            if received_checksum != calculated_checksum:
                vprint("Checksum mismatch.",2)
                return None
            vprint("Checksum valid.",4)
            # return response

            # Extract command and data
            command = response[3:7].decode().strip()
            data = response[7:-3].decode().strip()
            vprint(f"Command: {command}, Data: {data}",4)

            return command, data
        else:
            print("No response received.")
        return

    @send_write_command
    def memory_change(self, memory_location:int):
        """This command changes the selected memory location of the dispenser. The LCD screen will update to the new memory location, 
        including updating the dispense time, pressure, and vacuum parameters.  Client command and data: CH--ccc  ccc: The 3-digit 
        memory location from 0–399. The dispenser will automatically limit the value to prevent any errors."""
        print('IN MEMORY CHANGE')
        if not (0 <= memory_location <= 399):
            raise ValueError("Memory location must be between 0 and 399.")
        data = f"{memory_location:03d}"  # Format as 3-digit string with leading zeros
        message = self.construct_message('Memory Change', data)
        return message

    @send_write_command
    def timed_mode(self):
        """This command switches the dispenser to the Timed mode."""
        message = self.construct_message('Timed Mode')
        return message

    @send_write_command
    def steady_mode(self):
        """This command switches the dispenser to the Steady mode."""
        message = self.construct_message('Steady Mode')
        return message

    @send_write_command
    def time_steady_toggle(self):
        """This command toggles the dispenser between Timed and Steady modes."""
        message = self.construct_message('Time/Steady Toggle')
        return message

    @send_write_command
    def pressure_set(self, pressure_value:int):
        """This command updates the pressure value in the current memory location
        Client command and data: PS--pppp  pppp: The 4-digit pressure setting excluding
        the decimal point. This is a unitless value. The valid pressure ranges and decimal
        point are determined by the pressure units currently selected in the dispenser."""
        if not (0 <= pressure_value <= 6895):
            raise ValueError("Pressure value must be between 0 and 6895 for kPa and Bar, and between 0 and 1000 for psi.")
        data = f"{pressure_value:04d}"  # Format as 4-digit string with leading zeros
        message = self.construct_message('Pressure Set', data)
        return message

    @send_write_command
    def vacuum_set(self, vacuum_value:int):
        """This command updates the vacuum value in the current memory location.  Client
        command and data: VS--vvvv  vvvv: The 4-digit vacuum, setting excluding the decimal
        point. This is a unitless value. The valid vacuum ranges and decimal point are
        determined by the vacuum units currently selected in the dispenser."""
        if not (0 <= vacuum_value <= 448):
            raise ValueError("Vacuum value must be between 0 and 448 for kPa, and lower for H2O and mmHg")
        data = f"{vacuum_value:04d}"  # Format as 4-digit string with leading zeros
        message = self.construct_message('Vacuum Set', data)
        return message

    @send_write_command
    def time_set(self, time_value:float):
        """This command updates the dispense time value in the current memory location.
        Client command and data: DS--Tttttt  ttttt: The 4- or 5-digit dispense
        time value, excluding the decimal point. The valid range is 0.0000 to 9.9999.
        This command accepts either 3 or 4 decimal places.  
        • If a value between 0000 to 9999 is entered, the dispenser will set the 
        dispense time as 0.000 s to 9.999 s.
        
        Hard coded to 5 digits."""
        if not (0.0000 <= time_value <= 9.9999):
            raise ValueError("Time value must be between 0.0000 and 9.9999 seconds.")
        data = f"{int(time_value * 10000):05d}"  # Format as 5-digit string with leading zeros
        message = self.construct_message('Time Set', data)
        return message

    @send_write_command
    def set_real_time_clock(self,hour_format:str,hour:int, minute:int, second:int):
        """This command sets the time for the real time clock on the dispenser. 
        Client command and data: EB--HhhMmmAMa  hh: Hours. 0–23 for 24 hour format,
        1–12 for 12 hour format  mm: Minutes. 0–59  a: Hour format. 0 = AM, 1 = PM, 
        2 = 24 hour format"""
        if hour_format not in ['AM', 'PM', '24']:
            raise ValueError("Hour format must be 'AM', 'PM', or '24'.")
        if hour_format == '24' and not (0 <= hour <= 23):
            raise ValueError("Hour must be between 0 and 23 for 24-hour format.")
        if hour_format in ['AM', 'PM'] and not (1 <= hour <= 12):
            raise ValueError("Hour must be between 1 and 12 for 12-hour format.")
        if not (0 <= minute <= 59):
            raise ValueError("Minute must be between 0 and 59.")
        
        format_code = {'AM': '0', 'PM': '1', '24': '2'}[hour_format]
        data = f"H{hour:02d}M{minute:02d}AM{format_code}"
        message = self.construct_message('Set the Real Time Clock', data)
        return message

    @send_write_command
    def set_real_time_date(self,day:int, month:int, year:int):
        """This command sets the date for the real time clock on the dispenser. 
        Client command and data: EC--MmmDddYyy
        mm: Months. 1–12 
        dd: Days. 1–31 
        yy: Years. 00–99"""
        if not (1 <= month <= 12):
            raise ValueError("Month must be between 1 and 12.")
        if not (1 <= day <= 31):
            raise ValueError("Day must be between 1 and 31.")
        if not (0 <= year <= 99):
            raise ValueError("Year must be between 0 and 99.")
        
        data = f"M{month:02d}D{day:02d}Y{year:02d}"
        message = self.construct_message('Set the Real Time Date', data)
        return message
        
    @send_write_command
    def dispense(self):
        """This command initiates a dispense cycle. If the dispenser is in Timed Mode, it will
        dispense for the duration currently set for the Dispense Time parameter. If the
        dispenser is in Steady Mode, it will begin dispensing. Another dispense command is
        then needed to end the dispense cycle."""
        message = self.construct_message('Dispense')
        return message

if __name__ == "__main__":
    nordson = NordsonEFD('/dev/ttyUSB0', 115200)
    print(nordson.pressure_set(50))