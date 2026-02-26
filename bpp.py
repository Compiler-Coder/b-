#!/usr/bin/env python3
import sys
import re
import time

OPS = {
    "add": 1,
    "subtract": 1,
    "multiply": 2,
    "divide": 2,
}

class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class GUIClosed(Exception):
    pass


class GUIManager:
    def __init__(self):
        try:
            import tkinter as tk
        except Exception as exc:
            raise RuntimeError("GUI support requires tkinter to be available.") from exc
        self.tk = tk
        self.root = None
        self.windows = {}
        self.labels = {}
        self.inputs = {}
        self.buttons = {}
        self.button_flags = {}
        self.closed = False

    def create_window(self, win_id, title, width, height):
        if win_id in self.windows:
            raise ValueError(f"Window '{win_id}' already exists")
        if self.root is None:
            win = self.tk.Tk()
            self.root = win
            win.protocol("WM_DELETE_WINDOW", self._on_close)
        else:
            win = self.tk.Toplevel(self.root)
            win.protocol("WM_DELETE_WINDOW", self._on_close)
        win.title(str(title))
        win.geometry(f"{int(width)}x{int(height)}")
        win.withdraw()
        self.windows[win_id] = win
        self.flush()

    def show_window(self, win_id):
        win = self._get_window(win_id)
        win.deiconify()
        win.lift()
        self.flush()

    def hide_window(self, win_id):
        win = self._get_window(win_id)
        win.withdraw()
        self.flush()

    def add_label(self, win_id, label_id, text):
        if label_id in self.labels:
            raise ValueError(f"Label '{label_id}' already exists")
        parent = self._get_window(win_id)
        label = self.tk.Label(parent, text=str(text))
        label.pack(pady=4)
        self.labels[label_id] = label
        self.flush()

    def add_input(self, win_id, input_id):
        if input_id in self.inputs:
            raise ValueError(f"Input '{input_id}' already exists")
        parent = self._get_window(win_id)
        entry = self.tk.Entry(parent)
        entry.pack(pady=4)
        self.inputs[input_id] = entry
        self.flush()

    def add_button(self, win_id, button_id, text):
        if button_id in self.buttons:
            raise ValueError(f"Button '{button_id}' already exists")
        parent = self._get_window(win_id)
        flag = {"clicked": False}

        def on_click():
            flag["clicked"] = True

        btn = self.tk.Button(parent, text=str(text), command=on_click)
        btn.pack(pady=6)
        self.buttons[button_id] = btn
        self.button_flags[button_id] = flag
        self.flush()

    def set_label(self, label_id, text):
        label = self._get_label(label_id)
        label.config(text=str(text))
        self.flush()

    def read_input(self, input_id):
        entry = self._get_input(input_id)
        value = entry.get()
        if re.fullmatch(r"-?\d+", value):
            return int(value)
        if re.fullmatch(r"-?\d+\.\d+", value):
            return float(value)
        return value

    def wait_for_button(self, button_id):
        if self.root is None:
            raise ValueError("No GUI window has been created")
        if button_id not in self.buttons:
            raise ValueError(f"Unknown button id: {button_id}")
        flag = self.button_flags[button_id]
        flag["clicked"] = False
        while not flag["clicked"]:
            if self.closed:
                raise GUIClosed()
            try:
                self.root.update_idletasks()
                self.root.update()
            except self.tk.TclError as exc:
                self.closed = True
                raise GUIClosed() from exc
            time.sleep(0.01)

    def wait_seconds(self, seconds):
        if self.root is None:
            time.sleep(seconds)
            return
        end = time.monotonic() + seconds
        while True:
            now = time.monotonic()
            if now >= end:
                break
            if self.closed:
                raise GUIClosed()
            self.root.update_idletasks()
            try:
                self.root.update()
            except self.tk.TclError as exc:
                self.closed = True
                raise GUIClosed() from exc
            time.sleep(0.01)

    def flush(self):
        if self.root is None:
            return
        if self.closed:
            raise GUIClosed()
        try:
            self.root.update_idletasks()
            self.root.update()
        except self.tk.TclError as exc:
            self.closed = True
            raise GUIClosed() from exc

    def _get_window(self, win_id):
        if win_id not in self.windows:
            raise ValueError(f"Unknown window id: {win_id}")
        return self.windows[win_id]

    def _get_label(self, label_id):
        if label_id not in self.labels:
            raise ValueError(f"Unknown label id: {label_id}")
        return self.labels[label_id]

    def _get_input(self, input_id):
        if input_id not in self.inputs:
            raise ValueError(f"Unknown input id: {input_id}")
        return self.inputs[input_id]

    def _on_close(self):
        self.closed = True
        if self.root is not None:
            try:
                self.root.destroy()
            except self.tk.TclError:
                pass


