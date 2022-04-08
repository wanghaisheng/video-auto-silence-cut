import os
import ffmpeg
from PIL import Image
from statistics import mean
import subprocess
import shutil
from random import randint
import time
import argparse
import sys

parser = argparse.ArgumentParser(description='All avaliable variables that you can access')
parser.add_argument( '-fps', dest='frames', default=30, type=int, help='framerate of the video [int]')
parser.add_argument( '-cs', dest='chunk', default='5:9', type=str, 
        help='size for each frame chunk, xth out of every y pixels, smaller will take longer [x:y]')
parser.add_argument( '-cl', dest='length', default='5:7', type=str,
        help='range for how long each cut clips are [x:y]')
parser.add_argument( '-r', dest='resolution', default='1920:1080', type=str,
        help='resolution of the final video [w:h]')

args = parser.parse_args()

#Chunk Size
args.chunk = args.chunk.split(":")
center = int(args.chunk[0])
chunksize = int(args.chunk[1])

#Clip Length
args.length = args.length.split(":")
shortlength = int(args.length[0])
longlength = int(args.length[1])

#Resolution
args.resolution = args.resolution.split(":")
width = int(args.resolution[0])
height = int(args.resolution[1])

print(center, chunksize)
print(shortlength, longlength)
print(width, height)

# Delete all .gitkeeps
if os.path.exists('exports/.gitkeep'):
    os.remove('exports/.gitkeep')
if os.path.exists('frames/color/.gitkeep'):
    os.remove('frames/color/.gitkeep')
if os.path.exists('frames/gray/.gitkeep'):
    os.remove('frames/gray/.gitkeep')
if os.path.exists('imports/.gitkeep'):
    os.remove('imports/.gitkeep')

# Delete frame folders
color_folders = os.listdir('frames/color/') # Delete colored frames
for folders in color_folders:
    shutil.rmtree(f'frames/color/{folders}')

gray_folders = os.listdir('frames/gray/') # Delete gray frames
for folders in gray_folders:
    shutil.rmtree(f'frames/gray/{folders}')

start_time = time.time() # how long does it take to calculate averages
videos = os.listdir('imports/')
finframe_list = [] # global variable
vidavg_list = [] # global varialbe

if len(videos) == 0:
    print('No videos in imports/ folder')
    sys.exit()

# Generate colored and grayscale frames for all videos
def genframes():
    # Generate color frames
    for video in range(len(videos)):
        print(videos[video])
        os.mkdir(f'frames/color/video-{video}')
        subprocess.run(f'ffmpeg -i imports/{videos[video]} -vf fps={args.frames}/1 frames/color/video-{video}/frame%04d.jpg -hide_banner')

    # Generate grayscale frames
    for video in videos:
        os.mkdir(f'frames/gray/video-{videos.index(video)}')
        (
            ffmpeg
            .input(f'frames/color/video-{videos.index(video)}/frame%04d.jpg')
            .hue(s=0)
            .output(f'frames/gray/video-{videos.index(video)}/frame%04d.jpg')
            .overwrite_output()
            .run()
        )
genframes()

