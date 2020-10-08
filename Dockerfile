FROM continuumio/miniconda
LABEL authors="Aron Skaftason" \
      description="Docker image for IGcaller"

# Install the conda environment
COPY misc/ig_caller_env.yaml /

RUN conda env create -f /ig_caller_env.yaml && conda clean -a

ENV PATH /opt/conda/envs/IGcaller_env/bin:$PATH

COPY / /IgCaller/.
