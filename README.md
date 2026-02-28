# B++

B++ is a tiny, English-like programming language designed to be easy to read and write. It uses indentation to define blocks and avoids symbols like `{}` or `;`.

## Language Overview

B++ programs are written as clear sentences. Indentation is the only way to show which lines belong to a block (functions, if/otherwise, and loops).

Example style:

```
function add with one and two
  set result to one add two
  give back result

ask "What is your first number?" and save it to first
ask "What is your second number?" and save it to second
set answer to add using first and second
say "The result is", answer
```

## Syntax Rules

- One instruction per line.
- Blocks are defined only by indentation (2 or 4 spaces, but be consistent).
- Strings are in double quotes.
- `#` starts a comment; everything after it on that line is ignored.
- Variables are words (letters, numbers, underscores).

### Variables

```
set name to "Jim"
change name to "Bob"
```

Supports numbers and text.

Boolean values are also supported with lowercase keywords:

```
set is_ready to true
set is_done to false
```

### Math

Natural math phrasing:

```
set total to one add two
set total to total multiply 5
```

Supported operators: `add`, `subtract`, `multiply`, `divide`.

### Input and Output

```
ask "Question" and save it to variable
say "Text", variable
```

### Timing

```
wait 5 seconds
wait 0.5 seconds
```

Notes:

- `wait` accepts whole numbers or decimals (seconds).

### GUI

```
create window main with title "Title" and size 800 by 600
add label title to main with text "B++ GUI"
add input first to main
add input second to main
add button calculate to main with text "Calculate"
add label result to main with text "Result:"
show main
wait for button calculate click
read input first and save it to one
read input second and save it to two
set answer to one add two
set label result to "Result:", answer
wait 5 seconds
hide main
```

Notes:

- Window ids are single words.
- Use `say` to print instructions in the terminal so users aren't staring at a blank window.

### Functions

```
function greet with name
  say "Hello", name
```

Return values with:

```
give back value
```

Call functions with:

```
set result to add using one and two
```

Built-in functions:

```
set values to list using 10 and 20 and 30
set count to length_of using values
set text_value to to_text using count
set number_value to to_number using "42.5"
set rounded to round_number using 9.876 and 2
```

### Conditions

```
if number is greater than 10
  say "Big"
otherwise if number is equal to 10
  say "Exactly ten"
otherwise
  say "Small"
```

Logical operators in conditions:

```
if is_ready and not is_done
  say "Continue"
```

Supported comparisons: `is greater than`, `is less than`, `is equal to`, `is not equal to`.

### Loops

```
repeat 5 times
  say "Hi"

repeat while number is less than 10
  change number to number add 1

set names to list using "Ana" and "Bo" and "Cy"
repeat for each name in names
  say "Hello", name
```

## How Indentation Defines Blocks

- A block starts on the next line after a statement that introduces a block (`function`, `if`, `otherwise if`, `otherwise`, `repeat`).
- All lines indented more than the introducing line belong to that block.
- When indentation returns to a previous level, the block ends.

## How the Interpreter Reads Code

1. Read the file line by line.
2. Ignore empty lines.
3. Measure indentation for each line.
4. Build a tree of blocks based on indentation changes.
5. Execute the tree from top to bottom.

## How Variables Are Stored

- Variables live in a dictionary (map) of name to value.
- Each function call creates a new local dictionary.
- Locals fall back to globals if a name is missing.

## How Functions Are Called Internally

1. The interpreter stores function definitions in a map of name to block.
2. On `set result to add using one and two`:
   - Evaluate argument expressions.
   - Create a new local scope with parameters bound to values.
   - Run the function block until `give back` is hit.
   - Return the value to the caller.

## Small Example Program

```
function add with one and two
  set result to one add two
  give back result

ask "What is your first number?" and save it to first
ask "What is your second number?" and save it to second
set answer to add using first and second
say "The result is", answer
```

## Building a Simple Interpreter in Python

Keep it small and direct:

1. **Tokenizer**: Split each line into words while keeping quoted strings intact.
2. **Parser**: Use indentation to build a tree of nodes. Each node is a statement with an optional child block.
3. **Evaluator**:
   - Implement handlers for `set`, `change`, `ask`, `say`, `if`, `otherwise`, `repeat`, `function`, and `give back`.
   - Use a dictionary for globals and a stack of dictionaries for locals.
   - Support simple expression parsing for `add`, `subtract`, `multiply`, `divide`.
4. **Runner**: Execute nodes in order, honoring `give back` to exit a function.

## Running B++ Programs

Use the included interpreter:

```
./bpp examples/add_numbers.bpp
```

## Interactive Mode

Run the interpreter without a file to enter interactive mode:

```
./bpp
```

## Install as a Global Command (Linux)

To run `bpp` from anywhere, make the launcher executable and add this repo to your `PATH`:

```
chmod +x /path/to/b++/bpp
echo 'export PATH="/path/to/b++:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

If you use `zsh`, write to `~/.zshrc` instead of `~/.bashrc`.

Notes:

- Use a blank line to execute a multi-line block (like `if`, `repeat`, `function`).
- Type `exit` or `quit` to leave.

## Writing B++ Programs

- Use clear, plain-English sentences.
- Keep indentation consistent.
- One instruction per line.
