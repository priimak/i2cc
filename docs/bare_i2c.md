# Sending and Receiving low level I2C commands.

When you first open _I2CC_, it should look like so:

![](images/default-window.png)

In the lower right corner you can see that I2C dongle is connected on serial port `/dev/ttyUSB0`. If nothing is shown
that means that you do not have dongle connected or recognized by the host computer.

![](images/serial-port-to-dongle.png)

Clicking on _Scan_ button will perform scan for devices on I2C bus at which point they will appear in the dropdown box.

![](images/scan.png)

Application always operates within context of some project. Project **_default_** is, well, the default project. That is
shown in the left lower corner. You can create new project by going to menu "_File_" => "_New Project_".

![](images/where-is-project.png)

Clock speed by default is 100 KHz, but you can select higher value in `Speed` drop down box. Note that at higher speeds
you may need to lower value of the pullup resitor.

![](images/speed-and-pullup.png)

At the device address 0x47 I have
[BMP581](https://www.bosch-sensortec.com/en/products/environmental-sensors/pressure-sensors/bmp581)
temperature and pressure sensor. Register at address 0x1 holds ASCI ID which according the documentation should be
`0b01010000`. So, enter `1` into _Addr:_ field and click `Read Register` or simply press `Enter`. Note, that values in
_Addr:_ field are always interpreted as hexadecimal.

![](images/read-register-input.png)

As a result at the bottom of the window you will exact bits exchanged in the transaction between master and slave.

![](images/read-register-transaction-data.png)

Highlighted in yellow are bits that were sent from master to the slave and in pink from slave to the master. Letters `S`
and `P` represent start and stop condition respectively.
`Sr` is a restart condition. `W` indicates that we are writing to the slave and
`R` that we are reading from the slave device. `Ack` is acknowledgment from either device.

In the left most panel you will see results of reading that register. Both in hex and binary.

![](images/read-register-results.png)

Indeed, you can see that value of this register is `0b01010000` as per the specification for this device.