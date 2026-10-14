"""Copy product recipes as explicitly synthetic user recipes for public tests."""
import shutil
from pathlib import Path
import yaml


def copy_recipe(source, destination):
    result=shutil.copytree(source,destination)
    path=Path(destination)/'recipe.yaml'
    data=yaml.safe_load(path.read_text())
    data.update(author={'name':'Synthetic author','contacts':['https://example.invalid/author']},license='MIT')
    path.write_text(yaml.safe_dump(data,sort_keys=False))
    return result
