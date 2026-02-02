from functools import cached_property
from pathlib import Path
from typing import Iterator

from pydantic import Field

from aqm_eval.base import AeBaseModel


class VerifyPair(AeBaseModel):
    actual: Path
    expected: Path
    variables: tuple[str, ...] = Field(
        default=(
            "O3",
            "PM25_TOT",
        ),
        min_length=1,
    )


class VerifyContext(AeBaseModel):
    verify_pairs: tuple[VerifyPair, ...] = Field(min_length=1)
    baseline_dir: Path | None = None
    expt_dir: Path | None = None
    tolerance: float = 1e-12
    verbose: bool = True
    fail_fast: bool = False

    @cached_property
    def verify_pairs_full_path(self) -> tuple[VerifyPair, ...]:
        ret = []
        for verify_pair in self.verify_pairs:
            actual = verify_pair.actual
            if not actual.exists():
                if self.expt_dir is None:
                    raise ValueError(f"expt_dir must be set if actual path does not exist. {actual=}")
                actual = self.expt_dir / actual
            expected = verify_pair.expected
            if not expected.exists():
                if self.baseline_dir is None:
                    raise ValueError(f"baseline_dir must be set if expected path does not exist. {expected=}")
                expected = self.baseline_dir / expected
            ret.append(VerifyPair.model_validate(dict(actual=actual, expected=expected, variables=verify_pair.variables)))
        return tuple(ret)

    def iter_nccmp_cmds(self) -> Iterator[tuple[str, ...]]:
        for verify_pair in self.verify_pairs_full_path:
            cmd = ["nccmp"]
            if self.verbose:
                cmd.append("--verbose")
            v = ",".join(verify_pair.variables)
            cmd += ["-d", "-m", "-v", v, "-t", str(self.tolerance), str(verify_pair.actual), str(verify_pair.expected)]
            yield tuple(cmd)
