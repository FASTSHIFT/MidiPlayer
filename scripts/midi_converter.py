import mido
import argparse

def midi_to_freq(note):
    """将MIDI音符编号转换为频率"""
    return 440.0 * (2.0 ** ((note - 69) / 12.0))

def parse_midi(filename):
    # 加载MIDI文件
    mid = mido.MidiFile(filename)
    tracks = []
    
    # 遍历每个音轨
    for track in mid.tracks:
        notes = []
        current_time = 0.0
        tempo = 500000  # 默认速度（微秒/四分音符）
        note_on_times = {}
        note_on_velocities = {}
        
        # 遍历每个消息
        for msg in track:
            delta_time = mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
            current_time += delta_time
            
            # 更新速度
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                continue
            
            # 处理音符开始消息
            if msg.type == 'note_on' and msg.velocity > 0:
                note_on_times[msg.note] = current_time
                note_on_velocities[msg.note] = msg.velocity
                continue
            
            # 处理音符结束消息或音速为0的音符开始消息
            if msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in note_on_times:
                    start_time = note_on_times[msg.note]
                    duration = (current_time - start_time) * 1000  # 持续时间转为毫秒
                    frequency = midi_to_freq(msg.note)  # 获取频率
                    velocity = note_on_velocities[msg.note]  # 获取音量
                    notes.append((start_time, frequency, duration, velocity))
                    del note_on_times[msg.note]
                    del note_on_velocities[msg.note]
        
        tracks.append(notes)
    
    return tracks

def generate_c_file(tracks, output_filename):
    with open(output_filename, 'w') as f:
        f.write("#include <stdint.h>\n\n")
        f.write("typedef struct {\n")
        f.write("    uint32_t start_time : 25;\n")
        f.write("    uint32_t volume : 7;\n")
        f.write("    uint16_t freq;\n")
        f.write("    uint16_t duration;\n")
        f.write("} Audio_Data_t;\n\n")
        
        f.write("typedef struct {\n")
        f.write("    const Audio_Data_t* data;\n")
        f.write("    uint32_t size;\n")
        f.write("} Audio_TrackData_t;\n\n")
        
        for i, track in enumerate(tracks):
            f.write(f"const Audio_Data_t track_{i + 1}_data[] = {{\n")
            for start_time, frequency, duration, velocity in track:
                # 将开始时间转换为整数
                start_time_int = int(start_time * 1000)
                # 将频率转换为整数
                freq_int = int(frequency)
                # 将持续时间转换为整数（假设以毫秒为单位）
                duration_int = int(duration)
                # 音量保持为uint8_t
                volume_int = int(velocity)
                f.write(f"    {{ {start_time_int}, {volume_int}, {freq_int}, {duration_int}, }},\n")
            f.write("};\n\n")
        
        f.write("const Audio_TrackData_t all_track_data[] = {\n")
        for i in range(len(tracks)):
            f.write(f"    {{ track_{i + 1}_data, sizeof(track_{i + 1}_data) / sizeof(track_{i + 1}_data[0]) }},\n")
        f.write("};\n\n")

# 命令行参数解析
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="解析MIDI文件并将每个音轨拆分成：[开始时间(毫秒)]， [频率], [持续时间（毫秒）], [音量]的形式，然后生成C文件")
    parser.add_argument('filename', type=str, help='MIDI文件的路径')
    parser.add_argument('output_filename', type=str, help='生成的C文件的路径')
    args = parser.parse_args()
    
    tracks = parse_midi(args.filename)
    generate_c_file(tracks, args.output_filename)
