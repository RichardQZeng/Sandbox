import concurrent.futures
import multilib

from pathlib import Path  # to create the folder to store the images
from PIL import Image
import numpy as np
import uuid  # Don't forget to import uuid


def create_random_bg(N):
    Path("bg_images_2").mkdir(parents=True, exist_ok=True)  # creates the folder
    folder = "bg_images_2/"  # keep folder name here and use it to save the image

    for i in range(N):
        pixel_data = np.random.randint(
            low=0, high=256, size=(1024, 1024, 3), dtype=np.uint8
        )

        img = Image.fromarray(pixel_data, "RGB")  # turn the array into an image
        img_name = f"bg_{i}_{uuid.uuid4()}.png"  # give a unique name with a special identifier for each image
        img.save(folder + img_name)
        
# Using concurrent.futures to handle multiprocessing
def run_in_parallel(N, num_processes):
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [
            executor.submit(multilib.create_random_bg, N) for _ in range(num_processes)
        ]
        for future in concurrent.futures.as_completed(futures):
            print(future.result())  # You can handle results or exceptions here

# Example usage
N = 100  # Number of images per process
num_processes = 4  # Number of parallel processes
run_in_parallel(N, num_processes)