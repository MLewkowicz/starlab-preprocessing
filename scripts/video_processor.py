import cv2
import moviepy.editor as mp
import json
import numpy as np
import os 
import torch
import requests
import os
from torch.nn import CosineSimilarity
import matplotlib.pyplot as plt
from transformers import CLIPTokenizer, CLIPModel, CLIPTextModel
import sys
from PIL import Image
from pycocotools import mask as mask_utils
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor
class ImageProcessor:
    def __init__(self):
        sam_checkpoint = "/mnt/c/Users/indue/Downloads/sam_vit_h_4b8939.pth"
        model_type = "vit_h"
        
        device = "cuda"
        
        sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
        sam.to(device=device)
        
        self.mask_generator = SamAutomaticMaskGenerator(sam)
    def show_anns(anns):
        if len(anns) == 0:
            return
        sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
        ax = plt.gca()
        ax.set_autoscale_on(False)
    
        img = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
        img[:,:,3] = 0
        for ann in sorted_anns:
            m = ann['segmentation']
            color_mask = np.concatenate([np.random.random(3), [0.35]])
            img[m] = color_mask
        ax.imshow(img)
    
    def create_masked_images(self, image, output_dir, frame_id):
        # Generate the mask
        images = []
        masks = self.mask_generator.generate(image)
        frame_dir = os.path.join(output_dir, "Frame.{}".format(frame_id)) 

        os.makedirs(frame_dir, exist_ok=True)
        DATA_FILE = os.path.join(frame_dir, "mask_data.txt")
        # MASK_DIR = os.path.join(frame_dir, "masks")
        # os.makedirs(MASK_DIR, exist_ok=True)
        IMAGE_FILE = os.path.join(frame_dir, "frame.jpg")

        cv2.imwrite(IMAGE_FILE, image)
        # Apply each mask on the image
        with open(DATA_FILE, 'w') as f: 
            for i, ann in enumerate(masks): 
                annotation = ann
                annotation['segmentation'] = [] 
                mask = ann['segmentation']
                bbox = ann['bbox']
                # Create an empty black image with the same size
                # bbox_image = self.extract_bbox(image, ann['bbox'])
                f.write(json.dumps(annotation) + '\n')
                # filename = "Mask.{}.png".format(i)
                # Save the masked image to the output folder
                # output_path = os.path.join(MASK_DIR, filename)
                # masked_image_pil = Image.fromarray(masked_image)
                # bbox_image = bbox_image[:,:,::-1]
                # masked_image_pil = Image.fromarray(bbox_image)
                # masked_image_pil = masked_image_pil.save(output_path)
                # cv2.imwrite(output_path, masked_image_pil)
                # images.append(preprocess(masked_image_pil))
    
        print("Saved frame data for {}".format(frame_id)) 
        return images
        
    def extract_bbox(self, img, bbox):
        x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
        return img[y:y+h, x:x+w]

class VideoProcessor:
    def __init__(self, video_file) -> None:
        self.transcript = ""
        self.video_file = video_file
        self.image_processor = ImageProcessor()
    def process_transcript():
        pass

    def video_to_images(self, interval, output_folder):
        clip = mp.VideoFileClip(self.video_file)
        print(clip.fps)
        print("Loaded video file...") 
        os.makedirs(output_folder, exist_ok=True)
    
        # total num frames + interval offset
        total_frames = int(clip.fps * clip.duration)
        frames_step = interval

        vidcap = cv2.VideoCapture(self.video_file)
    
        for i in range(0, total_frames, frames_step):
            vidcap.set(cv2.CAP_PROP_POS_FRAMES, i)
            success, image = vidcap.read()
            if success:
                frame_id = round(i / clip.fps, 2)
                self.image_processor.create_masked_images(image, output_folder, frame_id)  
        return 0 

def main():
    video_file = "/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/oYMAX90kNkU.mp4"
    video_processor = VideoProcessor(video_file)    
    video_processor.video_to_images(30, "Data10")

if __name__=="__main__":
    main()
