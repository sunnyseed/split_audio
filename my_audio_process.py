from typing import List, Tuple


# Record the start and end times of continuous silence periods over 5 seconds
def detect_silence_periods(sound, silence_threshold_in_decibels, chunk_size, silence_size) -> List[Tuple[int, int]]:
    silence_duration = 0
    silence_periods = []  # store tuples of (start_time, end_time) of silence periods

    assert chunk_size > 0  # to avoid infinite loop

    current_time = 0
    silence_start = 0  # used to record the start time of silence exceeding 5 seconds
    silence_head = True

    while current_time < len(sound):
        if sound[current_time:current_time + chunk_size].dBFS < silence_threshold_in_decibels:
            silence_duration += chunk_size
            if silence_head:
                silence_start = current_time
                silence_head = False
        else:
            if silence_duration >= silence_size:
                silence_end = current_time
                silence_periods.append((silence_start, silence_end))
                # print(f"+ {milliseconds_to_hms(silence_start)} -> {milliseconds_to_hms(silence_end)} [{silence_duration}]")
            silence_head = True
            silence_start = 0
            silence_duration = 0

        current_time += chunk_size

    # Check for silence at the end of the sound
    if silence_duration >= silence_size:
        silence_end = len(sound)
        silence_periods.append((silence_start, silence_end))
        # print(f"+ {milliseconds_to_hms(silence_start)} -> {milliseconds_to_hms(silence_end)} [{silence_duration}]")

    return silence_periods


# 检测并返回音频文件中超过5秒的静音部分的开始时间
def find_long_silences(audio, ignore_size, silence_db, silence_chunk, silence_length) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:

    silence_starts = detect_silence_periods(audio, silence_db, silence_chunk, silence_length)

    # 合并短于5000毫秒的间隔
    combined_silences = []
    if silence_starts:
        start, end = silence_starts[0]
        for next_start, next_end in silence_starts[1:]:
            if next_start - end < ignore_size:
                # print(f"- {milliseconds_to_hms(end)} +> {milliseconds_to_hms(next_start)} [{next_start - end}]")
                end = next_end
            else:
                combined_silences.append((start, end))
                start, end = next_start, next_end
        combined_silences.append((start, end))

    # 获取非静音段的起止时间
    non_silences = []
    last_end = 0
    for silence_start, silence_end in combined_silences:
        if silence_start - last_end > 0:  # 去头
            non_silences.append((last_end, silence_start))
            # print(f"Voice   {milliseconds_to_hms(last_end)} to {milliseconds_to_hms(silence_start)} [{silence_start - last_end}]")
        last_end = silence_end
    if len(audio) - last_end > 0:  # 去尾
        non_silences.append((last_end, len(audio)))

    return combined_silences, non_silences


# 按类型转换为图标
def number_to_stars(item_type: str, duration: int, zoom_level: int = 5) -> str:
    """
    Convert a number to a string of asterisks or dashes based on the item type and duration.
    Parameters
    ----------
    item_type
    duration
    zoom_level

    Returns
    -------

    """
    # 缩放比例
    duration = duration // zoom_level
    if item_type == "Si":
        if duration > 20:
            asterisks = f"<{'-' * 19}"
        else:
            asterisks = f"{'-' * duration}"
    else:
        asterisks = f"{'*' * duration}"

    return asterisks


# 毫秒转 hh:mm:ss
def milliseconds_to_hms(ms: int) -> str:
    """
    Convert milliseconds to hours, minutes, and seconds.
    """
    ms = int(ms)
    seconds, milliseconds = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


# 毫秒转 mm:ss
def milliseconds_to_ms(ms: int) -> str:
    """
    Convert milliseconds to minutes and seconds.
    """
    ms = int(ms)
    seconds, milliseconds = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{minutes:02}:{seconds:02}"
