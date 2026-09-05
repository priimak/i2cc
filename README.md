# I2C Commander (I2CC)

GUI for interfacing with I2C devices

For official documentation see this page "[I2C Commander](https://priimak.github.io/i2cc/)".

## Development

```shell
git clone git@github.com:priimak/i2cc.git
cd i2cc/
uv venv -p 3.13
.\.venv\Scripts\activate
uv sync
```

On Linux do `source .venv/bin/activate`

To run _I2C Commander_ 

```shell
uv run i2cc
```