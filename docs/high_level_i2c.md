# Programing devices over I2C

Now that we know how to read and write individual registers we are ready to move up one level and use Python 
language for programming devices using these lower level primitives directly inside _I2C Commander_. 

As before we are working with BMP581 chip. We assume that all registers from the datasheet have already being defined.

According to the datasheet after powering up the chip it is recommended to read several registers and confirm specific 
values. If those values are as per specification, then proceed with temperature and pressure measurements.

* Read `CHIP_ID` register and check that its value is not 0.
* Confirm that in `STATUS` register fields `status_nvm_rdy` and `status_nvm_err` have values 1 and 0 respectively.
* Confirm that in register `INT_STATUS` field `por` is set to 1.

Note that reading `INIT_STATUS` register resets all of its fields to 0. This means that init sequence as outlined above 
can only be run once on freshly powered on BPM581 chip.

Let's create function that performs these checks. First lets switch to the "_User defined commands_" tab.

![](images/user-commands-tab.png)

You will see three main parts. 

* _Commands/Actions_ - this is a list of custom commands defined by the user.
* _Output Console_ - printouts and error messages that would normally be written into a terminal will appear here.
* _Code Preview_ - here you will see the code as you click/select commands in the _Commands/Actions_ list.

Now click on "_Define new command_" button. New window will open where you can enter following

![](images/init-custom-command.png)

Line above, "Init" is a name of custom command as it will appear in the list of commands.
And bellow is the code

```python
if ctx.init_done is not None:
    print("Power-on init sequence was already done once")
    exit()

read(dut.CHIP_ID)
read(dut.STATUS)
read(dut.INT_STATUS)

if dut.CHIP_ID.chip_id == 0:
    print("Init failed. CHIP_ID is 0")

elif dut.STATUS.status_nvm_rdy != 1:
    print(f"Init failed. STATUS.status_nvm_rdy is {dut.STATUS.status_nvm_rdy}")
    
elif dut.STATUS.status_nvm_err != 0:
    print(f"Init failed. STATUS.status_nvm_err is {dut.STATUS.status_nvm_err}")

elif dut.INT_STATUS.por != 1:
    print(f"Init failed. INT_STATUS.por is {dut.INT_STATUS.por}")

else:
    print("Init success")
    ctx.init_done = True
```

This code is plain python but implicitly in it several special functions and objects are available to the user.
Let's go over this code to see what they are.

First we are going to access variable `ctx.init_done` and see if it not `None`. Object `ctx` is global session 
persistent context. You can read and place any variable in it, and it will survive from one invocation of the command 
to the next. Context `ctx` is also shared between commands, which is how you can pass messages from one command to 
another. When you access context variable that is not defined yet, it returns `None`. Variable becomes defined and 
populated by some value when you assign some value to it. At the bottom you can see such 
assignment `ctx.init_done = True`. Thus, the check at the top ensures that init sequence will be run more than once.

Following three lines have form similar to `read(dut.CHIP_ID)`. Object `dut` is implicitly available to the user, 
and it represents access to the _device under test_ (aka _DUT_) and its registers.

Function `read(...)` takes register as an argument and reads that register from the connected chip. After registers are 
read we can access their fields. For example, we can check that `dut.CHIP_ID.chip_id == 0` and so on. 

Now lets click "_Ok_" button. This command should now appear in the list.

![](images/commands-1.png)

Now if you double-click (or click on "_Run command_" button or simply press _Enter_ on the keyboard) on this action,
its code will execute and print `Init success` in _Output Console_. Subsequent calls to this command prints out
`Power-on init sequence was already done once`.