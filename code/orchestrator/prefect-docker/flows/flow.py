from prefect import flow, task

@task
def say_hello(name):
    print(f"hello {name}")

@task
def say_goodbye(name):
    print(f"goodbye {name}")

@flow(name="test flow",
      persist_result=True,
      result_serializer='json',
      result_storage='remote-file-system/minio-results')
def greetings(names=["arthur", "trillian", "ford", "marvin"], id="1234"):
    print(f"flow id: {id}")
    for name in names:
        say_hello(name)
        say_goodbye(name)
    return "done"

if __name__ == "__main__":
    greetings(["arthur", "trillian", "ford", "marvin"])
