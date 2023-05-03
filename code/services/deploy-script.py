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
FRONTEND_PATH: str = "../frontend/MLodImage/"


def main():
    global DOCKER_REGISTRY, SERVICE_NAMESPACE
    # read environment variables
    DOCKER_REGISTRY = os.environ["DOCKER_REGISTRY"]
    SERVICE_NAMESPACE = os.environ["NAMESPACE"]
    discover_services()


def get_modified_services() -> list:
    """
    This function returns a list of all services that have been modified in the last commit
    """
    # get list of modified files in the last commit
    modified_services = os.popen("git diff --name-only HEAD^ HEAD").read().split("\n")

    # filter for services/frontend folder
    modified_services = list(filter(lambda x: x.startswith("code/services/"), modified_services))
    modified_frontend = list(filter(lambda x: x.startswith("code/frontend/"), modified_services))

    print(modified_frontend)

    # keep only the service/frontend name
    modified_services = list(map(lambda x: x.split("/")[2], modified_services))
    modified_frontend = list(map(lambda x: x.split("/")[2], modified_frontend))

    # remove duplicates
    modified_services = list(set(modified_services))
    modified_frontend = list(set(modified_frontend))

    return modified_services + modified_frontend


def discover_services() -> None:
    """
    This function discovers all the services in the services folder
    """
    # get list of modified services
    modified_services = get_modified_services()
    print("Modified services: " + str(modified_services))
    for service in os.listdir():
        if os.path.isdir(service):
            # check if the service has a Dockerfile and is in the list of modified services
            if os.path.isfile(f"{service}/Dockerfile") and service in modified_services:
                docker_build(service)
                deploy_service(service)

    for frontend in os.listdir("../frontend"):
        if os.path.isdir(frontend):
            # check if the frontend has a Dockerfile and is in the list of modified services
            if os.path.isfile(f"{frontend}/Dockerfile") and frontend in modified_services:
                docker_build(FRONTEND_PATH)
                deploy_service(FRONTEND_PATH)


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
    os.environ["SERVICE"] = service_name if service_name != FRONTEND_PATH else "webapp"  # set name for frontend
    os.system(f"envsubst < ../k8s/service.yml | cat")
    status = os.system(f"envsubst < ../k8s/service.yml | kubectl apply -n {SERVICE_NAMESPACE} -f -")
    if status != 0:
        raise Exception(f"Error while deploying " + service_name)
    os.system(f"kubectl -n {SERVICE_NAMESPACE} rollout restart deployment {service_name}")
    if status != 0:
        raise Exception("Error while restarting " + service_name)
    print(f"{service_name} deployed!")


if __name__ == '__main__':
    main()
