from transcript_parser import *
import os
import ast

def merge_two_dicts(x, y):
    z = x.copy()   # start with keys and values of x
    z.update(y)    # modifies z with keys and values of y
    return z

timecoded_transcript = format_altered_transcript("Tih8I3Klw54.en.vtt", "output.txt")
OUTPUT_FILE = "Tih8I3Klw54_10_fixed_combined.txt"
VIDEO_METADATA_FILE = "/home/scrc/video-editing-pipeline/segment-anything/scripts/Tih8I3Klw54_10_combined.txt"

with open(VIDEO_METADATA_FILE, 'r') as file:
            data = file.read()
            interval_data = data.strip().split("\n")
            interval_data = [ast.literal_eval(interval) for interval in interval_data]

with open(OUTPUT_FILE, 'w') as f:
    for interval in interval_data:
        start_frame = Timecode(interval["start"])
        end_frame = Timecode(interval["end"])

        transcript = extract_range(start_frame, end_frame, timecoded_transcript)
        interval['transcript'] = transcript["text"]
        f.write(str(interval) + '\n')