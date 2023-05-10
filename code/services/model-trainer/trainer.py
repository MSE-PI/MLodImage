"""
This python file as the objective to train the model and save it on DVC
"""
from time import sleep

if __name__ == '__main__':
    print("Training model...")
    sleep(120)
    print("Model trained!")
    # kubectl wait that the pod is terminated