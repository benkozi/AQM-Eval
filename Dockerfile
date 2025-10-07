FROM continuumio/miniconda3

RUN apt-get update --yes && apt-get install --yes tmux vim less

COPY environment.yml /opt/build/environment.yml
RUN conda env create -f /opt/build/environment.yml -q

COPY pyproject.toml /opt/build/pyproject.toml
COPY src /opt/build/src
WORKDIR /opt/build
RUN conda run -n aqm-eval bash -c "pip install --no-deps . && pip list"
RUN conda run -n aqm-eval bash -c "aqm-data-sync --help"
RUN conda run -n aqm-eval bash -c "aqm-mm-eval --help"

# Test that the yaml_template directory exists after pip installation
RUN test -d /opt/conda/envs/aqm-eval/lib/python3.11/site-packages/aqm_eval/mm_eval/yaml_template

WORKDIR /opt
RUN rm -rf /opt/build

# Activate environment by default
RUN echo "conda activate aqm-eval" >> ~/.bashrc
