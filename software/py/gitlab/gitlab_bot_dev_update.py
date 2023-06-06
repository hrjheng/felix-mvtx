import os
import sh
from sh import git
import gitlab

project_id_CRU_ITS = 34336
project_id_RU_mainFPGA  = 20090

target_branch = 'development'

def main():
    gl = gitlab.Gitlab(url="https://gitlab.cern.ch/", private_token=os.environ['CI_JOBKEY'])
    gl.auth()
    project = gl.projects.get(project_id_CRU_ITS, lazy=True)
    merges = project.mergerequests.list(state='opened', target_branch=target_branch, wip='no', draft='no', scope='all')
    if len(merges) > 0:
        git.remote('set-url', 'origin', f"https://itsruci:{os.environ['CI_JOBKEY']}@gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS.git")
        git.config('--local', 'user.name', '\'itsruci\'')
        git.config('--local', 'user.email', '\'its.ru.ci@cern.ch\'')
        git.fetch('--all')
        for merge in merges:
            print(f"Updating : {merge.source_branch}")
            try:
                git.checkout('--track', f"remotes/origin/{merge.source_branch}")
            except (sh.ErrorReturnCode_1) as err:
                print(f"Branch {merge.source_branch} not existing anymore, was it already merged? : {err}")
                continue
            except (sh.ErrorReturnCode_128) as err:
                print(f"Something went terribly wrong on branch {merge.source_branch} : {err}")
                continue
            try:
                git.rebase(f"remotes/origin/{target_branch}")
            except (sh.ErrorReturnCode_1) as err:
                print(f"Branch {merge.source_branch} failed automatic rebase: {err}")
                merge.notes.create({'body': f"Automatic rebase of {target_branch} branch failed. Please resolve merge-conflict manually."})
                git.reset('--hard', 'ORIG_HEAD')
                continue
            except (sh.ErrorReturnCode_128) as err:
                print(f"Something went terribly wrong on branch {merge.source_branch} : {err}")
                git.reset('--hard', 'ORIG_HEAD')
                continue
            try:
                git.push('--force-with-lease', 'origin', f"{merge.source_branch}")
            except (sh.ErrorReturnCode_1, sh.ErrorReturnCode_2) as err:
                print(f"Failed to push on branch {merge.source_branch}: {err}")
                git.reset('--hard', 'ORIG_HEAD')
            except (sh.ErrorReturnCode_128) as err:
                print(f"Something went terribly wrong on branch {merge.source_branch} : {err}")
                git.reset('--hard', 'ORIG_HEAD')
                continue
    print("Update complete")

if __name__ == "__main__":
    main()