def ensure_gui(state):
    if state["gui"] is None:
        state["gui"] = GUIManager()
    return state["gui"]


def tokenize(text):
    parts = re.findall(r'"[^"]*"|\S+', text)
    tokens = []
    for p in parts:
        if p.startswith('"') and p.endswith('"'):
            tokens.append(("str", p[1:-1]))
        else:
            tokens.append(("word", p))
    return tokens


def split_commas(text):
    parts = []
    buf = []
    in_quotes = False
    for ch in text:
        if ch == '"':
            in_quotes = not in_quotes
            buf.append(ch)
            continue
        if ch == ',' and not in_quotes:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def parse_statement(line):
    if line.startswith("function "):
        rest = line[len("function "):].strip()
        if " with " in rest:
            name, params_part = rest.split(" with ", 1)
            params = [p.strip() for p in params_part.split(" and ") if p.strip()]
        else:
            name = rest.strip()
            params = []
        return {"type": "function", "name": name, "params": params, "children": []}

    if line.startswith("set label "):
        m = re.match(r"^set\s+label\s+(\w+)\s+to\s+(.+)$", line)
        if not m:
            raise ValueError(f"Invalid set label statement: {line}")
        parts = split_commas(m.group(2))
        exprs = [tokenize(p) for p in parts if p]
        return {"type": "set_label", "id": m.group(1), "exprs": exprs}

    if line.startswith("set "):
        m = re.match(r"^set\s+(\w+)\s+to\s+(.+)$", line)
        if not m:
            raise ValueError(f"Invalid set statement: {line}")
        return {"type": "set", "name": m.group(1), "expr": tokenize(m.group(2))}

    if line.startswith("change "):
        m = re.match(r"^change\s+(\w+)\s+to\s+(.+)$", line)
        if not m:
            raise ValueError(f"Invalid change statement: {line}")
        return {"type": "change", "name": m.group(1), "expr": tokenize(m.group(2))}

    if line.startswith("give back "):
        return {"type": "return", "expr": tokenize(line[len("give back "):].strip())}

    if line.startswith("ask "):
        m = re.match(r'^ask\s+"([^"]*)"\s+and\s+save\s+it\s+to\s+(\w+)$', line)
        if not m:
            raise ValueError(f"Invalid ask statement: {line}")
        return {"type": "ask", "prompt": m.group(1), "name": m.group(2)}

    if line.startswith("say "):
        parts = split_commas(line[len("say "):])
        exprs = [tokenize(p) for p in parts if p]
        return {"type": "say", "exprs": exprs}

    if line.startswith("add label "):
        m = re.match(r"^add\s+label\s+(\w+)\s+to\s+(\w+)\s+with\s+text\s+(.+)$", line)
        if not m:
            raise ValueError(f"Invalid add label statement: {line}")
        parts = split_commas(m.group(3))
        exprs = [tokenize(p) for p in parts if p]
        return {"type": "add_label", "id": m.group(1), "window": m.group(2), "exprs": exprs}

    if line.startswith("add input "):
        m = re.match(r"^add\s+input\s+(\w+)\s+to\s+(\w+)$", line)
        if not m:
            raise ValueError(f"Invalid add input statement: {line}")
        return {"type": "add_input", "id": m.group(1), "window": m.group(2)}

    if line.startswith("add button "):
        m = re.match(r"^add\s+button\s+(\w+)\s+to\s+(\w+)\s+with\s+text\s+(.+)$", line)
        if not m:
            raise ValueError(f"Invalid add button statement: {line}")
        parts = split_commas(m.group(3))
        exprs = [tokenize(p) for p in parts if p]
        return {"type": "add_button", "id": m.group(1), "window": m.group(2), "exprs": exprs}

    if line.startswith("read input "):
        m = re.match(r"^read\s+input\s+(\w+)\s+and\s+save\s+it\s+to\s+(\w+)$", line)
        if not m:
            raise ValueError(f"Invalid read input statement: {line}")
        return {"type": "read_input", "id": m.group(1), "name": m.group(2)}

    if line.startswith("create window "):
        m = re.match(
            r'^create\s+window\s+(\w+)\s+with\s+title\s+"([^"]*)"\s+and\s+size\s+(.+)\s+by\s+(.+)$',
            line,
        )
        if not m:
            raise ValueError(f"Invalid create window statement: {line}")
        return {
            "type": "create_window",
            "id": m.group(1),
            "title": [("str", m.group(2))],
            "width": tokenize(m.group(3)),
            "height": tokenize(m.group(4)),
        }

    if line.startswith("show "):
        m = re.match(r"^show\s+(\w+)$", line)
        if not m:
            raise ValueError(f"Invalid show statement: {line}")
        return {"type": "show_window", "id": m.group(1)}

    if line.startswith("hide "):
        m = re.match(r"^hide\s+(\w+)$", line)
        if not m:
            raise ValueError(f"Invalid hide statement: {line}")
        return {"type": "hide_window", "id": m.group(1)}

    if line.startswith("wait for button "):
        m = re.match(r"^wait\s+for\s+button\s+(\w+)(?:\s+click)?$", line)
        if not m:
            raise ValueError(f"Invalid wait for button statement: {line}")
        return {"type": "wait_button", "id": m.group(1)}

    if line.startswith("wait "):
        m = re.match(r"^wait\s+(.+)\s+seconds?$", line)
        if not m:
            raise ValueError(f"Invalid wait statement: {line}")
        return {"type": "wait", "duration": tokenize(m.group(1))}

    if line.startswith("if "):
        cond_tokens = tokenize(line[len("if "):].strip())
        return {"type": "if", "cond": cond_tokens, "children": []}

    if line == "otherwise":
        return {"type": "otherwise", "children": []}

    if line.startswith("repeat while "):
        cond_tokens = tokenize(line[len("repeat while "):].strip())
        return {"type": "repeat_while", "cond": cond_tokens, "children": []}

    if line.startswith("repeat ") and line.endswith(" times"):
        count_part = line[len("repeat "):-len(" times")].strip()
        return {"type": "repeat_times", "count": tokenize(count_part), "children": []}

    raise ValueError(f"Unknown statement: {line}")


