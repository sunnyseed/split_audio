import datetime
from pathlib import Path
import os
import json
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from flask import Flask, request, jsonify, send_from_directory

from my_audio_process import find_long_silences, number_to_stars, milliseconds_to_hms, milliseconds_to_ms
from my_log import log, log_config

app = Flask(__name__)
# Configuration for uploads
IS_DEBUG = os.environ.get('IS_DEBUG', 'False').upper() == 'TRUE'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a'}
log(f"Debug Mode: {'On' if IS_DEBUG else 'Off'}", "", "WARNING")
'''
export IS_DEBUG='False'
export UPLOAD_FOLDER='./SPF_audio.nosync'
export DOWNLOAD_FOLDER='./DOWNLOAD.nosync'
export MAX_CONTENT_LENGTH='100000000' # 100MB
'''
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', './SPF_audio.nosync')
app.config['DOWNLOAD_FOLDER'] = os.environ.get('DOWNLOAD_FOLDER', './DOWNLOAD.nosync')
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))  # Limit file size 100MB

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['DOWNLOAD_FOLDER']):
    os.makedirs(app.config['DOWNLOAD_FOLDER'])


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part', 'code': 400})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'message': 'No selected file', 'code': 400})

    # Parameters extracted from form data
    # 多少 DB 算静音？-20 比 -30 容忍度大，估计为低于平均 x
    # m4a -30db +3000 / 1500; mp3 -35db +4000; 语文 -35db +4000;
    silence_db = float(request.form.get('silence_db', -35.0))  # 静音的分贝数
    silence_length = int(request.form.get('silence_length', 4000))  # 识别为静音的最小长度
    voice_ignore = int(request.form.get('voice_ignore', 5000))  # 忽略两段静音间的人声的间隔
    silence_chunk = int(request.form.get('silence_chunk', 500))  # 单个块大小，数值大，容忍度大
    combine_voice = int(request.form.get('combine_voice', 5 * 60 * 1000))  # 将小于 n 的人声组合在一起
    zoom_level = int(request.form.get('zoom_level', 5 * silence_length))  # 显示缩放比例,SILENCE_LENGTH 的倍数
    log(f"Parameters: silence_db: {silence_db}, silence_length: {silence_length}, voice_ignore: {voice_ignore}, "
        f"silence_chunk: {silence_chunk}, combine_voice: {combine_voice}, zoom_level: {zoom_level}")

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        formatted_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{formatted_time}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        results = process_audio(file_path, app.config['DOWNLOAD_FOLDER'], silence_db, silence_length, voice_ignore,
                                silence_chunk, combine_voice, zoom_level)
        return jsonify(results)

    return jsonify({'message': 'File type not allowed', 'code': 422})


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Serve a file from the download directory."""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)


def process_audio(file_path, output_path, silence_db, silence_length, voice_ignore, silence_chunk,
                  combine_voice, zoom_level):
    # Process the audio file with the provided parameters

    file_path = Path(file_path)
    output_path = Path(output_path)
    if file_path.suffix == ".m4a":
        file_format = "mp4"
    else:
        file_format = file_path.suffix[1:]

    _base_path = file_path.parent

    audio = AudioSegment.from_file(file_path, format=file_format)
    # 打印音频长度
    audio_duration = len(audio)
    log(f"检测：{file_path.name} [{milliseconds_to_hms(audio_duration)}]", "", "info")
    silences, voices = find_long_silences(audio, voice_ignore, silence_db, silence_chunk, silence_length)

    # Assign a type and combine silences and voices
    combined = [('Si', start, end) for start, end in silences] + [('Vo', start, end) for start, end in voices]
    # Sort by start time
    sorted_combined = sorted(combined, key=lambda x: x[1])

    # 打印细节
    if IS_DEBUG:
        for idx, (item_type, start, end) in enumerate(sorted_combined):
            _line = f"{idx:03}.{milliseconds_to_hms(start)} {item_type} [{milliseconds_to_ms(end - start)}]"
            asterisks = number_to_stars(item_type, end - start, zoom_level)
            if item_type == "Si":
                _line += f" {asterisks.rjust(20, ' ')}|"
            else:
                _line += f"{' ' * 21}|{asterisks}"
            log(_line)

        # Calculate max, min, and average of durations
        durations = [(end - start) for start, end in voices]

        if durations:
            max_duration = milliseconds_to_ms(max(durations))
            min_duration = milliseconds_to_ms(min(durations))
            avg_duration = milliseconds_to_ms(int(sum(durations) / len(durations)))

            log(f"人声: MAX: {max_duration} MIN: {min_duration} AVG: {avg_duration}")

        # Calculate max, min, and average of durations
        durations = [(end - start) for start, end in silences]

        if durations:
            max_duration = milliseconds_to_ms(max(durations))
            min_duration = milliseconds_to_ms(min(durations))
            avg_duration = milliseconds_to_ms(int(sum(durations) / len(durations)))

            log(f"静音: MAX: {max_duration} MIN: {min_duration} AVG: {avg_duration}")

    # 人声部分保存为新的音频文件
    current_segment = AudioSegment.empty()  # Current audio segment that will be appended until it reaches 5000ms
    current_length = 0  # Total length of current_segment
    output_idx = 1  # For naming the output files

    sum_duration = 0
    links = []
    for idx, (start, end) in enumerate(voices):
        segment = audio[start:end]
        current_segment += segment
        current_length += len(segment)

        # When the segment exceeds 5000ms, or it's the last segment
        if current_length >= combine_voice or idx == len(voices) - 1:
            output_file = output_path.joinpath(f"{file_path.stem}_{output_idx:03}{file_path.suffix}")
            # Save the current segment to a file
            current_segment.export(output_file, format=file_format)

            sum_duration += current_length
            log(f"Output: {output_file.stem} [{milliseconds_to_ms(current_length)}]{' ' * 5}>"
                f"{number_to_stars('Vo', current_length, zoom_level)}")

            # 生成下载链接
            download_link = f"{output_file.name}"
            links.append(download_link)

            # Reset for the next combined segment
            current_segment = AudioSegment.empty()
            current_length = 0
            output_idx += 1

    result_output = {'message': f"Split: {output_idx}, "
                                f"Coverage: {round(sum_duration / audio_duration * 100):>2}%, "
                                f"Duration: {milliseconds_to_hms(sum_duration)}",
                     'download_links': links,
                     'code': 200}
    log(json.dumps(result_output), "", "INFO")

    return result_output


if __name__ == '__main__':
    if IS_DEBUG:
        log_config('trim_mute_api.log', 'DEBUG')
    else:
        log_config('trim_mute_api.log', 'WARNING')
    app.run(host='0.0.0.0', port=5001, debug=IS_DEBUG)
