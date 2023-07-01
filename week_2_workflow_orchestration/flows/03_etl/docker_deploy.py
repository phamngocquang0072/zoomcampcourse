from prefect.infrastructure.docker import DockerContainer
from prefect.deployments import Deployment
from parameterized_flow import etl_parent_flow

docker_block = DockerContainer.load("docker-zoom")

docker_deploy = Deployment.build_from_flow(
    flow=etl_parent_flow,
    name='docker-flow',
    infrastructure=docker_block
)

if __name__ == "__main__":  
    docker_deploy.apply()
