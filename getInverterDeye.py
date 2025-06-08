#!/usr/bin/env python
import minimalmodbus
import time
import struct
import sys
import mysql.connector
import deye
from pathlib import Path

p = Path(__file__).with_name('db.cred')
f = open(p.absolute(), 'r')
cred = f.read().splitlines()

mydb = mysql.connector.connect(
  host=cred[0],
  user=cred[1],
  password=cred[2],
  database=cred[3]
)

mycursor = mydb.cursor()

sql_fields = []
sql_values = []
for register in deye.registers:
	if ( register[deye.reg_log] == 1 ):
		sql_fields.append( ' `' + register[deye.reg_db_field] + '`' )
		sql_values.append( ' %s AS `' + register[deye.reg_db_field] + '`' )

#sqlInsertData = 'INSERT INTO `pv` ( `timestamp`,{fields} ) VALUES ( NOW(6),{values} )'.format(
#		fields=",".join(sql_fields),
#		values=",".join(sql_values)
#	)

sqlInsertData = 'INSERT INTO `pv` ( `timestamp`,`unix_ts`,{fields},`em_frq`,`em_grid_P`,`em_import_E`,`em_export_E` ) SELECT NOW(6),FLOOR(UNIX_TIMESTAMP(NOW(6))*1000),{values},AVG(`frq`) AS `em_frq`,AVG(`P`) AS `em_grid_P`,AVG(`import_E`) AS `em_import_E`,AVG(`export_E`) AS `em_export_E` FROM `log`.`em_wago` WHERE `unix_ts` > %s'.format(
		fields=",".join(sql_fields),
		values=",".join(sql_values)
	)
#print( sqlInsertData )
#sys.exit()

# get last data timestamp
mycursor.execute("SELECT FLOOR(`unix_ts`/1000) FROM `pv` ORDER BY `unix_ts` DESC LIMIT 1")
myresult = mycursor.fetchall()
for x in myresult:
	lastLogTimestamp = x[0]

lastLogTimestamp = float(lastLogTimestamp)
#sys.exit()

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

#zero export power to -100 ((65536 + -100)%65536)
#inverter.write_registers( 104, [ ( 65536 + (-50) ) % 65536 ] )

