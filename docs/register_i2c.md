# Accessing devices using high level register models

Sending low level register read and write commands on I2C bus is useful,
but registers always have clear specifications for their fields and how to 
interpret them. Here is a definition for OSR register for BMP581 chip 

![](images/bmp581-osr-register-spec.png)

Let's define this register in I2CC to enable much higher level access 
to this chip.

But first, since we are dealing with BPM581 chip lets create project specific to this
chip. We do that by going to menu "_File_" => "_Save as Project_".

![](images/save-project-as.png)

This will copy currently opened project under a new name and open it. This will be 
reflected in the project label in the lower left corner.

![](images/new-project-label.png)