import machine
sda = machine.Pin(16)
scl = machine.Pin(17)

i2c = machine.I2C(0, sda=sda, scl=scl)

devices = i2c.scan()

for address in devices:
    try:
        print('Reading from ', address)
        print(i2c.readfrom(address, 4))
    except:
        #print('Failed: ', address)
        pass
    else:
        print('Success: ', address)
