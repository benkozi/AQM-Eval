from pathlib import Path

from polyfactory.factories.pydantic_factory import ModelFactory

from aqm_eval.mm_eval.driver.package.core import TaskKey, PackageKey
from aqm_eval.mm_eval.rocoto.srw_render import PackageData, PackageDataCollection, Renderer, \
    TaskDataCollection, TaskData

#     __randomize_collection_length__ = True
#     __min_collection_length__ = len(PackageKey)
#     __max_collection_length__ = len(PackageKey)
#
# class TaskDataCollectionFactory(ModelFactory[TaskDataCollection]):
#     __randomize_collection_length__ = True
#     __min_collection_length__ = len(TaskKey)
#     __max_collection_length__ = len(TaskKey)

class TaskDataFactory(ModelFactory[TaskData]):
    __use_defaults__ = True


class TaskDataCollectionFactory(ModelFactory[TaskDataCollection]):
    __use_defaults__ = True

    # @classmethod
    # def members(cls) -> tuple[TaskData, ...]:
    #     return tuple(TaskDataFactory.build(key=task_key) for task_key in TaskKey)

class PackageDataFactory(ModelFactory[PackageData]):
    __use_defaults__ = True
    __model_factories__ = {TaskDataCollection: TaskDataCollectionFactory}


class PackageDataCollectionFactory(ModelFactory[PackageDataCollection]):
    __use_defaults__ = True
    __model_factories__ = {PackageData: PackageDataFactory}


def test(tmp_path: Path) -> None:
    #tdk: add to cli
    packages = PackageDataCollection()
    print(packages)
    renderer = Renderer(coll=packages, out_dir=tmp_path)
    renderer.run()
    print(renderer.out_path.read_text())