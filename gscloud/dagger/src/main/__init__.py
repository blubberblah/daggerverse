"""A generated module for Gscloud functions

This module has been generated via dagger init and serves as a reference to
basic module structure as you get started with Dagger.

Two functions have been pre-created. You can modify, delete, or add to them,
as needed. They demonstrate usage of arguments and return types using simple
echo and grep commands. The functions can be called from the dagger CLI or
from one of the SDKs.

The first line in this comment block is a short description line and the
rest is a long description with more detail on the module's purpose or usage,
if appropriate. All modules should have a short description.
"""

"""
tkn=****** dagger call kubeconfig-file --user-id=****** --user-token=env:tkn --cluster-uuid=***** contents


https://archive.docs.dagger.io/0.9/205271/replace-dockerfile/
https://daggerverse.dev/mod/github.com/seungyeop-lee/daggerverse/scp@4ba108db8397e7c2739ca89616a57100da858e07#Commander.fileToRemote

"""


from typing import Annotated
import dagger
from dagger import dag, field, function, object_type, Doc


@object_type
class Gscloud:
    #@function
    #async def kubeconfig(self, user_id: str, user_token: dagger.Secret, cluster_uuid: str) -> str:
    #    file = await self.kubeconfig_file(user_id, user_token, cluster_uuid)
    #    return await file.contents()

    # used as an option, see: https://docs.dagger.io/manuals/developer/python/944887/attribute-functions 
    gs_api_url: Annotated[str, Doc("Gridscale API endpoint URL")] = "https://api.gridscale.io"

    KUBECFG_PATH="/gs-cluster-kubeconfig.yaml"

    @function
    async def kubeconfig_file(
        self,
        user_id: Annotated[str, Doc("Username")],
        user_token: Annotated[dagger.Secret, Doc("A reference to a secret value representing the Usertoken")],
        cluster_uuid: Annotated[str, Doc("UUID of cluster")],
    ) -> dagger.File:
        cont = await self.gscloud_container()
        file = await (
            cont
            .with_env_variable("GRIDSCALE_UUID", user_id)
            .with_env_variable("GRIDSCALE_TOKEN", await user_token.plaintext())
            .with_env_variable("GRIDSCALE_URL", self.gs_api_url)
            .with_exec(["sh", "-c",
                    "gscloud kubernetes cluster save-kubeconfig"
                    f" --kubeconfig {self.KUBECFG_PATH}"
                    f" --cluster {cluster_uuid}"
            ])
            .file("/gs-cluster-kubeconfig.yaml")
        )
        return file
                
    async def gscloud_container(self) -> dagger.Container:
        cont = await (
            dag.container()
            #.from_("alpine:latest")
            .from_("cgr.dev/chainguard/wolfi-base")
            .with_exec(["apk", "add", "--no-cache", "curl", "jq", "unzip"])
        ) 
        release_url = await(
            cont.with_exec(["sh", "-c",
                 "curl -sL https://api.github.com/repos/gridscale/gscloud/releases/latest "
                 "| jq -r '.assets[] "
                 f"| select(.name|match(\"gscloud_.*_linux_amd64.zip$\")) "
                 "| .browser_download_url' "
                 "| tr -d '\n'"
            ])
            .stdout()
        )
        return await(
            cont
            .with_exec(["sh", "-c",
                f"curl -Ls --output /tmp/gscloud-latest.zip '{release_url}' "
                "&& unzip -j /tmp/gscloud-latest.zip gscloud -d /usr/local/bin "
                "&& chmod u+x /usr/local/bin/gscloud"
            ])
        )