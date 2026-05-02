# MidiPlayer — 跨平台 MIDI 混音库方案设计

## 1. 项目定位

MidiPlayer 是一个**跨平台的轻量级 MIDI 方波混音库**，核心代码纯 C、零外部依赖、平台无关。它可以：

- 作为 **子仓库 (git submodule)** 被其他项目引入
- 在 **Host (Linux/macOS/Windows)** 上编译运行单元测试和 PC 端验证播放
- 在 **STM32F103** 上作为独立 example 运行（PWM 音频输出）
- 未来扩展到其他 MCU 平台

设计参考 FPBInject 的库集成模式：提供 `library.cmake` 导出源文件列表和编译选项，外部项目 include 即可使用。

## 2. 现状评估

### 2.1 当前项目 (MidiPlayer)

| 文件 | 状态 | 评价 |
|------|------|------|
| `scripts/midi_converter.py` | 已实现 | MIDI → C 数组，输出 `(start_time, freq, duration, volume)` 元组，可用但数据格式需改进 |
| `scripts/midi_player.py` | 已实现 | PC 端 Python 方波混音验证，依赖 pyaudio/numpy，不可移植 |
| `resources/*.mid` | 有 | 测试用 MIDI 文件 |

Python 播放器验证了混音可行性，但浮点运算 + 线程模型 + 44.1kHz 采样率不适合嵌入式。

### 2.2 参考项目 evade2 (ATMLib2)

ATMLib2 是为 AVR ATmega32U4 (16MHz) 设计的 4 通道软件合成器，核心思路完全适用：

- **方波合成**：相位累加器 + 阈值比较，无需查表，无浮点
- **整数混音**：4 通道 ±vol 加法 + DC 偏移，10-bit 输出，永不溢出
- **分层时钟**：16kHz ISR 做波形合成，/8 分频做音序 tick
- **Pattern 字节码**：紧凑的命令系统，支持效果（滑音、琶音等）

**问题**：ATMLib2 的振荡器层 (osc.c) 和平台层深度耦合（AVR 汇编 ISR、AVR 定时器寄存器），音序器层依赖 `PROGMEM`/`pgm_read_*`。需要拆分重构。

### 2.3 参考项目 FPBInject (构建系统 & 工程模式)

FPBInject 提供了值得参照的工程实践：

| 能力 | 实现方式 |
|------|---------|
| 跨平台构建 | `CMakeLists.txt` 顶层自动检测 NuttX/Bare-metal 环境 |
| 库集成 | `cmake/library.cmake` 导出 `SOURCES` / `INCLUDES` / `DEFINITIONS` |
| STM32 裸机 | `cmake/stm32f103.cmake` + `cmake/arm-none-eabi-gcc.cmake` 工具链 |
| 单元测试 | Host 编译真实源码 + mock 硬件，自研轻量测试框架 |
| CI | GitHub Actions：编译检查 + 单元测试 + 覆盖率报告 (lcov) |
| 平台层 | `Project/Platform/STM32F10x/` 完整的 StdPeriph + CMSIS + Timer/PWM 驱动 |

**可直接复用**：工具链 cmake、平台层、测试框架模式、CI 流程模式。

## 3. 架构设计

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                     外部项目 / Example                       │
│              (STM32 example / PC player / 游戏引擎)          │
├─────────────────────────────────────────────────────────────┤
│                    MidiPlayer 公共 API                       │
│         mp_init() / mp_play() / mp_stop() / mp_tick()       │
├──────────────────────┬──────────────────────────────────────┤
│   音序器 (sequencer) │         SFX 播放器 (可选)             │
│   MIDI 事件流解析     │         音效抢占通道                  │
├──────────────────────┴──────────────────────────────────────┤
│                  振荡器 / 混音器 (osc)                       │
│    N 通道方波合成 + LFSR 噪声 → 10-bit 混合采样值            │
├─────────────────────────────────────────────────────────────┤
│                    平台抽象层 (port)                          │
│   mp_port_pwm_init / mp_port_pwm_write / mp_port_timer_*   │
│   由使用者实现，库本身不包含任何硬件代码                       │
└─────────────────────────────────────────────────────────────┘
```

关键原则：
- **库核心 (Source/)** 是纯 C，不包含任何平台头文件，不调用任何硬件 API
- **平台抽象 (port)** 通过函数指针或弱符号由使用者注入
- **STM32 example** 是库的一个使用示例，不是库的一部分

### 3.2 核心模块划分

| 模块 | 文件 | 职责 | 平台依赖 |
|------|------|------|---------|
| 振荡器 | `Source/mp_osc.c/h` | 相位累加、方波生成、LFSR 噪声、多通道混音 | 无 |
| 音序器 | `Source/mp_sequencer.c/h` | 解析 MIDI 事件数据，驱动振荡器 | 无 |
| 音符表 | `Source/mp_note_table.c/h` | MIDI 音符号 → phase_increment 查找表 | 无 |
| 公共 API | `Source/mp_player.c/h` | 对外统一接口，组合振荡器和音序器 | 无 |
| 平台接口 | `Source/mp_port.h` | 定义平台需要实现的接口（仅头文件） | 无 |

### 3.3 平台抽象接口

```c
// Source/mp_port.h — 平台需要实现的接口

