from cat_fact import api_flow
from prefect.deployments import Deployment
from prefect.filesystems import RemoteFileSystem

minio_block = RemoteFileSystem(
    basepath="s3://prefect-flows/api_flow",
    key_type="hash",
    settings=dict(
        use_ssl = False,
        key = "minioadmin",
        secret = "minioadmin",
        client_kwargs = dict(endpoint_url = "http://localhost:9000")
    ),
)
minio_block.save("minio", overwrite=True)

deployment = Deployment.build_from_flow(
    flow=api_flow,
    storage=RemoteFileSystem.load('minio'),
    name="example-deployment", 
    version=1, 
    work_queue_name="default",
)
deployment.apply()