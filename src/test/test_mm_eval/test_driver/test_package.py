from polyfactory.factories.pydantic_factory import ModelFactory

from aqm_eval.mm_eval.driver.package import MetEvalPackage


class MetEvalPackageFactory(ModelFactory[MetEvalPackage]): ...


class TestMetEvalPackage:
    def test(self) -> None:
        package = MetEvalPackageFactory.build()
        assert package.mm_models[0].link_alldays_path_template.endswith("eval_ish*.nc")