// 将混音采样值写入音频输出（PWM duty / DAC / 音频缓冲区）
// value: 0 ~ 1023 (10-bit)
void mp_port_audio_write(uint16_t value);

// 获取当前时间戳（毫秒），用于音序器计时
uint32_t mp_port_get_tick_ms(void);
```

STM32 example 中实现为 TIM PWM 写入；Host 测试中实现为 mock 或 PCM 缓冲区写入。

### 3.4 振荡器设计（从 ATMLib2 移植重构）

保留 ATMLib2 的核心算法，去掉所有平台耦合：

```c
// 配置项（编译期可调）
#define MP_OSC_CH_COUNT      4    // 通道数，可扩展到 8
#define MP_OSC_SAMPLE_RATE   16000
#define MP_OSC_PWM_BITS      10
#define MP_OSC_DC_OFFSET     (1 << (MP_OSC_PWM_BITS - 1))  // 512

// 每通道参数
struct mp_osc_params {
    uint8_t  mod;              // 占空比调制 (0~255, 127=50%)
    uint8_t  vol;              // 音量 (0~127)
    uint16_t phase_increment;  // 频率控制
};

// 核心函数 — 由定时器中断或音频回调调用
// 返回 10-bit 混合采样值 (0~1023)
uint16_t mp_osc_mix_sample(void);

// 通道控制
void mp_osc_set_freq(uint8_t ch, uint16_t phase_inc);
void mp_osc_set_vol(uint8_t ch, uint8_t vol);
void mp_osc_set_mod(uint8_t ch, uint8_t mod);
```

`mp_osc_mix_sample()` 是纯计算函数，不访问任何硬件，完全可测试。

### 3.5 音序器设计

两阶段实现：

**Phase 1（简化音序器）**：基于现有 `midi_converter.py` 的数据格式

```c
// 每个音符事件 8 字节
typedef struct {
    uint32_t start_time_ms : 25;  // 开始时间
    uint32_t volume        : 7;   // 音量
    uint16_t freq;                // phase_increment
    uint16_t duration_ms;         // 持续时间
} mp_note_event_t;

// 每个音轨
typedef struct {
    const mp_note_event_t *events;
    uint32_t event_count;
} mp_track_t;
```

**Phase 2（ATM 音序器，可选）**：移植 ATMLib2 的 Pattern 字节码系统，支持效果。作为可选模块编译。

### 3.6 数据流

```
离线 (PC)                              运行时
─────────                              ──────
*.mid ──→ midi_converter.py ──→ midi_data.h (const 数组)
                                           │
                                           ▼
                                    mp_sequencer_tick()
                                           │
                                    读取事件，控制通道开关
                                           │
                                           ▼
                              ┌── mp_osc_mix_sample() ──┐
                              │   (16kHz 调用)           │
                              │   返回 10-bit 采样值      │
                              └──────────┬───────────────┘
                                         │
                                         ▼
                              mp_port_audio_write(value)
                              ┌─────────────────────────┐
                              │ STM32: TIMx->CCRy = val  │
                              │ Host:  pcm_buffer[i]=val │
                              │ Test:  mock_record(val)  │
                              └─────────────────────────┘
