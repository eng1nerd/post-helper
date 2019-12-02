import os
import subprocess
import sys

from pynt import task
from pyntcontrib import execute, safe_cd

PACKAGE_NAME = "jekyll_post_helper"
PIPENV = "pipenv run"
SRC = "."
PYTHON = "python3.8"
IS_DJANGO = False
IS_ACTIONS = "GH_ACTIONS" in os.environ
if IS_ACTIONS:
    PIPENV = ""
else:
    PIPENV = "pipenv run"

MAC_LIBS = ":"
BUILD_SERVER_LIBS = ":"

sys.path.append(os.path.join(os.path.dirname(__file__), "."))
from build_utils import check_is_aws, execute_get_text, execute_with_environment, is_it_worse, skip_if_no_change, timed

CURRENT_HASH = None

if check_is_aws():
    MAC_LIBS += BUILD_SERVER_LIBS


@task()
@skip_if_no_change("clean_state")
@timed()
def clean_state():
    with safe_cd(".build_state"):
        # wild cards don't expand by default
        for file in os.listdir("."):
            if file.startswith("last") and file.endswith(".txt"):
                execute("rm", "-f", str(file))


@task()
@skip_if_no_change("formatting")
@timed()
def formatting():
    max_length = "120"
    with safe_cd(SRC):
        execute(*("{0} black -l {1} {2}".format(PIPENV, max_length, PACKAGE_NAME).split(" ")))


@task(formatting)
@skip_if_no_change("compile_py")
@timed()
def compile_py():
    with safe_cd(SRC):
        execute(PYTHON, "-m", "compileall", PACKAGE_NAME)


@task(compile_py)
@skip_if_no_change("lint", expect_files="lint.txt")
@timed()
def lint():
    with safe_cd(SRC):
        if os.path.isfile("lint.txt"):
            execute("rm", "lint.txt")
    with safe_cd(SRC):
        # so that pylint doesn't stop us with a bad return value

        if IS_DJANGO:
            django_bits = " --load-plugins pylint_django"
        else:
            django_bits = ""

        command = "{0} pylint{1} --rcfile=pylintrc {2}".format(PIPENV, django_bits, PACKAGE_NAME).strip()
        print(command)
        command = command.split(" ")

        # keep out of src tree, causes extraneous change detections
        lint_output_file_name = "lint.txt"
        with open(lint_output_file_name, "w") as outfile:
            # Ths is set up to supress lint failing on even 1 line of lint.
            # but that doesn't distinguish betweet lint or ImportErrors!
            my_env = config_pythonpath()
            # subprocess.run(command, stdout=outfile, env=my_env, timeout=120)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, env=my_env)
            for line in iter(process.stdout.readline, b""):  # replace '' with b'' for Python 3
                if b"memoize.py" in line:
                    continue
                sys.stdout.write(line.decode())
                outfile.write(line.decode())

        fatal_errors = sum(
            1
            for line in open(lint_output_file_name)
            if "no-member" in line or "no-name-in-module" in line or "import-error" in line
        )

        if fatal_errors > 0:
            for line in open(lint_output_file_name):
                if "no-member" in line or "no-name-in-module" in line or "import-error" in line:
                    print(line)

            print("Fatal lint errors : {0}".format(fatal_errors))
            exit(-1)
            return

        num_lines = sum(
            1
            for line in open(lint_output_file_name)
            if "*************" not in line
            and "---------------------" not in line
            and "Your code has been rated at" not in line
        )

        got_worse = is_it_worse("lint", num_lines, margin=10)
        max_lines = 350
        if num_lines > max_lines or got_worse:
            if got_worse:
                print("lint got worse - lines : {0}".format(num_lines))
            else:
                print("Too many lines of lint : {0} out of max of {1}".format(num_lines, max_lines))
            exit(-1)


@task(lint)
@timed()
def pytest_tests():
    with safe_cd(SRC):
        if IS_DJANGO:
            # Django app
            command = "{0} {1} manage.py test {2} -v 2".format(PIPENV, PYTHON, PACKAGE_NAME).strip()
            # We'd expect this to be MAC or a build server.
            my_env = config_pythonpath()
            execute_with_environment(command, env=my_env)
        else:
            my_env = config_pythonpath()
            if IS_ACTIONS:
                command = "{0} -m pytest {1}".format(PYTHON, "test").strip()
            else:
                command = "{0} {1} -m pytest {2}".format(PIPENV, PYTHON, "test").strip()
            print(command)
            execute_with_environment(command, env=my_env)


def config_pythonpath():
    if check_is_aws():
        env = "DEV"
    else:
        env = "MAC"
    my_env = {**os.environ, "ENV": env}
    my_env["PYTHONPATH"] = my_env.get("PYTHONPATH", "") + MAC_LIBS
    print(my_env["PYTHONPATH"])
    return my_env