def parse_lines(lines):
    root = []
    stack = [(0, root)]
    last_node = None

    for raw in lines:
        if raw.strip() == "":
            continue
        if "\t" in raw:
            raise ValueError("Tabs are not allowed. Use spaces for indentation.")
        indent = len(raw) - len(raw.lstrip(" "))
        text = raw.strip()

        if indent > stack[-1][0]:
            if not last_node or "children" not in last_node:
                raise ValueError(f"Unexpected indent: {raw}")
            child_list = []
            last_node["children"] = child_list
            stack.append((indent, child_list))
        elif indent < stack[-1][0]:
            while stack and indent < stack[-1][0]:
                stack.pop()
            if not stack or indent != stack[-1][0]:
                raise ValueError(f"Bad indentation: {raw}")

        node = parse_statement(text)
        stack[-1][1].append(node)
        last_node = node

    return root


def eval_token(tok, env, functions, state):
    ttype, val = tok
    if ttype == "str":
        return val
    if ttype == "word":
        if re.fullmatch(r"-?\d+", val):
            return int(val)
        if re.fullmatch(r"-?\d+\.\d+", val):
            return float(val)
        if val in env:
            return env[val]
        raise ValueError(f"Unknown variable: {val}")
    raise ValueError(f"Bad token: {tok}")


