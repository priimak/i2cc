import io
import traceback
from contextlib import redirect_stderr, redirect_stdout

from i2c_api import I2CTransactionBuilder
from rgscore import RLinkI2C, S, U
from sprats.collections import Variable

from i2cc.app import App
from i2cc.custom_commands.show_func import mk_show_func
from i2cc.custom_commands.user_prompt import EvalExit, mk_prompt_user
from i2cc.project.project import CustomCommand


class CommandRunner:
    def __init__(self, app: App):
        self.app = app
        link = RLinkI2C(self.app.i2c, self.app.device_address)

        def mk_link_provider(lnk):
            def provider():
                return lnk

            return provider

        def exit_eval():
            raise EvalExit()

        attrs = {}
        for r in self.app.project.reg_list.registers:
            attrs[r.name] = r.mk_embedding_class(mk_link_provider(link), auto_sync=False)()
        dut_cls = type("DUT", (), attrs)
        self.gg = {
            "read": lambda r: r._read(),
            "write": lambda r: r._write(),
            "dut": dut_cls(),
            "ctx": self.app.project.commands_context,
            "i2c": I2CTransactionBuilder(self.app.i2c, default_device_address=self.app.device_address),
            "Variable": Variable,
            "exit": exit_eval,
            "show": mk_show_func(),
            "U": U,
            "S": S,
            "__device_address__": self.app.device_address,
            "__project_name__": self.app.project.name,
        }

    def run_command(self, cmd: CustomCommand):
        try:
            self.gg["__command_name__"] = cmd.label
            self.gg["prompt_user"] = mk_prompt_user(cmd.label)
            out_buffer = io.StringIO()
            try:
                with redirect_stdout(out_buffer), redirect_stderr(out_buffer):
                    eval(cmd.compiled_code, self.gg)
            finally:
                log_str = out_buffer.getvalue().rstrip()
                if log_str != "":
                    self.app.append_custom_commands_log_stdout(log_str)

        except EvalExit:
            pass
        except Exception as ex:
            if isinstance(ex, ValueError):
                self.app.show_error(str(ex))
            else:
                tb_lines = traceback.format_exception(type(ex), ex, ex.__traceback__)
                x = "".join(tb_lines[2:])
                self.app.show_error(str(x))