@task()
@skip_if_no_change("vulture", expect_files="dead_code.txt")
@timed()
def dead_code():
    """
    This also finds code you are working on today!
    """
    with safe_cd(SRC):
        exclusions = "--exclude *settings.py,migrations/,*models.py,*_fake.py,*tests.py,*ui/admin.py"
        if IS_ACTIONS:
            command = "{0} vulture {1} {2}".format(PYTHON, PACKAGE_NAME, exclusions).strip().split()
        else:
            command = "{0} vulture {1} {2}".format(PIPENV, PACKAGE_NAME, exclusions).strip().split()

        output_file_name = "dead_code.txt"
        with open(output_file_name, "w") as outfile:
            env = config_pythonpath()
            subprocess.call(command, stdout=outfile, env=env)

        cutoff = 120
        num_lines = sum(1 for line in open(output_file_name) if line)
        if num_lines > cutoff:
            print("Too many lines of dead code : {0}, max {1}".format(num_lines, cutoff))
            exit(-1)


@task()
@timed()
def pip_check():
    print("pip_check always returns")
    with safe_cd(SRC):
        execute("pipenv", "check")


@task()
@skip_if_no_change("mypy")
def mypy():
    """
    Are types ok?
    """
    if sys.version_info < (3, 4):
        print("Mypy doesn't work on python < 3.4")
        return
    if IS_ACTIONS:
        command = "{0} -m mypy {1} --ignore-missing-imports --strict".format(PYTHON, PACKAGE_NAME).strip()
    else:
        command = "{0} mypy {1} --ignore-missing-imports --strict".format(PIPENV, PACKAGE_NAME).strip()

    bash_process = subprocess.Popen(
        command.split(" "),
        # shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = bash_process.communicate()  # wait
    mypy_file = "mypy_errors.txt"
    with open(mypy_file, "w+") as lint_file:
        lines = out.decode().split("\n")
        for line in lines:
            if "build_utils.py" in line:
                continue
            if "test.py" in line:
                continue
            if "tests.py" in line:
                continue
            if "/test_" in line:
                continue
            if "/tests_" in line:
                continue
            else:
                lint_file.writelines([line + "\n"])

    num_lines = sum(1 for line in open(mypy_file) if line and line.strip(" \n"))
    max_lines = 25
    if num_lines > max_lines:
        raise TypeError(f"Too many lines of mypy : {num_lines}, max {max_lines}")


@task()
@timed()
def jiggle_version():
    with safe_cd(SRC):
        command = "pip install jiggle_version --upgrade"
        execute(*(command.split(" ")))
        command = f"{PIPENV} jiggle_version here --module={PACKAGE_NAME}".strip()
        result = execute_get_text(command)
        print(result)
        command = f"{PIPENV} jiggle_version find --module={PACKAGE_NAME}".strip()
        result = execute_get_text(command)
        print(result)


@task()
@timed()
def pin_dependencies():
    with safe_cd(SRC):
        # right not because of black, pylint and astroid and (more?) freeze fails.
        # would have to do this in fresh env w/o dev deps.
        try:
            execute(*(f"{PIPENV} pipenv_to_requirements --freeze".strip().split(" ")))
        except:
            print("No pipfile.lock, switching to ordinary freeze")
            execute(*(f"{PIPENV} pip freeze".strip().split(" ")))
            raise NotImplementedError("TODO: pipe to requirements.txt")


@task()
@timed()
def check_setup_py():
    """
    Setup.py checks package things including README.rst
    """
    with safe_cd(SRC):
        if IS_ACTIONS:
            execute(PYTHON, *("setup.py check -s".split(" ")))
        else:
            execute(*("{0} {1} setup.py check -s".format(PIPENV, PYTHON).strip().split(" ")))


@task(pin_dependencies, dead_code, check_setup_py, compile_py, mypy, lint, pytest_tests, jiggle_version)
@skip_if_no_change("package")
@timed()
def package():
    with safe_cd(SRC):
        for folder in ["build", "dist", PACKAGE_NAME + ".egg-info"]:
            execute("rm", "-rf", folder)

    with safe_cd(SRC):
        execute(PYTHON, "setup.py", "sdist", "--formats=gztar,zip")

    os.system('say "package complete."')


@task()
@timed()
def echo(*args, **kwargs):
    """
    Pure diagnotics
    """
    print(args)
    print(kwargs)


# Default task (if specified) is run when no task is specified in the command line
# make sure you define the variable __DEFAULT__ after the task is defined
# A good convention is to define it at the end of the module
# __DEFAULT__ is an optional member

__DEFAULT__ = echo
