from moviepy.editor import VideoFileClip

def split_video(video_path, output_folder, clip_duration=10):
    # Load the video
    video = VideoFileClip(video_path)
    video_duration = int(video.duration)

    # Split the video into 30-second clips
    for i in range(0, video_duration, clip_duration):
        start_time = i
        end_time = min(i + clip_duration, video_duration)
        clip = video.subclip(start_time, end_time)
        clip.write_videofile(f"{output_folder}/clip_{i//clip_duration + 1}.mp4", codec="libx264")

    print("Video splitting completed!")

if __name__ == "__main__":
    video_path = "oYMAX90kNkU.mp4"  # Replace with the path to your video
    output_folder = "clips10"   # Replace with the path to your desired output folder
    split_video(video_path, output_folder)
