from pathlib import Path

import jinja2
import yaml

from aqm_eval.mm_eval.driver.config import Config
from aqm_eval.mm_eval.rocoto.srw_render import render_task_group


def test(tmp_path: Path, bin_dir: Path) -> None:
    render_task_group(tmp_path)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=tmp_path),
        undefined=jinja2.StrictUndefined,
    )
    template = env.get_template("aqm_post_melodies_monet.yaml")

    srw_config = bin_dir / "srw-config.yaml"
    srw_config_raw = srw_config.read_text()
    srw_config_raw = srw_config_raw.replace("!int '{{ platform.NCORES_PER_NODE }}'", "100")
    new_content = yaml.safe_load(srw_config_raw)
    new_content["melodies_monet_parm"]["aqm"]["output_dir"] = str(tmp_path)
    new_content["melodies_monet_parm"]["aqm"]["models"]["eval"]["expt_dir"] = str(tmp_path)
    new_content["melodies_monet_parm"]["start_datetime"] = "2023-06-01-12:00:00"
    new_content["melodies_monet_parm"]["end_datetime"] = "2023-06-02-12:00:00"
    new_content["melodies_monet_parm"]["cartopy_data_dir"] = tmp_path
    new_content["melodies_monet_parm"]["output_dir"] = tmp_path
    new_content["melodies_monet_parm"]["run_dir"] = tmp_path

    cfg = Config.from_yaml(new_content)
    data = cfg.to_yaml()
    data["platform"] = {"SCHED_NATIVE_CMD": "__run__"}
    data["jobname"] = "foobar"
    output = template.render(data)
    print(output)
