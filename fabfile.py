# -*- coding: utf-8 -*-
from fabric.api import task, local


@task
def build():
    """Build docker image."""
    local('sudo docker build -t scrapyrt .')


@task
def run(project_dir, port=9080):
    """Run docker image."""
    cmd = ('sudo docker run -p {port}:{port} -tid '
           '-v {project_dir}:/scrapyrt/project scrapyrt')
    local(cmd.format(project_dir=project_dir, port=port))
