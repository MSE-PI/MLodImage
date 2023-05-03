"""
This file contains a script to deploy all services on the Kubernetes cluster
"""

__author__ = "Florian Hofmann"
__date__ = "15.04.2023"

import os

DOCKER_REGISTRY: str = "-"
SERVICE_NAMESPACE: str = "-"
GPU_CORE: str = "tencent.com/vcuda-core: 20"
GPU_MEMORY: str = "tencent.com/vcuda-memory: 64"



def main():
    global DOCKER_REGISTRY, SERVICE_NAMESPACE
    # read environment variables
    DOCKER_REGISTRY = os.environ["DOCKER_REGISTRY"]
    SERVICE_NAMESPACE = os.environ["NAMESPACE"]
    discover_services()


def discover_services() -> None:
    """
    This function discovers all the services in the services folder
    """
    for service in os.listdir():
        if os.path.isdir(service):
            # check if the service ha a Dockerfile
            if os.path.isfile(f"{service}/Dockerfile"):
                docker_build(service)
                deploy_service(service)

def docker_build(service_name: str) -> None:
    """
    This function builds the docker image of a service and pushes it to the Container Registry
    """
    print(f"Building {service_name}...")
    status = os.system(f"docker build -t {DOCKER_REGISTRY}{service_name} {service_name}")
    if status != 0:
        raise Exception(f"Error while building {service_name}")
    print(f"{service_name} built, pushing to registry...")
    status = os.system(f"docker push {DOCKER_REGISTRY}{service_name}")
    if status != 0:
        raise Exception(f"Error while pushing {service_name} to registry")
def deploy_service(service_name: str) -> None:
    """
    This function deploys a service on the Kubernetes cluster
    """
    # check if the service has a .gpu file
    if os.path.isfile(f"{service_name}/.gpu"):
        # set GPU ENV variables
        print("GPU on : " + service_name)
        os.environ["GPU_CORE"] = GPU_CORE
        os.environ["GPU_MEMORY"] = GPU_MEMORY
    else:
        os.environ["GPU_CORE"] = ""
        os.environ["GPU_MEMORY"] = ""
    print(f"Deploying {service_name}...")
    # setup service environment variables
    os.environ["SERVICE"] = service_name
    os.system(f"envsubst < ../k8s/service.yml | cat")
    #return
    status = os.system(f"envsubst < ../k8s/service.yml | kubectl apply -n {SERVICE_NAMESPACE} -f -")
    if status != 0:
        raise Exception(f"Error while deploying " + service_name)
    os.system(f"kubectl -n {SERVICE_NAMESPACE} rollout restart deployment {service_name}")
    if status != 0:
        raise Exception("Error while restarting " + service_name)
    print(f"{service_name} deployed!")

if __name__ == '__main__':
    main()