def eval_expr(tokens, env, functions, state):
    if not tokens:
        return None

    # Function call expression: name using arg and arg
    if len(tokens) >= 2 and tokens[0][0] == "word" and tokens[1] == ("word", "using"):
        fname = tokens[0][1]
        arg_tokens = tokens[2:]
        args = []
        current = []
        for tok in arg_tokens:
            if tok == ("word", "and"):
                if current:
                    args.append(current)
                    current = []
            else:
                current.append(tok)
        if current:
            args.append(current)
        arg_values = [eval_expr(a, env, functions, state) for a in args]
        return call_function(fname, arg_values, env, functions, state)

    if len(tokens) == 1:
        return eval_token(tokens[0], env, functions, state)

    # Shunting-yard for simple math
    output = []
    ops = []

    for tok in tokens:
        if tok[0] == "word" and tok[1] in OPS:
            while ops and OPS[ops[-1]] >= OPS[tok[1]]:
                output.append(("op", ops.pop()))
            ops.append(tok[1])
        else:
            output.append(("val", eval_token(tok, env, functions, state)))

    while ops:
        output.append(("op", ops.pop()))

    stack = []
    for kind, val in output:
        if kind == "val":
            stack.append(val)
        else:
            if len(stack) < 2:
                raise ValueError("Invalid expression")
            b = stack.pop()
            a = stack.pop()
            if val == "add":
                stack.append(a + b)
            elif val == "subtract":
                stack.append(a - b)
            elif val == "multiply":
                stack.append(a * b)
            elif val == "divide":
                stack.append(a / b)
    if len(stack) != 1:
        raise ValueError("Invalid expression")
    return stack[0]


def eval_condition(tokens, env, functions, state):
    words = [t[1] if t[0] == "word" else None for t in tokens]
    if "is" not in words:
        raise ValueError("Condition must include 'is'")
    is_idx = words.index("is")

    left_tokens = tokens[:is_idx]
    right_tokens = []

    def match_phrase(phrase):
        if words[is_idx + 1:is_idx + 1 + len(phrase)] == phrase:
            return True
        return False

    if match_phrase(["greater", "than"]):
        right_tokens = tokens[is_idx + 3:]
        return eval_expr(left_tokens, env, functions, state) > eval_expr(right_tokens, env, functions, state)
    if match_phrase(["less", "than"]):
        right_tokens = tokens[is_idx + 3:]
        return eval_expr(left_tokens, env, functions, state) < eval_expr(right_tokens, env, functions, state)
    if match_phrase(["equal", "to"]):
        right_tokens = tokens[is_idx + 3:]
        return eval_expr(left_tokens, env, functions, state) == eval_expr(right_tokens, env, functions, state)
    if match_phrase(["not", "equal", "to"]):
        right_tokens = tokens[is_idx + 4:]
        return eval_expr(left_tokens, env, functions, state) != eval_expr(right_tokens, env, functions, state)

    raise ValueError("Unknown condition")


def call_function(name, args, env, functions, state):
    if name not in functions:
        raise ValueError(f"Unknown function: {name}")
    fn = functions[name]
    params = fn["params"]
    if len(args) != len(params):
        raise ValueError(f"Function '{name}' expects {len(params)} args")
    local_env = dict(env)
    for p, v in zip(params, args):
        local_env[p] = v
    try:
        exec_block(fn["children"], local_env, functions, state)
    except ReturnSignal as rs:
        return rs.value
    return None