# Calculate frame averages and return start and end value
def avgframes():
    folders = os.listdir('frames/gray')
    numframes = 0
    totalavg = []
    global finframe_list
    global vidavg_list

    # Check chunks of every frame in the frames folder
    for folder in folders:
        vidfold = os.listdir(f'frames/gray/{folder}')
        vidavg = []
        totalframes = [] # just for curosity purposes
        global vidavg_list # first frame of clip
        global finframe_list # last frame of clip
        i = 0
        print(f'Calculating frame chunks for {folder}')
        for frame in vidfold:
            chunk = [] # Reset chunks for each frame
            currentframe = Image.open(f'frames/gray/{folder}/{vidfold[i]}')
            i += 1
            pixel = currentframe.load()
            totalframes.append(currentframe)

            for y in range(currentframe.size[1]): # check every y value
                if y % chunksize == center: # but only every 5th out of 9th
                    for x in range(currentframe.size[0]):
                        if x % chunksize == center:
                            chunk.append(pixel[x, y])
            numframes += 1
            
            # Get gray value of each chunk's pixel and divide by 255 to get 0-1 scale
            chunkavg = mean([i[0] for i in chunk])/225
            vidavg.append(chunkavg)
            chunkmax = max(vidavg)
            totalavg.append(chunkavg)

            currentframe.close() # Frees up memory

        print('avg:', mean(totalavg))
        print('max:', chunkmax)
        vidavg_list.append(vidavg.index(chunkmax))

        # Vary clip lengths
        finframe = (randint(shortlength, longlength) * args.frames) + vidavg.index(chunkmax)
        if finframe > len(vidavg):
            finframe = len(vidavg)
        finframe_list.append(finframe)

        print(f'Video is {len(vidavg)} frames long')
        print(f'First frame is {vidavg.index(chunkmax)}')
        print('Final frame would be:', finframe)

        print(f'--- {time.time() - start_time} seconds ---')
        print()

    print(mean(totalavg))
    print(max(totalavg))
    print('# of frames:', numframes)
avgframes()

# Export clips and combine them
def exportvideo():
    i = 0
    global vidavg_list
    global finframe_list
    print(vidavg_list)
    print(finframe_list)

    # Cut up videos into their clip form
    for video in videos:
        (
            ffmpeg
            .input(f'imports/{video}')
            .trim(start_frame=vidavg_list[i], end_frame=finframe_list[i])
            .filter('scale', width, height)
            .output(f'exports/video{i+1}.mp4', framerate=args.frames)
            .overwrite_output()
            .run()
        )
        i += 1

    # Combine all those new videos
    exports = os.listdir('exports/')
    for video in exports:
        exports = os.listdir('exports/')
        if not(len(exports) == 1): # Checks if the final output is the only one left
            if exports[0] == 'export.mp4':
                # rename to allow code to continue as it cannot replace it with the same name
                os.rename(f'exports/{exports[0]}', f'exports/vid0.mp4')
                exports = os.listdir('exports/')

            if not exports[0] == 'vid0.mp4': # If two clips have NOT been combined yet
                vid0 = ffmpeg.input(f'exports/{exports[0]}')
                vid1 = ffmpeg.input(f'exports/{exports[1]}')
                (
                    ffmpeg
                    .concat(
                        vid0,
                        vid1,
                    )
                    .output('exports/export.mp4', framerate=args.frames)
                    .run()
                )
                vidavg_list.pop(1) # as videos get combined,
                vidavg_list.pop(0) # remove their first and last frame positions
                finframe_list.pop(1)
                finframe_list.pop(0)
            else: # If two clips HAVE been combined
                vid0 = ffmpeg.input(f'exports/{exports[0]}')
                vid1 = ffmpeg.input(f'exports/{exports[1]}')
                if len(vidavg_list) > 1 and len(finframe_list) > 1:
                    vidavg_list.pop(0)
                    finframe_list.pop(0)
                (
                    ffmpeg
                    .concat(
                        vid0,
                        vid1,
                    )
                    .output('exports/export.mp4', framerate=args.frames)
                    .run()
                )
            # The newly created 'export.mp4' does not get counted yet in the exports list.
            os.remove(f'exports/{exports[1]}')
            os.remove(f'exports/{exports[0]}') # Delete [1] first so it can delete [0]
        else:
            print('All videos edited together!')
exportvideo()

# Delete frame folders
color_folders = os.listdir('frames/color/') # Delete colored frames
for folders in color_folders:
    shutil.rmtree(f'frames/color/{folders}')

gray_folders = os.listdir('frames/gray/') # Delete gray frames
for folders in gray_folders:
    shutil.rmtree(f'frames/gray/{folders}')

shutil.rmtree('frames/final') # Delete final folder
os.mkdir(f'frames/final')
