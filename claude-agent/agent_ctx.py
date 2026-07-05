"""AgentCtx — context object for dynamic Claude agent scripts.

Usage in an agent script stored in Project.agent:

    ctx.clone_git_url()
    task = ctx.get_task()
    kinds = ctx.get_kinds()
    strategy = ctx.decide_strategy(task, kinds)
    if ctx.get_modification_level() > MIDDLE:
        ctx.create_subtasks(strategy)
    ctx.branch(task)
    ctx.push(task)
    ctx.gh_create_pr(task)
    ctx.change_assignee(ctx.get_assignee())

The push() pipeline is split into finer-grained steps:

    ctx.implement(task)       # run the agent + tests, returns changed files
    ctx.commit(task)          # git add + commit, returns commit SHA
    ctx.git_push_only()       # git push only

push() chains implement() -> commit() -> git_push_only() and then updates the
task status to review (4) and posts a completion comment, so existing scripts
keep working unchanged.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

import anthropic
import requests

# Modification level constants available in agent scripts
SMALL = 1
MIDDLE = 2
LARGE = 3

# Code-generation tuning.  The previous 8K cap silently truncated full-file
# rewrites mid-output, which was the main cause of broken/inaccurate edits.
# Large outputs require streaming to avoid SDK HTTP timeouts.
_CODE_MAX_TOKENS = 64000

_KIND_PREFIX = {"feature": "Ftr", "bugfix": "Fix", "hotfix": "Fix", "enhancement": "Eta"}
_KIND_MAP = {"bug": "bugfix", "feature": "feature", "enhancement": "enhancement", "hotfix": "hotfix"}

# Status id used to mark a task as "in review" once the agent has pushed.
_REVIEW_STATUS = 4


def _strip_code_fences(text):
    """Remove a leading 