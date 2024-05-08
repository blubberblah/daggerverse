"""Module wrapping the gscloud commandline tool.


"""

from typing import Annotated
import dagger
from dagger import dag, field, function, object_type, Doc


@object_type
class Gscloud:
    """Wrapper for Gscloud tool, see: https://github.com/gridscale/gscloud.\nFor now only 'gscloud save-kubeconfig' is implemented."""
    #@function
    #async def kubeconfig(self, user_id: str, user_token: dagger.Secret, cluster_uuid: str) -> str:
    #    file = await self.kubeconfig_file(user_id, user_token, cluster_uuid)
    #    return await file.contents()

    # used as an option, see: https://docs.dagger.io/manuals/developer/python/944887/attribute-functions 
    gs_api_url: Annotated[str, Doc("Gridscale API endpoint URL")] = "https://api.gridscale.io"

    KUBECFG_PATH="/gs-cluster-kubeconfig.yaml"

    @function
    async def kubeconfig(
        self,
        user_id: Annotated[str, Doc("Username")],
        user_token: Annotated[dagger.Secret, Doc("A reference to a secret value representing the Usertoken")],
        cluster_uuid: Annotated[str, Doc("UUID of cluster")],
    ) -> dagger.File:
        """Generate kubeconfig for a cluster"""
        cont = await self.container()
        file = (
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
                
    @function
    async def container(self) -> dagger.Container:
        build_ctr = (
            dag.container()
            #.from_("alpine:latest")
            .from_("cgr.dev/chainguard/wolfi-base")
            .with_exec(["apk", "add", "--no-cache", "curl", "jq", "unzip"])
        ) 
        release_url = await (
            build_ctr.with_exec(["sh", "-c",
                 "curl -sL https://api.github.com/repos/gridscale/gscloud/releases/latest "
                 "| jq -r '.assets[] "
                 f"| select(.name|match(\"gscloud_.*_linux_amd64.zip$\")) "
                 "| .browser_download_url' "
                 "| tr -d '\n'"
            ])
            .stdout()
        )
        file = (
            build_ctr
            .with_exec(["sh", "-c",
                f"curl -Ls --output /tmp/gscloud-latest.zip '{release_url}' "
                "&& unzip -j /tmp/gscloud-latest.zip gscloud -d /usr/local/bin "
                "&& chmod u+x /usr/local/bin/gscloud"
            ]).file("/usr/local/bin/gscloud")
        )
        return (
            # make a new container containing only the gscloud binary
            dag.container()
            .from_("cgr.dev/chainguard/wolfi-base")
            .with_file("/usr/local/bin/gscloud", file)
        )