```

## 4. 目录结构

```
MidiPlayer/
├── CMakeLists.txt                      # 顶层：自动检测 Host / STM32 环境
├── cmake/
│   ├── library.cmake                   # 库集成模块（外部项目 include 用）
│   ├── arm-none-eabi-gcc.cmake         # ARM 工具链（从 FPBInject 复制）
│   └── stm32f103.cmake                 # STM32 example 构建配置
│
├── Source/                             # ★ 库核心（纯 C，零平台依赖）
│   ├── mp_osc.c / mp_osc.h            # 振荡器 / 混音器
│   ├── mp_sequencer.c / mp_sequencer.h # 音序器
│   ├── mp_note_table.c / mp_note_table.h # 音符频率表
│   ├── mp_player.c / mp_player.h      # 公共 API
│   └── mp_port.h                       # 平台接口定义（仅头文件）
│
├── tests/                              # 单元测试（Host 编译）
│   ├── CMakeLists.txt
│   ├── test_framework.c / .h          # 轻量测试框架（参考 FPBInject）
│   ├── mock_port.c / .h               # mp_port 的 mock 实现
│   ├── test_osc.c                     # 振荡器测试
│   ├── test_sequencer.c              # 音序器测试
│   ├── test_note_table.c            # 音符表测试
│   ├── test_player.c                 # 集成测试
│   ├── test_main.c                   # 测试入口
│   └── run_tests.sh                  # 构建+运行+覆盖率脚本
│
├── examples/
│   └── stm32f103/                     # STM32 独立运行示例
│       ├── CMakeLists.txt             # 引用 cmake/stm32f103.cmake
│       ├── main.c                     # 应用入口
│       ├── port_stm32f103.c / .h      # mp_port 的 STM32 实现
│       ├── midi_data.h                # 转换好的乐谱数据
│       └── Platform/                  # 从 FPBInject 复制的平台层
│           └── STM32F10x/
│               ├── CMSIS/
│               ├── Config/
│               ├── Core/              # GPIO, Timer, PWM, Delay
│               ├── Startup/           # startup + 链接脚本
│               └── STM32F10x_StdPeriph_Driver/
│
├── scripts/
│   ├── midi_converter.py              # MIDI → C 数组转换器
│   └── midi_player.py                 # PC 端验证播放器
│
├── resources/
│   └── *.mid                          # MIDI 源文件
│
├── docs/
│   ├── STM32F103_MIDI_Player_方案设计.md
│   └── Summary of MIDI Messages.pdf
│
├── .github/
│   └── workflows/
│       └── ci.yml                     # GitHub Actions CI
│
├── .gitignore
├── LICENSE
└── README.md
```

### 4.1 关键设计决策

**为什么 Source/ 不包含 examples/stm32f103/Platform/?**

Platform 层（StdPeriph、CMSIS、启动文件）是 STM32 example 的依赖，不是库的一部分。其他项目引入 MidiPlayer 子仓库时，只需要 `Source/` 和 `cmake/library.cmake`，不需要携带任何 STM32 代码。

**为什么 tests/ 在顶层而不是 Source/ 下?**

测试需要 mock 平台接口，属于项目级别的验证，不是库源码的一部分。放顶层也方便 CI 直接定位。

## 5. 库集成方式

### 5.1 作为子仓库引入

```bash
# 外部项目
git submodule add https://github.com/xxx/MidiPlayer.git libs/MidiPlayer
```

```cmake
# 外部项目的 CMakeLists.txt
set(MP_OSC_CH_COUNT 4)  # 可选：配置通道数
include(libs/MidiPlayer/cmake/library.cmake)

target_sources(my_app PRIVATE ${MIDIPLAYER_SOURCES})
target_include_directories(my_app PRIVATE ${MIDIPLAYER_INCLUDES})
target_compile_definitions(my_app PRIVATE ${MIDIPLAYER_DEFINITIONS})
```

### 5.2 library.cmake 导出内容

```cmake
# cmake/library.cmake
set(MIDIPLAYER_SOURCES
    ${MP_ROOT}/Source/mp_osc.c
    ${MP_ROOT}/Source/mp_sequencer.c
    ${MP_ROOT}/Source/mp_note_table.c
    ${MP_ROOT}/Source/mp_player.c)

set(MIDIPLAYER_INCLUDES
    ${MP_ROOT}/Source)

set(MIDIPLAYER_DEFINITIONS "")

# 可选配置
if(DEFINED MP_OSC_CH_COUNT)
    list(APPEND MIDIPLAYER_DEFINITIONS MP_OSC_CH_COUNT=${MP_OSC_CH_COUNT})
