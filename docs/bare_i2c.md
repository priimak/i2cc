# Sending and Receiving low level I2C commands.

When you first open _I2CC_, it should look like so:

![](images/default-window.png)

In the lower right corner you can see that I2C dongle is connected on serial port `/dev/ttyUSB0`. If nothing 
is shown that means that you do not have dongle connected or recognized by the host computer.

![](images/serial-port-to-dongle.png)

Clicking on _Scan_ button will perform scan for devices on I2C bus at which point they will appear in 
the dropdown box.

![](images/scan.png)

Application operates within context of some project. Project **_default_** is, well, the default project.
That is shown in the left lower corner.

![](images/where-is-project.png)