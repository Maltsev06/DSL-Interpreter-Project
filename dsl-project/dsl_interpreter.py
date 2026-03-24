import json
import sys
import re

class DSLInterpreter:
    def __init__(self, config):
        self.config = config
        self.context = {}

    def validate_config(self):
        try:
            assert "app" in self.config
            assert "server" in self.config
            assert "features" in self.config
            assert "workflow" in self.config
            steps = self.config["workflow"].get("steps", [])
            assert isinstance(steps, list) and len(steps) >= 8
        except AssertionError:
            raise ValueError("Config missing required blocks or workflow.steps too short")

        # Перевірка типів та значень
        app = self.config["app"]
        if app["env"] not in ["dev", "test", "prod"]:
            raise ValueError("Invalid app.env")
        server = self.config["server"]
        if server["logLevel"] not in ["debug", "info", "warning", "error"]:
            raise ValueError("Invalid server.logLevel")
        if not (1 <= server["port"] <= 65535):
            raise ValueError("Port out of range")

    def resolve(self, val):
        """Підставляє змінні у форматі ${var}."""
        if isinstance(val, str):
            matches = re.findall(r"\$\{([^}]+)\}", val)
            for m in matches:
                parts = m.split(".")
                v = self.context
                for p in parts:
                    if isinstance(v, dict):
                        v = v.get(p)
                    else:
                        v = None
                    if v is None:
                        raise ValueError(f"Variable '{m}' not found")
                val = val.replace(f"${{{m}}}", str(v))
            return val
        return val

    def get_number(self, val):
        val = self.resolve(val)
        if isinstance(val, (int, float)):
            return val
        try:
            return float(val)
        except:
            raise ValueError(f"Expected number, got '{val}'")

    def execute_step(self, step):
        t = step.get("type")
        if t == "print":
            msg = self.resolve(step["message"])
            print(msg)
        elif t == "set":
            self.context[step["var"]] = self.resolve(step["value"])
        elif t == "add":
            a = self.get_number(step["a"])
            b = self.get_number(step["b"])
            self.context[step["var"]] = a + b
        elif t == "multiply":
            a = self.get_number(step["a"])
            b = self.get_number(step["b"])
            self.context[step["var"]] = a * b
        elif t == "if":
            cond = step["condition"]
            left = self.get_number(cond["left"])
            right = self.get_number(cond["right"])
            op = cond["op"]
            result = {
                "==": left == right,
                "!=": left != right,
                ">": left > right,
                ">=": left >= right,
                "<": left < right,
                "<=": left <= right
            }.get(op)
            if result is None:
                raise ValueError(f"Unknown operator '{op}'")
            branch = step["then"] if result else step.get("else", [])
            for s in branch:
                self.execute_step(s)
        elif t == "summary":
            print("--- Summary ---")
            for f in step["fields"]:
                v = self.context.get(f)
                print(f"{f}: {v}")
        else:
            raise ValueError(f"Unknown step type '{t}'")

    def run(self):
        self.validate_config()
        self.context["app"] = self.config["app"]
        self.context["server"] = self.config["server"]
        self.context["features"] = self.config["features"]

        for step in self.config["workflow"]["steps"]:
            self.execute_step(step)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dsl_interpreter.py config.json")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        cfg = json.load(f)
    interpreter = DSLInterpreter(cfg)
    interpreter.run()