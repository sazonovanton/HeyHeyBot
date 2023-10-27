'''
Small python script to normalize volume of all wav files in a given directory
'''
import os
import subprocess

# Ask user for input directory
input_directory = input("Which directory contains your wav files? (default: ./data/audio)\n")
if not input_directory:
    input_directory = './data/audio'

# 1. Get loudness stats for all files
loudness_values = []
for file_name in os.listdir(input_directory):
    if file_name.endswith('.wav'):
        full_path = os.path.join(input_directory, file_name)
        print(f" - Processing {full_path}")
        result = subprocess.check_output(
            ['ffmpeg', '-i', full_path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
            stderr=subprocess.STDOUT
        ).decode('utf-8')
        # print(f" - Result: {result}")
        
        # Get loudness value
        for line in result.split('\n'):
            if "input_i" in line:
                data = line.split(':')[1].replace(',', '').replace('"', '').strip()
                data = float(data)
                # if inf or -inf
                if data == float('inf') or data == float('-inf'):
                    data = 0
                print(f"   Volume: {data:.2f} dBFS")
                loudness_values.append(data)
                break

print(f"\nFound loudness values for {len(loudness_values)} files\n")
if not loudness_values:
    print("\nNo files found")
    exit()

# 2. Calculate average loudness
avg_loudness = sum(loudness_values) / len(loudness_values)

print(f"\nAverage loudness: {avg_loudness:.2f} dBFS")
input(f"Press Enter to normalize volume of all files to this value or Ctrl+C to exit\n")

# 3. Normalize volume of all files
for file_name in os.listdir(input_directory):
    if file_name.endswith('.wav'):
        full_path = os.path.join(input_directory, file_name)
        temp_mp3_path = os.path.join(input_directory, file_name.replace('.wav', '_temp.mp3'))
        normalized_path = os.path.join(input_directory, file_name.replace('.wav', '_normalized.wav'))
        # Normalization
        subprocess.call(
            ['ffmpeg', '-i', full_path, '-af', f'loudnorm=I={avg_loudness}', '-y', temp_mp3_path]
        )
        # Convert back to wav (because of an issue with wav-wav conversion, i think there is some sort of bitrate issue)
        # TODO: fix wav-wav conversion
        subprocess.call(
            ['ffmpeg', '-i', temp_mp3_path, '-acodec', 'pcm_s16le', '-y', normalized_path]
        )
        # Delete temp mp3 file
        os.remove(temp_mp3_path)

print(f"\nVolume normalized, files saved to {input_directory}")
input(f"Press Enter to replace original files with normalized files or Ctrl+C to exit\n")

# 4. Заменим файлы file_normalized.wav на исходные file.wav
for file_name in os.listdir(input_directory):
    if file_name.endswith('_normalized.wav'):
        full_path = os.path.join(input_directory, file_name)
        original_path = os.path.join(input_directory, file_name.replace('_normalized.wav', '.wav'))
        print(f" - Replacing {original_path}")
        os.remove(original_path)
        os.rename(full_path, original_path)

print(f"\nVolume normalized to {avg_loudness:.2f} dBFS, original files replaced")
input(f"\nPress Enter to exit\n")