endif()
```

使用者只需实现 `mp_port.h` 中声明的函数即可。

## 6. 单元测试策略

### 6.1 测试范围

| 模块 | 测试内容 | 方法 |
|------|---------|------|
| mp_osc | 单通道频率/音量/占空比、多通道混音、DC 偏移、边界值、LFSR 噪声 | 直接调用 `mp_osc_mix_sample()`，验证输出值 |
| mp_note_table | 音符号 → phase_increment 映射正确性 | 查表验证已知频率 |
| mp_sequencer | 事件触发时序、多音轨同步、音符开关 | mock 时间源，步进 tick，检查振荡器状态 |
| mp_player | 完整播放流程、暂停/恢复/停止 | 集成测试，mock port |

### 6.2 Mock 策略

```c
// tests/mock_port.c
static uint16_t mock_audio_buffer[4096];
static uint32_t mock_audio_index = 0;
static uint32_t mock_tick_ms = 0;

void mp_port_audio_write(uint16_t value) {
    if (mock_audio_index < 4096)
        mock_audio_buffer[mock_audio_index++] = value;
}

uint32_t mp_port_get_tick_ms(void) {
    return mock_tick_ms;
}

// 测试辅助
void mock_port_advance_ms(uint32_t ms) { mock_tick_ms += ms; }
void mock_port_reset(void) { mock_audio_index = 0; mock_tick_ms = 0; }
```

核心思路：振荡器是纯计算，不需要 mock；音序器通过 mock 时间源控制推进；port 层通过 mock 捕获输出。

### 6.3 测试框架

参考 FPBInject 的自研轻量框架（`test_framework.h`），不引入外部测试库依赖。提供 `TEST_ASSERT_EQUAL` / `RUN_TEST` / `TEST_SUITE_BEGIN` 等基础宏。

## 7. GitHub CI

```yaml
# .github/workflows/ci.yml
name: MidiPlayer CI

