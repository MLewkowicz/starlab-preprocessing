import os
import subprocess

def get_video_paths_from_directory(directory, extensions=['.mp4', '.avi', '.mkv', '.mov']):
    """
    Get all video paths from the specified directory based on the provided extensions.
    """
    video_files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.splitext(f)[1].lower() in extensions]
    return video_files

def split_video(video_path, output_dir, clip_length=30):
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get the video's total duration
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {video_path}"
    total_duration = float(subprocess.check_output(cmd, shell=True))

    # Calculate the number of clips
    num_clips = int(total_duration / clip_length) + (1 if total_duration % clip_length else 0)

    # Split the video
    for i in range(num_clips):
        start_time = i * clip_length
        output_file = os.path.join(output_dir, f"clip_{i + 1}.mp4")
        cmd = f"ffmpeg -i {video_path} -ss {start_time} -t {clip_length} -c copy {output_file}"
        subprocess.call(cmd, shell=True)

if __name__ == "__main__":
    directory = ""
    video_path = "kdN41iYTg3U.mp4"
    output_dir = "clips3"
    split_video(video_path, output_dir)

