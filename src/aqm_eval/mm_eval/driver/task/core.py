from abc import ABC, abstractmethod

from melodies_monet.driver import analysis
from pydantic import BaseModel

from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.mm_eval.driver.config import TaskKey


class AbstractEvalTask(ABC, BaseModel):
    model_config = {"frozen": True}

    key: TaskKey
    template_filename: str

    @abstractmethod
    def initialize(self):
        raise NotImplementedError

    @abstractmethod
    def run(self, an: analysis) -> None:
        raise NotImplementedError
