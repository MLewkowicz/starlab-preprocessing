import torch
from PIL import Image
import requests
from lavis.models import load_model_and_preprocess
import os


os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb=10'

image = Image.open("Image.jpg")

device = "cuda" if torch.cuda.is_available() else "cpu"

model, vis_processors, _ = load_model_and_preprocess(
    name="blip2_t5", model_type="pretrain_flant5xl", is_eval=True, device=device
)

image = vis_processors["eval"](image).unsqueeze(0).to(device)

description_prompt = "Question: What is happening in this image?"
object_prompt = "Describe in detail what unique objects are in this image. This includes information about people in the frame. Include information about the object's attributes such as color/size."

content = model.generate({"image": image, "prompt": description_prompt}, use_nucleus_sampling=True, num_captions=3)

object_content = model.generate({"image": image, "prompt": object_prompt})
