import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import build, db
from src.rules import RuleSet

@pytest.fixture(scope="session")
def starter(tmp_path_factory):
    d = tmp_path_factory.mktemp("starter")
    m = build.generate("starter", db_path=d/"s.db", export_dir=d/"exp", gt_dir=d/"gt", quiet=True)
    return dict(path=d/"s.db", manifest=m, gt=d/"gt", dir=d)

@pytest.fixture()
def conn(starter):
    c = db.connect(starter["path"], readonly=True); yield c; c.close()

@pytest.fixture(scope="session")
def rules(starter):
    c = db.connect(starter["path"], readonly=True); r = RuleSet.from_db(c); c.close(); return r
