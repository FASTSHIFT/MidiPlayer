import argparse
import mido
import numpy as np
import pyaudio
import time
import threading

# 全局变量和线程锁
active_notes = []
lock = threading.Lock()
SAMPLE_RATE = 44100
CHUNK_SIZE = 1024

def midi_to_freq(note):
    """将MIDI音符编号转换为频率"""
    return 440.0 * (2.0 ** ((note - 69) / 12.0))

def audio_callback(in_data, frame_count, time_info, status):
    """音频回调函数，生成方波信号"""
    global active_notes
    t = np.arange(frame_count) / SAMPLE_RATE
    mixed = np.zeros(frame_count, dtype=np.float32)
    
    with lock:
        current_notes = active_notes.copy()
    
    # 生成所有活动音符的方波并混合
    for note in current_notes:
        freq = midi_to_freq(note)
        phase = (freq * t) % 1.0
        square = np.where(phase < 0.5, 1.0, -1.0)
        mixed += square * 0.1  # 降低振幅避免削波
    
    # 归一化处理
    if len(current_notes) > 0:
        mixed /= len(current_notes)
    
    return (mixed.astype(np.float32).tobytes(), pyaudio.paContinue)

def process_midi_events(filename):
    """处理MIDI事件并控制音符开关"""
    mid = mido.MidiFile(filename)
    tempo = 500000  # 默认速度（微秒/四分音符）
    current_time = 0.0
    events = []
    
    # 合并所有音轨并计算事件时间
    for msg in mido.merge_tracks(mid.tracks):
        delta_ticks = msg.time
        delta_time = mido.tick2second(delta_ticks, mid.ticks_per_beat, tempo)
        current_time += delta_time
        
        if msg.type == 'set_tempo':
            tempo = msg.tempo
        
        events.append((current_time, msg))
    
    # 等待音频初始化
    time.sleep(0.5)
    start_time = time.time()
    
    # 按事件时间处理消息
    for event_time, msg in events:
        # 计算需要等待的时间
        elapsed = time.time() - start_time
        wait_time = event_time - elapsed
        if wait_time > 0:
            time.sleep(wait_time)
        
        # 处理音符事件
        if msg.type in ['note_on', 'note_off']:
            note = msg.note
            with lock:
                if msg.type == 'note_on' and msg.velocity > 0:
                    if note not in active_notes:
                        active_notes.append(note)
                else:
                    if note in active_notes:
                        active_notes.remove(note)

def main():
    parser = argparse.ArgumentParser(description='8-bit方波MIDI播放器')
    parser.add_argument('filename', help='MIDI文件路径')
    args = parser.parse_args()
    
    # 初始化音频流
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=SAMPLE_RATE,
                    output=True,
                    frames_per_buffer=CHUNK_SIZE,
                    stream_callback=audio_callback)
    
    try:
        stream.start_stream()
        # 启动MIDI处理线程
        midi_thread = threading.Thread(target=process_midi_events, args=(args.filename,))
        midi_thread.start()
        
        # 保持主线程运行
        while stream.is_active():
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == '__main__':
    main()
