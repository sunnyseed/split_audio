# 第一阶段：下载并解压 FFmpeg 静态构建
FROM alpine as ffmpeg-builder
RUN apk add --no-cache curl
RUN curl -O https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar xvf ffmpeg-release-amd64-static.tar.xz

# 第二阶段：从 Python 官方镜像构建最终镜像
FROM python:3.10-slim
LABEL authors="zhuym"
COPY --from=ffmpeg-builder /ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg-builder /ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe
RUN chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN mkdir -m 777 SPF_audio.nosync
RUN mkdir -m 777 DOWNLOAD.nosync
RUN mkdir -m 777 log.nosync

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Define environment variable
ENV IS_DEBUG=False \
    UPLOAD_FOLDER=./SPF_audio.nosync \
    DOWNLOAD_FOLDER=./DOWNLOAD.nosync \
    MAX_CONTENT_LENGTH=100000000

# Run app.py when the container launches
CMD ["python", "trim_mute_api.py"]
