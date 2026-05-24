import os


def git_hash(request):
    return {"GIT_HASH": os.environ.get("GIT_HASH", "unknown")}
