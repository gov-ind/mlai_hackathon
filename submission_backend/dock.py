import json
import os
import docker 
import uuid

import platform

def get_default_platform() -> str:
    machine = platform.uname().machine
    machine = {"x86_64": "amd64"}.get(machine, machine)
    return f"linux/{machine}"

def save_docker_submission(client, output_directory, submission_directory, evaluation_file, present_index):
    if not os.path.exists(output_directory):
        raise ValueError(f"Output directory {output_directory} does not exist")

    if not os.path.exists(submission_directory):
        raise ValueError(f"Submission path {submission_directory} does not exist")

    docker_image_tag = str(uuid.uuid4())
    print('### Building image')
    result = client.images.build(path=submission_directory, tag=docker_image_tag, platform=get_default_platform(), quiet=False)
    print(result[0], type(result[0]))
    print(dir(result[0]))

    for item in result[1]:
        print(item)

    print('### Finished building image')
    
    # copy the evaluation file to the output directory
    copied_evaluation_file = os.path.join(output_directory, "input.csv")
    print(evaluation_file, '9999(((9(9(999())))))')
    os.system(f"cp {evaluation_file} {copied_evaluation_file}")

    container = client.containers.run(
        docker_image_tag, 
        command=f"python bot/evaluate.py --output_file {output_directory}/output.json --data {copied_evaluation_file} --present_index {present_index}", 
        volumes={output_directory: {'bind': output_directory, 'mode': 'rw'}},
        detach=True,
        network_mode="none",
    )

    for line in container.logs(stream=True):
        print(line.strip())

    container.stop()
    container.remove()

    client.images.remove(docker_image_tag)
    os.remove(copied_evaluation_file)

    print(f'### Finished running container for image: {docker_image_tag}')

def get_submission_output(client, output_directory, submission_directory, evaluation_file, present_index):
    save_docker_submission(client, output_directory, submission_directory, evaluation_file, present_index)

    with open(os.path.join(output_directory, "output.json"), 'r') as f:
        data = json.load(f)

    os.remove(os.path.join(output_directory, "output.json"))

    return data
