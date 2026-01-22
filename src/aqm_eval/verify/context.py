import datetime
from pathlib import Path
from typing import Iterator

from pydantic import Field

from aqm_eval.base import AeBaseModel


class VerifyPair(AeBaseModel):
    actual: Path
    expected: Path


class VerifyContext(AeBaseModel):
    verify_pairs: tuple[VerifyPair,...] = Field(min_length=1)
    variables: tuple[str,...] = Field(default=("O3", "PM25_TOT",), min_length=1)
    baseline_dir: Path | None = None
    expt_dir: Path | None = None
    tolerance: float = 1e-12
    verbose: bool = True

    def iter_nccmp_cmds(self) -> Iterator[tuple[str,...]]:
        v = ",".join(self.variables)
        for verify_pair in self.verify_pairs:
            expected = verify_pair.expected
            if self.baseline_dir is not None:
                expected = self.baseline_dir / expected
            actual = verify_pair.actual
            if self.expt_dir is not None:
                actual = self.expt_dir / actual

            cmd = ["nccmp"]
            if self.verbose:
                cmd.append("--verbose")
            cmd += ["-d", "-m", "-v", v, "-t", str(self.tolerance), str(actual), str(expected)]
            yield tuple(cmd)