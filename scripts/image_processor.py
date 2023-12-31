import clip
import json
import ast
import torch
import requests
import os
import cv2
from torch.nn import CosineSimilarity
import matplotlib.pyplot as plt
from transformers import * # CLIPTokenizer, CLIPModel, CLIPTextModel 
import sys
import numpy as np
from PIL import Image
from pycocotools import mask as mask_utils
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor
from helpers import Timecode
from lavis.models import load_model_and_preprocess

INTERSECTION_THRESHOLD = 10

def iuo(self, bbox1, bbox2):
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[0] + bbox1[2], bbox2[0] + bbox2[2])
    y2 = min(bbox1[1] + bbox1[3], bbox2[1] + bbox2[3])

    intersection_area = max(0, x2 - x1) * max(0, y2 - y1)

    bbox1_area = bbox1[2] * bbox1[3]
    bbox2_area = bbox2[2] * bbox2[3]

    union_area = bbox1_area + bbox2_area - intersection_area
    if union_area == 0:
        return 0

    iou = intersection_area / union_area
    return iou

class ImageProcessor:
    def __init__(self):
        sam_checkpoint = "/mnt/c/Users/indue/Downloads/sam_vit_h_4b8939.pth"
        model_type = "vit_h"
        
        sam_kwargs = {
            "points_per_side": 32,
            "pred_iou_thresh": 0.86,
            "stability_score_thresh": 0.92,
            "crop_n_layers": 1,
            "crop_n_points_downscale_factor": 2,
            "min_mask_region_area": 100,
        }
        device = "cuda"
        
        sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
        sam.to(device=device)
        
        self.model, self.preprocess = clip.load("ViT-B/32")
        self.mask_generator = SamAutomaticMaskGenerator(
            model=sam,
            points_per_side= sam_kwargs["points_per_side"],
            pred_iou_thresh=sam_kwargs["pred_iou_thresh"],
            stability_score_thresh=sam_kwargs["stability_score_thresh"],
            crop_n_layers=sam_kwargs["crop_n_layers"],
            crop_n_points_downscale_factor=sam_kwargs["crop_n_points_downscale_factor"],
            min_mask_region_area=sam_kwargs["min_mask_region_area"],  # Requires open-cv to run post-processing
        )
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb=10'
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.blip_model, self.vis_processors, _ = load_model_and_preprocess(
            name="blip2_t5", model_type="pretrain_flant5xl", is_eval=True, device=device
        )
        print("Initialized Blip2 Successfully!")

    def show_anns(self, anns, image):
        if len(anns) == 0:
            return
        sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    
        mask = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
        mask[:,:,3] = 0
        for ann in sorted_anns:
            m = ann['segmentation']
            color_mask = np.concatenate([np.random.random(3), [0.35]])
            mask[m] = color_mask

        mask = (mask * 255).astype(np.uint8)
        image_with_alpha = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        
        colored_image = cv2.addWeighted(image_with_alpha, 1, mask, 1, 0)
        colored_image = (colored_image * 255).astype(np.uint8)

        cv2.imwrite('highlighted_img.jpg', colored_image[:,:, :3])

    def create_masks(self, image):
        masks = self.mask_generator.generate(image)
        self.show_anns(masks, image)

    def create_masked_images(self, image, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # Generate the mask
        images = []
        masks = self.mask_generator.generate(image)
    
        # Apply each mask on the image
        for i, ann in enumerate(masks):
            mask = ann['segmentation']
            bbox = ann['bbox']
            # print(ann['bbox'])
            # Create an empty black image with the same size
            bbox_image = self.extract_bbox(image, ann['bbox'])
            print(bbox_image.shape)
            masked_image = np.zeros_like(image)
            
            # Ensure the mask is binary
            binary_mask = np.where(mask > 0, 1, 0)
            
            # Mask the image
            for c in range(3):  # For each color channel
                masked_image[:, :, c] = image[:, :, c] * binary_mask
            filename = "mask_{}.png".format(i)
            # Save the masked image to the output folder
            output_path = os.path.join(output_dir, filename)
            # masked_image_pil = Image.fromarray(masked_image)
            masked_image_pil = Image.fromarray(bbox_image)
            masked_image_pil.save(output_path)
            images.append(transformers.preprocess(masked_image_pil))
        return images

    def generate_blip2_captions(self, VIDEO_METADATA_FILE, DATA_FOLDER, OUTPUT_FILE):
        with open(VIDEO_METADATA_FILE, 'r') as file:
            data = file.read()
            interval_data = data.strip().split("\n")
            interval_data = [ast.literal_eval(interval) for interval in interval_data]
        print("Succesfully parsed the metadata...")
        def merge_two_dicts(x, y):
            z = x.copy()   # start with keys and values of x
            z.update(y)    # modifies z with keys and values of y
            return z
        with open(OUTPUT_FILE, 'w') as f:
            for interval in interval_data:
                start_frame = Timecode(interval["start"])
                end_frame = Timecode(interval["end"])
                candidate_frame = (end_frame.convert_timecode_to_sec() + start_frame.convert_timecode_to_sec()) // 2 
                FRAME_DIR = os.path.join(DATA_FOLDER, "Frame.{}.0".format(int(candidate_frame)))

                IMAGE_FILE = os.path.join(FRAME_DIR, "frame.jpg")    
                # load image + bboxes
                if os.path.exists(IMAGE_FILE):
                    image = cv2.imread(IMAGE_FILE)
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(image)
                    image = self.vis_processors["eval"](image).unsqueeze(0).to(self.device)
                    description_prompt = "Question: What is happening in this image?"
                    object_prompt = "Question: What unique objects are in this image? Describe them in detail."

                    content = self.blip_model.generate({"image": image, "prompt": description_prompt}, use_nucleus_sampling=True)

                    object_content = self.blip_model.generate({"image": image, "prompt": object_prompt}, use_nucleus_sampling=True)
                    new_dict = {'dense_caption_2': content, 'objects': object_content}
                    print(new_dict)
                    interval_metadata = merge_two_dicts(interval, new_dict)
                    f.write(str(interval_metadata) + '\n')

    def extract_candidate_frame_masks(self, frame_range, input_sketch=None):
        start_frame = frame_range["start"]
        end_frame = frame_range["end"]
        
        candidate_frame = (end_frame.convert_timecode_to_sec() + start_frame.convert_timecode_to_sec()) // 2 
        FRAME_DIR = os.path.join("Data", "Frame.{}.0".format(int(candidate_frame)))

        MASK_METADATA_FILE = os.path.join(FRAME_DIR, "mask_data.txt")
        IMAGE_FILE = os.path.join(FRAME_DIR, "frame.jpg")    
        # load image + bboxes
        image = cv2.imread(IMAGE_FILE)
        # print(image.shape)
        # image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        with open(MASK_METADATA_FILE, 'r') as f:
            data = f.read()
            mask_data = data.strip().split("\n")
            mask_data = [json.loads(mask) for mask in mask_data]

        input_images = []
        input_bboxes = []

        for annotation in mask_data:
            crop = self.extract_bbox(image, annotation['bbox'])
            masked_image_pil = Image.fromarray(crop)
            input_images.append(self.preprocess(masked_image_pil))
            input_bboxes.append(annotation['bbox'])

        filtered_images = []
        filtered_bboxes = []
        if input_sketch:
            # filter images that dont have iou with input sketch >threshold
            for i, bbox in enumerate(input_bboxes):
                if iou(bbox, input_sketch) > INTERSECTION_THRESHOLD:
                    filtered_images.append(input_images[i]) 
                    filtered_bboxes.append(bbox)

            input_bboxes = filtered_bboxes
            input_images = filtered_images

        return input_images, input_bboxes, candidate_frame, image

    def extract_caption_from_bbox(self, bbox):
        
        return


    def extract_related_crop(self, input_text, input_bboxes, input_images, frame_id, image):  
        images = torch.tensor(np.stack(input_images)).cuda()
        text = clip.tokenize(input_text).cuda()

        with torch.no_grad():
            image_features = self.model.encode_image(images).float()
            text_features = self.model.encode_text(text).float()

        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        similarity = text_features.cpu().numpy() @ image_features.cpu().numpy().T

        ind = np.unravel_index(np.argmax(similarity), similarity.shape)
        print(ind)
        cv2.imwrite("Image.jpg", image)

        crop = self.extract_bbox(image, input_bboxes[ind[1]])
        cv2.imwrite("Crop.jpg", crop)
        print("Frame: {}".format(frame_id))

        # print(ind.shape)
        return input_bboxes[ind[1]]

    def extract_bbox(self, img, bbox):
        x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
        return img[y:y+h, x:x+w]

def main():    
    image_processor = ImageProcessor()
    pair1 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/oYMAX90kNkU_5.txt", "Data10", "oYMAX90kNkU_5_combined.txt"]
    pair2 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/oYMAX90kNkU_10.txt", "Data10", "oYMAX90kNkU_10_combined.txt"]
    # pair3 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/OKQpOzEY_A4_5.txt", "Data3", "OKQpOzEY_A4_5_combined.txt"]
    # pair4 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/OKQpOzEY_A4_10.txt", "Data3", "OKQpOzEY_A4_10_combined.txt"]
    # pair5 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/kdN41iYTg3U_5.txt", "Data2", "kdN41iYTg3U_5_combined.txt"]
    # pair6 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/kdN41iYTg3U_10.txt", "Data2", "kdN41iYTg3U_10_combined.txt"]
    # pair7 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/4LdIvyfzoGY_5.txt", "Data", "4LdIvyfzoGY_5_combined.txt"]
    # pair8 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/4LdIvyfzoGY_10.txt", "Data", "4LdIvyfzoGY_10_combined.txt"]
    # pair9 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/3_nLdcHBJY4_5.txt", "Data5", "3_nLdcHBJY4_5_combined.txt"]
    # pair10 = ["/home/scrc/video-editing-pipeline/segment-anything/Ask-Anything/video_chat_with_ChatGPT/3_nLdcHBJY4_10.txt", "Data5", "3_nLdcHBJY4_10_combined.txt"]

    for pair in [pair1, pair2]:
        VIDEO_METADATA_FILE = pair[0]
        DATA_FOLDER = pair[1]
        OUTPUT_FILE = pair[2]
        image_processor.generate_blip2_captions(VIDEO_METADATA_FILE, DATA_FOLDER, OUTPUT_FILE)
        print("FINISHED PAIR SUCCESSFULLY")
    # frame_range = {'start': Timecode("00:03:00"), 'end': Timecode("00:03:10")}
    # input_images, input_bboxes, frame_id, img = image_processor.extract_candidate_frame_masks(frame_range)
    # image_processor.create_masks(img)
    # image_processor.extract_related_crop("cables on a table", input_bboxes, input_images, frame_id, img)

if __name__=='__main__':
    main()