on:
  push:
    branches: [main, develop]
    paths: [Source/**, tests/**, cmake/**, examples/**, scripts/**]
  pull_request:
    branches: [main, develop]

jobs:
  # Host 单元测试 + 覆盖率
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: sudo apt-get install -y lcov bc
      - name: Run tests with coverage
        working-directory: tests
        run: |
          chmod +x run_tests.sh
          ./run_tests.sh coverage --threshold 80
      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: tests/build/coverage/

  # STM32 交叉编译检查（不烧录，只验证编译通过）
  stm32-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install ARM toolchain
        run: sudo apt-get install -y gcc-arm-none-eabi
      - name: Build STM32 example
        working-directory: examples/stm32f103
        run: |
          mkdir build && cd build
          cmake -DCMAKE_TOOLCHAIN_FILE=../../cmake/arm-none-eabi-gcc.cmake ..
          make -j$(nproc)

  # Python 转换工具验证
  converter-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install mido
        run: pip install mido
      - name: Test converter
        run: |
          python scripts/midi_converter.py \
            "resources/Pirates of the Caribbean - He's a Pirate.mid" \
            /tmp/test_output.c
          test -f /tmp/test_output.c
```

## 8. STM32F103 Example 技术细节

### 8.1 硬件映射

| 功能 | 定时器 | 配置 | 说明 |
|------|--------|------|------|
| PWM 输出 | TIM4_CH1 (PB6) | ARR=1023, PSC=0 | 72MHz/1024 ≈ 70.3kHz, 10-bit |
| 采样中断 | TIM3 | ARR=4499, PSC=0 | 72MHz/4500 = 16kHz |
| 系统节拍 | SysTick | 1kHz | 延时和音序器计时 |

### 8.2 port 实现

```c
// examples/stm32f103/port_stm32f103.c

void mp_port_audio_write(uint16_t value) {
    TIM4->CCR1 = value;  // 直接写 PWM 比较寄存器
}

uint32_t mp_port_get_tick_ms(void) {
    return millis();  // SysTick 驱动的毫秒计数
}
```

### 8.3 中断驱动

```c
// TIM3 16kHz 中断回调
void audio_sample_callback(void) {
    uint16_t sample = mp_osc_mix_sample();
    mp_port_audio_write(sample);

    // 每 8 次采样推进一次音序器 tick
    static uint8_t prescaler = 8;
    if (--prescaler == 0) {
        prescaler = 8;
        mp_sequencer_tick();
    }
}
```

### 8.4 硬件电路

```
STM32 PB6 (TIM4_CH1) ─── R(1kΩ) ───┬─── 音频输出
                                     │
                                   C(10nF)
                                     │
                                    GND

RC 低通截止频率 ≈ 15.9kHz
PWM 载波 ≈ 70.3kHz（与音频带宽间距 >4 倍，一阶 RC 足够）
```

### 8.5 资源预算

| 资源 | 预算 | 说明 |
|------|------|------|
| Flash (代码) | ~6KB | 库核心 + port + 平台层 |
| Flash (乐谱) | ~55KB | 剩余空间存 MIDI 数据 |
| RAM | ~1KB | 通道状态 + 栈 |
| CPU (ISR) | <3% | 16kHz × ~50 周期 / 72MHz |
| 定时器 | TIM3 + TIM4 | 采样 + PWM |
| GPIO | PB6 | PWM 输出 |

## 9. 实施步骤

### Phase 1：库骨架 + 构建系统 (Day 1)

1. 创建 `Source/` 目录，编写 `mp_osc.h/c`（振荡器核心，从 ATMLib2 移植重构）
2. 编写 `mp_port.h`（平台接口定义）
3. 编写 `cmake/library.cmake`
4. 编写 `CMakeLists.txt` 顶层
5. 验证：Host 编译通过

### Phase 2：单元测试框架 (Day 1-2)

1. 搭建 `tests/` 目录，复用 FPBInject 的测试框架模式
2. 编写 `mock_port.c`
3. 编写 `test_osc.c`：验证单通道方波输出、多通道混音、边界值
4. 编写 `run_tests.sh` + `tests/CMakeLists.txt`
5. 验证：`./run_tests.sh` 全部通过

### Phase 3：音序器 + 音符表 (Day 2-3)

1. 编写 `mp_note_table.c/h`（从 ATMLib2 的 noteTable 移植）
2. 编写 `mp_sequencer.c/h`（简化音序器，基于现有数据格式）
3. 编写 `mp_player.c/h`（公共 API）
4. 补充 `test_sequencer.c` / `test_player.c`
5. 改进 `midi_converter.py` 输出 phase_increment 而非频率

### Phase 4：STM32 Example (Day 3-4)

1. 从 FPBInject 复制 `Platform/STM32F10x/` 到 `examples/stm32f103/`
2. 从 FPBInject 复制 `cmake/arm-none-eabi-gcc.cmake`
3. 编写 `examples/stm32f103/CMakeLists.txt`
4. 编写 `port_stm32f103.c`（TIM3 中断 + TIM4 PWM）
5. 编写 `main.c`
6. 转换一首 MIDI 为 `midi_data.h`
7. 验证：编译烧录，听到音乐

### Phase 5：CI + 完善 (Day 4-5)

1. 编写 `.github/workflows/ci.yml`
2. 添加覆盖率门槛 (≥80%)
3. 添加 STM32 交叉编译检查
4. 完善 README
5. 清理 `.gitignore`（排除 `*_ref` 软链接等）

### Phase 6：进阶（可选）

- 移植 ATMLib2 的 Pattern 字节码音序器作为可选模块
- DMA 双缓冲方案
- 扩展波形类型（锯齿波、三角波）
- SD 卡读取乐谱

## 10. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 振荡器纯 C 重写后行为与 ATMLib2 不一致 | 中 | 单元测试覆盖所有边界情况，对比已知输出 |
| STM32F103C8 Flash 64KB 不够存大曲目 | 低 | ATM 格式数据紧凑；或换 STM32F103RCT6 (256KB) |
| 平台抽象层设计不够通用 | 中 | 先满足 STM32 + Host 两个平台，后续按需扩展 |
| CI 中无法验证实际音频输出 | 低 | 单元测试验证数值正确性；实际音质靠硬件验证 |

## 11. 参考资料

- `evade2_ref/ATMLib2_混音系统分析与STM32移植方案.md` — ATMLib2 深度技术分析
- `evade2_ref/Evade2/src/ATMLib2/` — ATMLib2 源码（osc.c, atm_synth.c, cmd_parse.c）
- `FPBInject_ref/cmake/library.cmake` — 库集成模式参考
- `FPBInject_ref/App/tests/` — 单元测试框架和 CI 流程参考
- `FPBInject_ref/Project/Platform/STM32F10x/` — STM32F103 平台层
