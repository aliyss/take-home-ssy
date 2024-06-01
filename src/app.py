import json
import subprocess
import uuid

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


@app.route("/")
def home_page():
    return render_template("home.html")


RESTRICT_IMPORTS_BLOCK = f"""
import builtins

def restrict_imports(allowed_modules):
    original_import = builtins.__import__

    
    def custom_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name not in allowed_modules:
            raise ImportError(f"Import '{{name}}' is not allowed.")
        return original_import(name, globals, locals, fromlist, level)
    
    return custom_import

def run_with_restricted_imports(func, allowed_modules):
    original_import = builtins.__import__
    builtins.__import__ = restrict_imports(allowed_modules)
    
    try:
        result = func()
    finally:
        builtins.__import__ = original_import
    
    return result
"""


RESTRICT_PRINTS_BLOCK = """
import io
from contextlib import redirect_stdout
"""

DEFAULT_IMPORTS = [
    "os",
    "numpy",
    "pandas",
    "json",
]

DEFAULT_DISALLOWED_FUNCTIONS = [
    "exec",
    "eval",
]


class HandledException(Exception):
    def __init__(self, message, description=None, result=None, status_code=400):
        self.message = message
        self.description = description
        self.result = result
        self.status_code = status_code


def get_url_params(request):
    query = request.args.get("imports")
    disallowed = request.args.get("disallowed")
    fastcheck = request.args.get("fastcheck")

    if query:
        query = query.split(",") if query else query
    elif query is not None:
        query = []

    if disallowed:
        disallowed = disallowed.split(",") if disallowed else disallowed
    elif disallowed is not None:
        disallowed = []

    return query, disallowed, fastcheck


def verify_script(data, fastcheck=False):
    script = data.get("script", "")

    if not script:
        raise HandledException("Script not provided.", "User input error.")

    if fastcheck:
        # Check if main function is present
        if "def main():" not in script:
            raise HandledException(
                "Main function not found.", "Main function is required."
            )

    return script.replace("\n", "\n    ")


def handle_lists(default_list, provided_list):
    return default_list if provided_list is None else provided_list


def create_function_blocker_script(script, disallowed_list):
    disallowed = "\n".join([f"    {f} = raise_exception" for f in disallowed_list])

    return f"""
def run():
    def raise_exception(*a):
        raise Exception("Disallowed function called.")

{disallowed}
    {script}
    return main()

"""


def create_import_blocker_script(import_list):
    allowed_imports = "\n".join([f"    import {module}" for module in import_list])

    return f"""
with redirect_stdout(io.StringIO()):
{allowed_imports}
    result = run_with_restricted_imports(run, allowed_modules={import_list})

"""


def create_execution_script(script, disallowed_list, import_list):
    return f"""
{create_function_blocker_script(script, disallowed_list)}

{RESTRICT_PRINTS_BLOCK}
{RESTRICT_IMPORTS_BLOCK}

result = None

{create_import_blocker_script(import_list)}

print(result)
"""


def create_execution_file(query, disallowed, script):
    import_list = handle_lists(DEFAULT_IMPORTS, query)
    disallowed_list = handle_lists(DEFAULT_DISALLOWED_FUNCTIONS, disallowed)

    # Create a unique temporary script file // uuid for future-proofing
    script_filename = f"/tmp/{uuid.uuid4()}.py"
    with open(script_filename, "w") as file:
        try:
            file.write(create_execution_script(script, disallowed_list, import_list))
        except Exception as e:
            raise HandledException(
                "Error writing script to file.", str(e), status_code=500
            )

    return script_filename


def run_nsjail(filename):
    result = subprocess.run(
        [
            "nsjail",
            "-Mo",
            "--config",
            "nsjail.cfg",
            "--",
            "/usr/local/bin/python3",
            filename,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )

    return result


def verify_nsjail_result(result):
    if result.returncode != 0:
        raise HandledException(
            "NSJAIL Error.",
            result.stderr.decode("utf-8"),
            status_code=422,
        )

    # Capture the output
    output = result.stdout.decode("utf-8")

    try:
        # Parse the output as JSON
        return json.loads(output)
    except json.JSONDecodeError as je:
        raise HandledException(
            "Response is not valid JSON.",
            str(je),
            result.stdout.decode("utf-8"),
            status_code=422,
        )


@app.route("/execute", methods=["POST"])
def execute_script():
    try:
        query, disallowed, fastcheck = get_url_params(request)
        data = request.get_json()

        scriptPart = verify_script(data, fastcheck)
        script_filename = create_execution_file(query, disallowed, scriptPart)

        result = run_nsjail(script_filename)
        return jsonify(verify_nsjail_result(result))
    except HandledException as e:
        return (
            jsonify(
                {
                    "error": e.message,
                    "description": e.description,
                    "result": e.result,
                }
            ),
            e.status_code,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, ssl_context="adhoc")
