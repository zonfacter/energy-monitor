import minimalmodbus
import time
import struct
import sys
import deye
from pathlib import Path

# port name, slave address (in decimal)
inverter = minimalmodbus.Instrument('/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A10MLD05-if00-port0', 1)
inverter.serial.baudrate = 9600
inverter.serial.bytesize = 8
inverter.serial.parity   = minimalmodbus.serial.PARITY_NONE
inverter.serial.stopbits = 1
inverter.mode = minimalmodbus.MODE_RTU
inverter.serial.timeout  = 1
inverter.close_port_after_each_call = True
#inverter.debug = True
#print(inverter)

#start_timestamp = int(time.time())

# Loop over 20 days in hour increments
#for hours in range(0, 20 * 24):  # 20 days, 24 hours each day
#    current_timestamp = start_timestamp + (hours * 60 * 60)  # Adding hour increments to the start timestamp

#    if current_timestamp // (24 * 60 * 60) % 10 == 0:
#        print(f"Hour {hours}: Inside if condition (max = 100)")
#    else:
#        print(f"Hour {hours}: Not inside if condition")
#sys.exit()

year = 23
month = 10
day = 14
hour = 10
minute = 14
second = 0
date = [ year * 256 + month, day * 256 + hour, minute * 256 + second ]

#inverter.write_register(62, year * 256 + month, 0, 16, False)
#inverter.write_register(63, day * 256 + hour, 0, 16, False)
#inverter.write_register(64, minute * 256 + second, 0, 16, False)
#inverter.write_registers(62, date )
#sys.exit()
#inverter.write_register(108, 50, False )

#zero export test
#inverter.write_registers( 104, [ ( 65536 + (-50) ) % 65536 ] )

currentRegister = 100
d = 100
#if ( len(sys.argv) > 1 ):
#	start = int(sys.argv[1])

#date = [ 22 * 256 + 7, 11 * 256 + 5, 17 * 256 + 36 ]
#inverter.write_registers(104, [ 65436 ] )
inverter.write_registers(143, [ 15000 ] )

while currentRegister <= 700:
	# Register number, number of decimals, function code
	data = inverter.read_registers(currentRegister, d, 3)
	n = len(data)
	for i in range(0,n):
		register = i + currentRegister
		raw = data[i]
		val = raw
		hrval = raw
		name = ''
		unit = '  '
		if ( register in deye.ref_registers ):
			r = deye.ref_registers[register]
			name = r[deye.reg_name]
			unit = r[deye.reg_unit]
			if ( r[3] == 's16' ):
				val = raw - ((raw & 0x8000) << 1)
			elif ( r[3] == 'u32' ):
				val = data[i] + (data[i+1] << 16)
			hrval = (val+r[deye.reg_offset]) * r[deye.reg_scale]
		if ( raw > 0 ):
			print( '{register:3n} x{hex:04X} {raw:5n} {val:6n} {hrval:6n} {unit:3} - {name}'.format(register=register,hex=raw,raw=raw,val=val,hrval=hrval,unit=unit,name=name) )

	currentRegister += d
	#sys.exit()
