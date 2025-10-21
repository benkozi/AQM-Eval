from pathlib import Path

from aqm_eval.mm_eval.driver.package.core import TaskKey, PackageKey
from aqm_eval.mm_eval.rocoto.srw_render import PackageData, PackageDataCollection, Renderer


def test(tmp_path: Path) -> None:
    packages = PackageDataCollection(packages=[PackageData(key=ii, tasks=tuple(TaskKey)) for ii in PackageKey])
    renderer = Renderer(coll=packages, out_dir=tmp_path)
    renderer.run()
    print(renderer.out_path.read_text())