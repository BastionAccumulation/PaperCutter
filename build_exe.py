"""Build the Windows executable with the project's own dependency environment."""
import subprocess
import sys
import venv
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    environment = root / '.codex' / 'package-env'
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / 'Scripts' / 'python.exe'
    subprocess.run(
        [str(python), '-I', '-m', 'pip', 'install', '--disable-pip-version-check',
         '-r', str(root / 'requirements.txt')],
        cwd=root, check=True,
    )
    subprocess.run(
        [str(python), '-I', '-m', 'PyInstaller', '--noconfirm', '--clean',
         str(root / 'paper_cutter.spec')],
        cwd=root, check=True,
    )


if __name__ == '__main__':
    main()
