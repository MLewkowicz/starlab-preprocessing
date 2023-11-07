import os

def rename_folders(base_directory):
    for foldername in os.listdir(base_directory):
        if foldername.startswith("Frame.") and foldername.count('.') == 2:
            parts = foldername.split('.')
            if parts[1].isdigit() and parts[2].isdigit():  # Ensure the frame number and the integer at the end are digits
                new_foldername = "Frame.{}.0".format(parts[1])
                old_folder_path = os.path.join(base_directory, foldername)
                new_folder_path = os.path.join(base_directory, new_foldername)
                os.rename(old_folder_path, new_folder_path)
                print(f"Renamed {old_folder_path} to {new_folder_path}")

base_directory = '/home/scrc/video-editing-pipeline/segment-anything/scripts/Data8'  # Replace with your directory
rename_folders(base_directory)