def exec_block(stmts, env, functions, state):
    def render_exprs(exprs):
        values = [eval_expr(e, env, functions, state) for e in exprs]
        return " ".join(str(v) for v in values)

    i = 0
    while i < len(stmts):
        if state["gui"] is not None and state["gui"].closed:
            raise GUIClosed()
        stmt = stmts[i]
        stype = stmt["type"]

        if stype == "function":
            functions[stmt["name"]] = stmt
        elif stype == "set":
            env[stmt["name"]] = eval_expr(stmt["expr"], env, functions, state)
        elif stype == "change":
            env[stmt["name"]] = eval_expr(stmt["expr"], env, functions, state)
        elif stype == "ask":
            value = input(stmt["prompt"] + " ")
            if re.fullmatch(r"-?\d+", value):
                value = int(value)
            elif re.fullmatch(r"-?\d+\.\d+", value):
                value = float(value)
            env[stmt["name"]] = value
        elif stype == "say":
            values = [eval_expr(e, env, functions, state) for e in stmt["exprs"]]
            print(*values)
        elif stype == "add_label":
            gui = ensure_gui(state)
            text = render_exprs(stmt["exprs"])
            gui.add_label(stmt["window"], stmt["id"], text)
        elif stype == "add_input":
            gui = ensure_gui(state)
            gui.add_input(stmt["window"], stmt["id"])
        elif stype == "add_button":
            gui = ensure_gui(state)
            text = render_exprs(stmt["exprs"])
            gui.add_button(stmt["window"], stmt["id"], text)
        elif stype == "read_input":
            gui = ensure_gui(state)
            env[stmt["name"]] = gui.read_input(stmt["id"])
        elif stype == "set_label":
            gui = ensure_gui(state)
            text = render_exprs(stmt["exprs"])
            gui.set_label(stmt["id"], text)
        elif stype == "create_window":
            gui = ensure_gui(state)
            title = eval_expr(stmt["title"], env, functions, state)
            width = eval_expr(stmt["width"], env, functions, state)
            height = eval_expr(stmt["height"], env, functions, state)
            gui.create_window(stmt["id"], title, width, height)
        elif stype == "show_window":
            gui = ensure_gui(state)
            gui.show_window(stmt["id"])
        elif stype == "hide_window":
            gui = ensure_gui(state)
            gui.hide_window(stmt["id"])
        elif stype == "wait_button":
            gui = ensure_gui(state)
            gui.wait_for_button(stmt["id"])
        elif stype == "wait":
            duration = eval_expr(stmt["duration"], env, functions, state)
            if duration is None:
                raise ValueError("wait requires a duration")
            duration = float(duration)
            if duration < 0:
                raise ValueError("wait duration must be non-negative")
            if state["gui"] is None:
                time.sleep(duration)
            else:
                state["gui"].wait_seconds(duration)
        elif stype == "if":
            cond = eval_condition(stmt["cond"], env, functions, state)
            if cond:
                exec_block(stmt.get("children", []), env, functions, state)
                if i + 1 < len(stmts) and stmts[i + 1]["type"] == "otherwise":
                    i += 1
            else:
                if i + 1 < len(stmts) and stmts[i + 1]["type"] == "otherwise":
                    exec_block(stmts[i + 1].get("children", []), env, functions, state)
                    i += 1
        elif stype == "otherwise":
            pass
        elif stype == "repeat_times":
            count = eval_expr(stmt["count"], env, functions, state)
            for _ in range(int(count)):
                exec_block(stmt.get("children", []), env, functions, state)
        elif stype == "repeat_while":
            while eval_condition(stmt["cond"], env, functions, state):
                exec_block(stmt.get("children", []), env, functions, state)
        elif stype == "return":
            raise ReturnSignal(eval_expr(stmt["expr"], env, functions, state))
        else:
            raise ValueError(f"Unknown statement type: {stype}")

        i += 1


def run_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    stmts = parse_lines(lines)
    env = {}
    functions = {}
    state = {"gui": None}
    try:
        exec_block(stmts, env, functions, state)
    except GUIClosed:
        return


def is_block_starter(line):
    if line.startswith("function "):
        return True
    if line.startswith("if "):
        return True
    if line == "otherwise":
        return True
    if line.startswith("repeat while "):
        return True
    if line.startswith("repeat ") and line.endswith(" times"):
        return True
    return False


def run_buffer(lines, env, functions, state):
    try:
        stmts = parse_lines([l + "\n" for l in lines])
        exec_block(stmts, env, functions, state)
    except GUIClosed:
        return
    except Exception as exc:
        print(f"Error: {exc}")


def repl():
    print("B++ interactive mode. Type 'exit' or 'quit' to leave.")
    env = {}
    functions = {}
    state = {"gui": None}
    buffer = []
    in_block = False
    while True:
        prompt = "... " if in_block else ">>> "
        try:
            line = input(prompt)
        except EOFError:
            print()
            break

        stripped = line.strip()
        if not in_block and stripped in ("exit", "quit"):
            break

        if stripped == "":
            if buffer:
                run_buffer(buffer, env, functions, state)
                buffer = []
                in_block = False
            continue

        if not in_block:
            if is_block_starter(stripped):
                in_block = True
                buffer.append(line)
            else:
                run_buffer([line], env, functions, state)
        else:
            buffer.append(line)


def main(argv):
    if len(argv) == 1:
        repl()
        return 0
    if len(argv) == 2:
        run_file(argv[1])
        return 0
    print("Usage: bpp.py <file.bpp>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