startTime = time.time()
# avg over samples
samples = 0
errors = 0
lastSocMinReserve = 0
lastBatteryCC = 0
lastMaxOutputPower = 0
while True:
	start = 500
	d = 100
	#if ( len(sys.argv) > 1 ):
	#	start = int(sys.argv[1])

	try:
		for r in deye.registers:
			if ( r[deye.reg_type] == 'bit' ):
				r[deye.reg_value] = 0
		while start < 601:
			# Start register, number, function code
			data = inverter.read_registers(start, d, 3)
			#print(data)
			n = len(data)
			for i in range(0,n):
				j = i + start
				if ( j in deye.ref_registers ):
					r = deye.ref_registers[j]
					if ( r[deye.reg_type] == 's16' ):
						r[deye.reg_value] += (data[i] - ((data[i] & 0x8000) << 1)) + r[deye.reg_offset]
					elif ( r[deye.reg_type] == 'u32' ):
						r[deye.reg_value] += data[i] + (data[i+1] << 16)
					elif ( r[deye.reg_type] == 'v16' ):
						if ( data[i] != 42991 ):
							r[deye.reg_value] += data[i]
					elif ( r[deye.reg_type] == 'bit' ):
						r[deye.reg_value] = data[i]
					else:
						r[deye.reg_value] += data[i]
					# add high word onto lower
					if ( r[deye.reg_log] == 2 ):
						lr = deye.ref_registers[r[deye.reg_db_field]]
						lr[deye.reg_value] += r[deye.reg_scale] * (r[deye.reg_value] + r[deye.reg_offset])

			start += d
		samples += 1
		#register = 1000
		#val = deye.ref_registers[register][deye.reg_value]
		#print( '{register:3n} {val:6n}'.format(register=register,val=val) )

		# log to db
		now = time.time()
		if ( now - startTime > 4.5 ):
			#log null row
			if ( now - lastLogTimestamp > 30 ):
				val = []
				val.append( round( (now + lastLogTimestamp) / 2 ) )
				val.append( round( 1000 * ((now + lastLogTimestamp) / 2) ) )
				mycursor.execute("INSERT INTO `pv` ( `timestamp`, `unix_ts` ) VALUES ( FROM_UNIXTIME(%s), %s )", val)
				mydb.commit()
			
			#toggle gen port 0=generator, 1=smartout, 2=microinverter
			gen = inverter.read_registers(133, 1, 3)
			mycursor.execute("SELECT `elevation` FROM `sun` WHERE `unix_ts` >= UNIX_TIMESTAMP(NOW())*1000 ORDER BY `unix_ts` LIMIT 1;")
			myresult = mycursor.fetchall()
			for x in myresult:
				el = x[0]
				if ( el > 0.0 ):
					if ( gen[0] != 2 ):
						inverter.write_register(133, 2, 0, 16, False)
				else:
					if ( gen[0] != 1 ):
						inverter.write_register(133, 0, 0, 16, False)
			"""
			gen = inverter.read_registers(133, 1, 3)
			if ( ( deye.ref_registers[672][deye.reg_value] / samples ) > 120 or
				 ( deye.ref_registers[673][deye.reg_value] / samples ) > 120 or
				 ( deye.ref_registers[667][deye.reg_value] / samples ) > 20):
				if ( gen[0] != 2 ):
					inverter.write_register(133, 2, 0, 16, False)
			else:
				if ( gen[0] != 1 ):
					inverter.write_register(133, 1, 0, 16, False)
			"""
			
			#adjust battery charge current
			Imin = 10
			Imax = 50
			socMinReserve = 15
			socLow = 30
			socHigh = 75
			socMax = 85
			minSellPower = 0
			batteryFullAge = 10000000
			mycursor.execute("SELECT `batteryImin`, `batteryImax`, `socMinReserve`, `socLow`, `socHigh`, `socMax`, `minSellPower` FROM `pv_values` WHERE `id` = 1 LIMIT 1;")
			myresult = mycursor.fetchall()
			for x in myresult:
				Imin = x[0]
				Imax = x[1]
				socMinReserve = x[2]
				socLow = x[3]
				socHigh = x[4]
				socMax = x[5]
				minSellPower = x[6]

			#every 10 days force fill battery
			mycursor.execute("SELECT ROUND(UNIX_TIMESTAMP(NOW()) - UNIX_TIMESTAMP(`timestamp`)) AS `ageSec` FROM `pv` WHERE `battery_SOC` >= 100 AND `timestamp` <= NOW() - INTERVAL 1 DAY ORDER BY `timestamp` DESC LIMIT 1;")
			myresult = mycursor.fetchall()
			for x in myresult:
				batteryFullAge = x[0]
			if batteryFullAge > (24 * 60 * 60 * 10):
				#print('--100')
				socHigh = 90
				socMax = 100
			#else:
				#print(int(now / (24 * 60 * 60)) % 10)

			cc = Imin

			#soc = deye.ref_registers[588][deye.reg_value] / samples
			data = inverter.read_registers(587, 2, 3)
			batteryV = data[0] / 100.0
			soc = data[1]
			data = inverter.read_registers(653, 1, 3)
			loadpower = data[0]
			data = inverter.read_registers(667, 7, 3)
			pvpower = data[0] + data[5] + data[6]

			if ( soc < 1 ) :
				#just in case something went wrong
				cc = Imin
			elif ( soc < socLow ) :
				#ramp up charge current from 0%soc to socLow from Imin to Imax
				cc = ((Imax - Imin) / socLow) * soc + Imin
			elif ( soc > socMax ) :
				#do not charge at all above socMax
				cc = 0
			elif ( soc > socHigh ) :
				#ramp down charge current from socHigh down to socMax from Imax down to 0
				cc = ( -Imax / ( socMax - socHigh ) ) * soc + Imax / ( 1 - (socHigh / socMax) )
			else :
				cc = Imax

			#adjust for total pvp power
			limitBatteryCharge = (pvpower - loadpower - minSellPower ) / batteryV
			cc = round( min( limitBatteryCharge, cc ) )

			if  ( cc < 0 ) :
				cc = 0
			if  ( cc > Imax ) :
				cc = Imax

			if ( cc > lastBatteryCC ) :
				cc = lastBatteryCC + 2
			if ( cc < lastBatteryCC ) :
				cc = lastBatteryCC - 2

			if ( cc != lastBatteryCC ) :
				#print( '{soc:3n},{batteryV:6f} : {cc:6n} - {pvpower:6n}'.format(soc=soc,batteryV=batteryV,cc=cc,pvpower=pvpower) )
				inverter.write_register(108, cc, False )
				lastBatteryCC = cc

			if ( lastSocMinReserve != socMinReserve ) :
				#print( 'socmin={socMinReserve:3n}'.format(socMinReserve=socMinReserve) )
				inverter.write_register(166, socMinReserve, False )
				inverter.write_register(167, socMinReserve, False )
				inverter.write_register(168, socMinReserve, False )
				inverter.write_register(169, socMinReserve, False )
				inverter.write_register(170, socMinReserve, False )
				inverter.write_register(171, socMinReserve, False )
				lastSocMinReserve = socMinReserve

			#update maxOutputPower
			mycursor.execute("SELECT `maxOutputPower` FROM `pv_values` WHERE `id` = 1 LIMIT 1;")
			myresult = mycursor.fetchall()
			for x in myresult:
				maxOutputPower = x[0]
			
			if ( maxOutputPower != lastMaxOutputPower ) :
				inverter.write_register(143, maxOutputPower, False )
				lastMaxOutputPower = maxOutputPower

			#insert to db
			val = []
			for r in deye.registers:
				if ( r[deye.reg_log] == 1 and r[deye.reg_type] != 'bit' ):
					val.append( round( r[deye.reg_value] / samples ) )
				elif ( r[deye.reg_log] == 1 and r[deye.reg_type] == 'bit' ):
					val.append( r[deye.reg_value] )
				r[deye.reg_value] = 0
			val.append( ( now - 5 ) * 1000 )
			mycursor.execute(sqlInsertData, val)
			mydb.commit()

			lastLogTimestamp = now

			#get inverter datetime
			date = inverter.read_registers(62, 3, 3)
			year = (date[0] >> 8) + 2000
			month = date[0] & 255
			day = (date[1] >> 8)
			hour = date[1] & 255
			minute = (date[2] >> 8)
			second = date[2] & 255

			timeSql = 'UPDATE `pv_values` SET `inverter_timestamp` = "{year}-{month}-{day} {hour}:{minute}:{second}"'.format( year = year, month = month, day = day, hour = hour, minute = minute, second = second)
			mycursor.execute(timeSql)
			mydb.commit()


			samples = 0
			errors = 0
			startTime = time.time()
	except Exception as error:
		#print( "[!] Exception occurred: ", error )
		#cleanup
		startTime = time.time()
		samples = 0
		for r in deye.registers:
			r[deye.reg_value] = 0

		errors += 1
		if ( errors > 100 ):
			print("getInverterDeye: exit, too many errors")
			sys.exit()
		time.sleep(2)

	time.sleep(1)
