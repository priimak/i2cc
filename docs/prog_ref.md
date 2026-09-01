# Programming language reference

Language used in the code for custom commands is Python 3.13. Below we describe in 
details additional variables, functions and objects available to developer of the 
custom commands that aid access to the I2C devices and their registers.

## Variables

### **\_\_project_name\_\_**
Variable that holds name of the current project. 

### **\_\_command_name\_\_**
Variable that holds name of the command that is executing.

### **\_\_device_address\_\_** 
Integer variable that holds i2c device address as selected in the GUI.

## Objects

### **ctx**

Context object that persists across the project session. Project session refers to a 
time duration when a given project is active. That is for example from the moment
application starts and previously loaded project is loaded again until either application
closes or use opens another project. Context object can be used to store arbitrary 
variables and functions which become available to all defined custom commands. Assigning
arbitrary variable in the context `ctx` creates it and attempts to access variable before it is being 
assigned return `None`.

```python
ctx.OSR = [1, 2, 4, 8, 16, 32, 64]
```

### **dut**

_Device Under Test_ (aka DUT) object that use to access register and theirs field as defined in
the _RegList_. For example

```python
dut.OSR_CONFIG # the whole register
dut.OSR_CONFIG.osr_p # field osr_p in the OSR_CONFIG register
```

Normal register fields are always interpreted as number according the fixed point number 
definition in the register model in RegList. To access raw BitArray for a given field
append `_raw` prefix.

```python
dut.OSR_CONFIG.osr_p_raw # returns raw BitArray object for a field osr_p
```

## Functions & Classes

### **read(...)**

### **write(...)**

### **Variable**

### **prompt_user(...)**
