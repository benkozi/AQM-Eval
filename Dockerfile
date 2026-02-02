FROM continuumio/miniconda3

RUN apt-get update --yes && apt-get install --yes tmux vim less

RUN conda install -c conda-forge mamba

COPY environment*.yml /opt/build/
RUN mamba env create -f /opt/build/environment-dev.yml -q

COPY pyproject.toml /opt/build/pyproject.toml
COPY src /opt/build/src
WORKDIR /opt/build

RUN conda run -n aqm-eval-dev bash -c "pip install --no-deps . && pip list"
RUN conda run -n aqm-eval-dev bash -c "aqm-data-sync --help"
RUN conda run -n aqm-eval-dev bash -c "aqm-mm-eval --help"
RUN conda run -n aqm-eval-dev bash -c "aqm-verify --help"

# Test that the yaml_template directory exists after pip installation
RUN test -d /opt/conda/envs/aqm-eval-dev/lib/python3.11/site-packages/aqm_eval/mm_eval/yaml_template

#RUN conda env create -f /opt/build/environment.yml -q
#RUN conda run -n aqm-eval bash -c "pip install --no-deps . && pip list"
#RUN conda run -n aqm-eval bash -c "aqm-data-sync --help"
#RUN conda run -n aqm-eval bash -c "aqm-mm-eval --help"

WORKDIR /opt
RUN rm -rf /opt/build

# Activate environment by default
RUN echo "conda activate aqm-eval-dev" >> ~/.bashrc
