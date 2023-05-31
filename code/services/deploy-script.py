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
FRONTEND_DIR_NAME: str = "MLodImage"
ORCHESTRATOR_PATH: str = "../orchestrator/fastapi/"
ORCHESTRATOR_DIR_NAME: str = "fastapi"
WEBAPP_PORT: int = 80
SERVICES_PORT: int = 8000


def main():
    global DOCKER_REGISTRY, SERVICE_NAMESPACE
    print("ROOT:" + os.environ["REPO_ROOT"])
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
    modified_frontend = modified_services.copy()
    modified_orchestrator = modified_services.copy()

    # filter for services/frontend folder
    modified_services = list(filter(lambda x: x.startswith("code/services/"), modified_services))
    modified_frontend = list(filter(lambda x: x.startswith("code/frontend/"), modified_frontend))
    modified_orchestrator = list(filter(lambda x: x.startswith("code/orchestrator/"), modified_orchestrator))

    # keep only the service/frontend name
    modified_services = list(map(lambda x: x.split("/")[2], modified_services))
    modified_frontend = list(map(lambda x: x.split("/")[2], modified_frontend))
    modified_orchestrator = list(map(lambda x: x.split("/")[2], modified_orchestrator))

    # remove duplicates
    modified_services = list(set(modified_services))
    modified_frontend = list(set(modified_frontend))
    modified_orchestrator = list(set(modified_orchestrator))

    return modified_services + modified_frontend + modified_orchestrator


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
                # check if the service has a pre-script to run before building the docker image
                if os.path.isfile(f"{service}/pre.sh"):
                    print(f"Running pre-script for {service}...")
                    status = os.system(f"sh {service}/.pre.sh")
                    if status != 0:
                        raise Exception(f"Error while running pre-script for {service}")
                docker_build(service)
                if os.path.isfile(f"{service}/.build-only"):
                    print(f"Skipping deployment of {service}")
                else:
                    deploy_service(service)

    # check if the frontend has been modified
    if FRONTEND_DIR_NAME in modified_services:
        docker_build(FRONTEND_PATH)
        deploy_service(FRONTEND_PATH)

    # check if the orchestrator has been modified
    if ORCHESTRATOR_DIR_NAME in modified_services:
        docker_build(ORCHESTRATOR_PATH)
        deploy_service(ORCHESTRATOR_PATH)


def docker_build(service_dir: str) -> None:
    """
    This function builds the docker image of a service and pushes it to the Container Registry
    """
    service_name: str = service_dir
    if service_dir == FRONTEND_PATH:
        service_name = "webapp"
    if service_dir == ORCHESTRATOR_PATH:
        service_name = "orchestrator"
    print(f"Building {service_name}...")
    status = os.system(f"docker build -t {DOCKER_REGISTRY}{service_name} {service_dir}")
    if status != 0:
        raise Exception(f"Error while building {service_name}")
    print(f"{service_name} built, pushing to registry...")
    status = os.system(f"docker push {DOCKER_REGISTRY}{service_name}")
    if status != 0:
        raise Exception(f"Error while pushing {service_name} to registry")


def deploy_service(service_dir: str) -> None:
    """
    This function deploys a service on the Kubernetes cluster
    """
    service_name: str = service_dir
    if service_dir == FRONTEND_PATH:
        service_name = "webapp"
    if service_dir == ORCHESTRATOR_PATH:
        service_name = "orchestrator"
    # check if the service has a .gpu file
    if os.path.isfile(f"{service_dir}/.gpu"):
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
    os.environ["PORT"] = str(SERVICES_PORT if service_name != "webapp" else WEBAPP_PORT)
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
