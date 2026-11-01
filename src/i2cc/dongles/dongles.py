import i2c_api
import i2c_drivers

SUPPORTED_DONGLES = i2c_api.I2CAPI_IMPL + i2c_drivers.I2CAPI_IMPL
SUPPORTED_DONGLES_DICT = {a.make_and_model(): a for a in SUPPORTED_DONGLES}
