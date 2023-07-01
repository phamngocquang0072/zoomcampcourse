from prefect.infrastructure.docker import DockerContainer

docker_block = DockerContainer(
    image="quangnpham/prefect:zoom",
    image_pull_policy="ALWAYS",
    auto_remove=True,
)

docker_block.save("docker-zoom", overwrite=True)