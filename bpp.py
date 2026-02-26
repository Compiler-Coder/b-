#!/usr/bin/env python3
import sys
import re

OPS = {
    "add": 1,
    "subtract": 1,
    "multiply": 2,
    "divide": 2,
}

class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


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


def eval_token(tok, env, functions):
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


def eval_expr(tokens, env, functions):
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
        arg_values = [eval_expr(a, env, functions) for a in args]
        return call_function(fname, arg_values, env, functions)

    if len(tokens) == 1:
        return eval_token(tokens[0], env, functions)

    # Shunting-yard for simple math
    output = []
    ops = []

    for tok in tokens:
        if tok[0] == "word" and tok[1] in OPS:
            while ops and OPS[ops[-1]] >= OPS[tok[1]]:
                output.append(("op", ops.pop()))
            ops.append(tok[1])
        else:
            output.append(("val", eval_token(tok, env, functions)))

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


def eval_condition(tokens, env, functions):
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
        return eval_expr(left_tokens, env, functions) > eval_expr(right_tokens, env, functions)
    if match_phrase(["less", "than"]):
        right_tokens = tokens[is_idx + 3:]
        return eval_expr(left_tokens, env, functions) < eval_expr(right_tokens, env, functions)
    if match_phrase(["equal", "to"]):
        right_tokens = tokens[is_idx + 3:]
        return eval_expr(left_tokens, env, functions) == eval_expr(right_tokens, env, functions)
    if match_phrase(["not", "equal", "to"]):
        right_tokens = tokens[is_idx + 4:]
        return eval_expr(left_tokens, env, functions) != eval_expr(right_tokens, env, functions)

    raise ValueError("Unknown condition")


def call_function(name, args, env, functions):
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
        exec_block(fn["children"], local_env, functions)
    except ReturnSignal as rs:
        return rs.value
    return None


def exec_block(stmts, env, functions):
    i = 0
    while i < len(stmts):
        stmt = stmts[i]
        stype = stmt["type"]

        if stype == "function":
            functions[stmt["name"]] = stmt
        elif stype == "set":
            env[stmt["name"]] = eval_expr(stmt["expr"], env, functions)
        elif stype == "change":
            env[stmt["name"]] = eval_expr(stmt["expr"], env, functions)
        elif stype == "ask":
            value = input(stmt["prompt"] + " ")
            if re.fullmatch(r"-?\d+", value):
                value = int(value)
            elif re.fullmatch(r"-?\d+\.\d+", value):
                value = float(value)
            env[stmt["name"]] = value
        elif stype == "say":
            values = [eval_expr(e, env, functions) for e in stmt["exprs"]]
            print(*values)
        elif stype == "if":
            cond = eval_condition(stmt["cond"], env, functions)
            if cond:
                exec_block(stmt.get("children", []), env, functions)
                if i + 1 < len(stmts) and stmts[i + 1]["type"] == "otherwise":
                    i += 1
            else:
                if i + 1 < len(stmts) and stmts[i + 1]["type"] == "otherwise":
                    exec_block(stmts[i + 1].get("children", []), env, functions)
                    i += 1
        elif stype == "otherwise":
            pass
        elif stype == "repeat_times":
            count = eval_expr(stmt["count"], env, functions)
            for _ in range(int(count)):
                exec_block(stmt.get("children", []), env, functions)
        elif stype == "repeat_while":
            while eval_condition(stmt["cond"], env, functions):
                exec_block(stmt.get("children", []), env, functions)
        elif stype == "return":
            raise ReturnSignal(eval_expr(stmt["expr"], env, functions))
        else:
            raise ValueError(f"Unknown statement type: {stype}")

        i += 1


def run_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    stmts = parse_lines(lines)
    env = {}
    functions = {}
    exec_block(stmts, env, functions)


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


def run_buffer(lines, env, functions):
    try:
        stmts = parse_lines([l + "\n" for l in lines])
        exec_block(stmts, env, functions)
    except Exception as exc:
        print(f"Error: {exc}")


def repl():
    print("B++ interactive mode. Type 'exit' or 'quit' to leave.")
    env = {}
    functions = {}
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
                run_buffer(buffer, env, functions)
                buffer = []
                in_block = False
            continue

        if not in_block:
            if is_block_starter(stripped):
                in_block = True
                buffer.append(line)
            else:
                run_buffer([line], env, functions)
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
