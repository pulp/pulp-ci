import os
import re
import json
from packaging.version import Version
from git import Repo

repo = Repo(os.getcwd())
heads = repo.git.ls_remote("--heads", "https://github.com/pulp/pulpcore.git").split("\n")
branches = [h.split("/")[-1] for h in heads if re.search(r"^([0-9]+)\.([0-9]+)$", h.split("/")[-1])]
branches.sort(key=lambda ver: Version(ver))

with open("ci/config/releases/supported-releases.json") as f:
    supported = f.read()

supported_json = json.loads(supported)

for version in supported_json:
    if Version(version) > Version("3.0.0"):
        print(f"Latest: {branches[-1]}\Current: {version}")
        version3 = version

if Version(branches[-1]) > Version(version3):
    supported = supported.replace(version3, branches[-1])

with open("ci/config/releases/supported-releases.json", "w") as f:
    f.write(supported)
