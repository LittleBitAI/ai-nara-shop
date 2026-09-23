"""이 폴더의 스크립트가 쓰는 `script.py` 를 커밋으로 고정해 불러온다.

작업 트리의 `script.py` 를 부르면 `main` 이 바뀔 때마다 같은 보관 응답의 결과가 바뀐다.
그리고 현재 코드에는 후보의 `competitive_row` 파싱과 게이트가 없다. 그래서 두 회차를
**그 회차를 만든 코드**로 읽는다.
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE_REV = "57e6134"   # 판정 당시 기준 코드 (script.py blob 51f3329)
CAND_REV = "9ed0805"   # B1 후보 회차 코드 (origin/run/b1-competitive-row)


def load_script(rev):
    """`rev:script.py` 를 임시 파일로 꺼내 모듈로 불러온다. 두 판을 한 프로세스에 함께 둔다."""
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:script.py"],
                            capture_output=True, check=True).stdout
    path = Path(tempfile.mkdtemp(prefix=f"script-{rev}-")) / "script.py"
    path.write_bytes(source)
    name = f"submission_{rev}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.load_sme_reference(str(ROOT / "open/data"))
    return module
