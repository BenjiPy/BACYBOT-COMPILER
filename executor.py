import subprocess
import tempfile
import os
import sys
import io
import threading

restricted_globals = {
    '__builtins__': {
        'print': print,
        'range': range,
        'len': len,
        'int': int,
        'float': float,
        'str': str,
        'bool': bool,
        'dict': dict,
        'list': list,
        'tuple': tuple,
        'set': set,
        'isinstance': isinstance,
        'issubclass': issubclass,
        'abs': abs,
        'sum': sum,
        'min': min,
        'max': max,
        'all': all,
        'any': any,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'sorted': sorted,
        'reversed': reversed,
        'type': type,
        'id': id,
        'dir': dir,
        '__import__': lambda name, globals=None, locals=None, fromlist=(), level=0: __import__(name, globals, locals, fromlist, level) if name not in {'os', 'sys', 'subprocess', 'shutil', 'socket', 'http', 'urllib', 'ftplib', 'popen', 'popen2'} else None,
        'exec': None,
        'eval': None,
        'open': None,
        'compile': None,
    }
}

restricted_locals = {}

def execute_python_code_with_state(code, globals_dict=restricted_globals, locals_dict=restricted_locals):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    new_stdout = io.StringIO()
    new_stderr = io.StringIO()
    sys.stdout = new_stdout
    sys.stderr = new_stderr
    result = ""

    try:
        compiled_code = compile(code, "<string>", "eval")
        result = eval(compiled_code, globals_dict, locals_dict)
        if result is not None:
            result = str(result)
    except SyntaxError:
        try:
            exec(code, globals_dict, locals_dict)
            result = new_stdout.getvalue()
        except Exception as e:
            result = f"Erreur lors de l'exécution du code : {e}"
    except Exception as e:
        result = f"Erreur lors de l'évaluation du code : {e}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return result, new_stderr.getvalue()

def execute_with_timeout(code, timeout=4):
    result = {}
    def target():
        result['output'], result['error'] = execute_python_code_with_state(code)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        return "", "L'exécution du code a dépassé le temps limite de 4 secondes."
    return result.get('output', '') or "", result.get('error', '') or ""

def reset_globals():
    global restricted_globals, restricted_locals
    restricted_globals = {
        '__builtins__': {
            'print': print,
            'range': range,
            'len': len,
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'dict': dict,
            'list': list,
            'tuple': tuple,
            'set': set,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'abs': abs,
            'sum': sum,
            'min': min,
            'max': max,
            'all': all,
            'any': any,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sorted': sorted,
            'reversed': reversed,
            'type': type,
            'id': id,
            'dir': dir,
            '__import__': lambda name, globals=None, locals=None, fromlist=(), level=0: __import__(name, globals, locals, fromlist, level) if name not in {'os', 'sys', 'subprocess', 'shutil', 'socket', 'http', 'urllib', 'ftplib', 'popen', 'popen2'} else None,
            'exec': None,
            'eval': None,
            'open': None,
            'compile': None,
        }
    }
    restricted_locals = {}

reset_globals()

def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    restricted_modules = {'os', 'sys', 'subprocess', 'shutil', 'socket', 'http', 'urllib', 'ftplib', 'popen', 'popen2'}
    if name in restricted_modules:
        raise ImportError(f"Importation du module '{name}' est interdite.")
    return __import__(name, globals, locals, fromlist, level)

def execute_python_code(code):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    new_stdout = io.StringIO()
    new_stderr = io.StringIO()
    sys.stdout = new_stdout
    sys.stderr = new_stderr

    try:
        exec(code, restricted_globals, restricted_locals)
        result = new_stdout.getvalue()
    except Exception as e:
        result = f"Erreur lors de l'exécution du code : {e}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return result

def execute_python_code_with_timeout(code, timeout=5):
    if not os.path.exists('CompilRoom'):
        os.makedirs('CompilRoom')

    with tempfile.NamedTemporaryFile(delete=False, dir='CompilRoom', suffix=".py") as temp_file:
        temp_file.write(code.encode())
        temp_file_path = temp_file.name

    try:
        result = subprocess.run(['python', temp_file_path], capture_output=True, text=True, timeout=timeout)
        stdout_output = result.stdout
        stderr_output = result.stderr
    except subprocess.TimeoutExpired:
        stdout_output = ""
        stderr_output = "L'exécution du code a dépassé le temps limite de 5 secondes."
    except Exception as e:
        stdout_output = ""
        stderr_output = f"Erreur inattendue : {str(e)}"
    finally:
        os.remove(temp_file_path)

    return stdout_output or "", stderr_output or ""

def compile_code_c(code):
    try:
        with open('CompilRoom/temp.c', 'w', encoding='utf-8') as file:
            file.write(code)

        compile_command = ['gcc', '-Wall', '-Wextra', 'CompilRoom/temp.c', '-o', 'CompilRoom/output']
        result = subprocess.run(compile_command, capture_output=True, text=True)
        if result.returncode != 0:
            return None, result.stderr

        if not os.path.exists('CompilRoom/output'):
            return "", "Le fichier compilé 'output' n'existe pas."

        if not os.access('CompilRoom/output', os.X_OK):
            os.chmod('CompilRoom/output', 0o755)

        execute_command = ['./output']
        result_execution = subprocess.run(execute_command, capture_output=True, text=True, cwd='CompilRoom', env={"PATH": "/usr/bin"}, timeout=5)

        return result_execution.stdout or "", result_execution.stderr or ""

    except subprocess.TimeoutExpired:
        return "", "L'exécution du code a dépassé le temps limite de 5 secondes."
    except Exception as e:
        return "", f"Erreur inattendue : {str(e)}"
