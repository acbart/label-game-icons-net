import subprocess

def get_git_username():
    res = subprocess.run(["git", "config", "user.name"], stdout=subprocess.PIPE)
    git_username = res.stdout.strip().decode()
    return git_username
