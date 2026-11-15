# ElevenLabs-Video-Audio-Studio

**AI 视频配乐与漫剧音效时间轴｜把 AI 视频画面、角色对白、BGM 和转场音效放进同一个声音制作流程。**

简体中文（默认） · [English](README.en.md) · 当前编辑器版本 v0.5

SoundFlow Studio 是一个本地运行的视频配乐与音效编辑器。你可以在同一个时间轴中生成或导入音乐与音效、调整片段位置，再让音乐在角色开口时自动降低音量。最终把配乐分轨交回剪辑软件，继续完成成片。

面向中国境内的 AI 视频创作者、AI 漫剧团队、动态漫画作者、短剧后期与独立开发者。用可运行、可二次开发的小工具，探索 ElevenLabs 的配乐、音效、语音与译配能力。画面可来自你已有的拍摄、动画或 AI 视频流程；本工具负责其文档所述的声音环节。

中文文档优先，界面目前以中文为主。可从内置样例、离线草案或模拟模式开始；具体可用方式见下文。

## AI 视频与漫剧实战场景

| 你的素材 | 建议操作 | 导出后怎样用 |
|---|---|---|
| AI 生成的 15–30 秒分镜视频 | 导入视频与已有对白，生成或导入配乐，再编排音效 | 导出配乐 WAV，放回剪映等剪辑软件 |
| 多角色对话的 AI 漫剧 | 复核讲话区间，设置人声避让，逐句检查音乐是否遮挡台词 | 导出音乐与音效分轨，交给后期继续混音 |
| 国风 / 玄幻动态漫画 | 文字生成氛围配乐，另做风声、转场等音效，并手动对齐画面 | 同一工程保留多个音轨，便于修改 |

### 可直接改写的声音需求

| 场景 | 创作描述示例 |
|---|---|
| 玄幻人物登场 | 20 秒纯器乐，稀疏鼓点和低频氛围，角色说话时减少密集旋律；结尾渐强 |
| 悬疑反转 | 克制的钢琴和弦乐，前段留白，转场时加入短促音效；避免长时间盖住人声 |
| 情绪向漫剧 | 温暖、节制、以人物对话为中心；配乐不要持续堆叠，句间再抬升情绪 |

这些描述是创作起点，不代表生成器会精确命中每个镜头；音效落点和配乐转折需在时间轴中检查。

## 为什么创作者会需要它

| 制作场景 | 可以怎样用 |
|---|---|
| 漫剧 / 动态漫画 | 角色对白出现时降低配乐，保留紧张感又让台词更容易听清 |
| 剧情短视频 | 把悬念铺垫、转场音效和情绪抬升放到不同轨道 |
| 产品演示 / 设计展示 | 用文字或画面生成配乐，再按展示节奏裁剪与淡入淡出 |
| 一组连续短片 | 批量导入后逐个进入编辑器精修，而不是只拿到一个不可编辑的混音结果 |

## 已实现的能力

- 音乐、音效和原视频对白多轨编辑；拖动、裁剪、分割、删除、音量、淡入淡出、吸附对齐。
- 每轨静音与人声避让开关；可编辑讲话区间和压低幅度、提前量、结束保持、恢复速度。
- 通过 ElevenLabs 从文字或视频生成音乐，从文字生成音效；也可直接导入已有音频。
- 点击“智能人声避让”时才触发 Scribe 识别；已有识别结果可复用，强制重新识别会再次请求 API。
- 浏览器 Web Audio 实时试听、避让前后对比、撤销/重做和自动保存。
- 输出配乐混音、音乐分轨、音效分轨、完整审听预混 WAV，以及时间轴工程 JSON。

**交付重点是音频和工程文件。当前 v0.5 编辑器导出流程不负责一键交付最终 MP4；可把 WAV 导入剪映、Premiere、DaVinci Resolve 等继续剪辑。**

界面目前以中文为主；本仓库提供中英文文档，尚未提供完整英文界面。

## 技术栈与环境

| 层 | 实现 |
|---|---|
| 前端 | 原生 HTML / CSS / JavaScript、Canvas 时间轴、Web Audio API |
| 本地后端 | Python、FastAPI、Uvicorn、Pydantic |
| API 通信 | HTTPX → ElevenLabs Music、Sound Effects、Scribe |
| 媒体处理 | FFmpeg / ffprobe；本地生成 WAV 混音 |
| 数据 | 本地 `runtime/` 文件、项目元数据与时间轴 JSON；无需数据库 |
| 推荐环境 | Python 3.11 / 3.12、FFmpeg、桌面浏览器；macOS / Linux / Windows |

## 快速开始

先把仓库下载或克隆到本机，在终端进入项目根目录（含 `app.py`、`requirements.txt`）。现有文件夹名称为 `SoundFlow_Studio_v0.5`。

### 下载项目

```bash
git clone https://github.com/lcnwys/elevenlabs-video-audio-studio.git
cd elevenlabs-video-audio-studio
```

也可在仓库页面选择 Code → Download ZIP，解压后进入包含 `requirements.txt` 的目录。安装命令均在该目录执行。

### 安装依赖

建议 Python **3.11 或 3.12**，并为每个项目单独建立虚拟环境。本项目是 Python 应用，**不需要 Node.js、npm 或独立数据库**。建议使用较新的 Chrome、Edge、Firefox 或 Safari；实际媒体解码能力取决于浏览器。

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果 PowerShell 的执行策略不允许激活，可直接使用 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`，后续启动命令也使用该 Python 路径。

FFmpeg 安装示例：

```bash
# macOS（已安装 Homebrew）
brew install ffmpeg
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install ffmpeg
```

Windows 请安装 FFmpeg 并将其 `bin` 目录加入 PATH。新开终端后确认：

```bash
ffmpeg -version
ffprobe -version
```

### 配置和启动

不调用 AI 时，可直接使用内置样例和本地编辑功能。需要真实生成或识别时，在启动服务的终端配置：

```bash
export ELEVENLABS_API_KEY="<your-elevenlabs-api-key>"
python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

PowerShell：

```powershell
$env:ELEVENLABS_API_KEY="<your-elevenlabs-api-key>"
python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

打开 **http://127.0.0.1:8765**；本地接口文档在 **http://127.0.0.1:8765/api/docs**。macOS 也可在已配置环境变量的终端执行 `./启动_Mac.command`。

| 配置项 | 说明 |
|---|---|
| `ELEVENLABS_API_KEY` | 仅在 AI 请求时需要，需有对应产品权限和额度 |
| `DUCKING_DATA_DIR` | 可选，本地任务目录，默认项目根目录的 `runtime/` |

**当前后端不自动读取 `.env`**；仅复制 `.env.example` 不会生效，请使用上述终端环境变量。填写的 Key 不应提交到仓库。

### 先做一个无需 API 的作品

1. 选择内置样例进入编辑器，播放并观察讲话区间。
2. 移动配乐、调整音乐音量，再启用人声避让比较效果。
3. 在合适的转场位置放入音效，调整淡入淡出。
4. 导出配乐 WAV、分轨或工程 JSON，交回你的剪辑流程。

也可直接打开仓库中的 `SoundFlow_Studio_v0.5_交互预览.html` 体验离线示例编辑。离线预览不执行 AI 生成；新素材的识别需要后端和 API。

## 给漫剧的一个配乐起点

> 20 秒悬疑漫剧配乐。开头保持克制，角色对白期间留出空间，最后 4 秒逐渐抬升张力；纯器乐，避免密集主旋律。音效单独制作，不盖住人声。

生成后仍应按镜头试听，把转折点与讲话区间手动对齐。API 生成并不保证准确命中每个剪辑点。

## 数据、成本和边界

| 操作 | 数据流向 / 费用 |
|---|---|
| 导入、时间轴编辑、FFmpeg 混音 | 本机处理；不需要 ElevenLabs 调用 |
| 视频生成音乐 | 视频及描述发送给 ElevenLabs；可能消耗额度 |
| Scribe 讲话识别 | 视频文件发送给 ElevenLabs，包含其中音画；可能消耗额度 |
| 文字音乐 / 音效生成 | 提示词发送给 ElevenLabs；可能消耗额度 |

Key 在后端从环境读取，通过 HTTPS 请求头发给 ElevenLabs；前端只获知是否已配置。`runtime/`、`.env` 和虚拟环境被 Git 忽略。这里的“本地运行”不代表“AI 请求零上传”，也不承诺上游零留存。

单视频目前限 **100 MB / 600 秒**。旧视频中已经混入的音乐不会被单独分离或移除；人声避让控制的是本工具添加的轨道。自动识别需人工复核；项目没有登录、多租户或自动任务清理。样例和用户作品的商用授权需分别核实。

## 开发入口

| 文件 / 目录 | 职责 |
|---|---|
| `app.py` | 项目、素材、识别和导出 API |
| `core.py` | 区间处理、FFmpeg 混音与媒体分析 |
| `elevenlabs_client.py` | Music / Scribe / Sound Effects 请求 |
| `frontend/` | 编辑器源代码 |
| `static/index.html` | 本地服务实际提供的构建页面 |
| `fc_worker.py` | 可复用的混音执行器，不代表已部署云函数 |

修改 `frontend/` 后执行 `python scripts/build_frontend.py`。开发测试命令为 `python -m pytest -q`；测试使用模拟响应，不等于真实账号 API 验收。

## 参考

- [ElevenLabs Video-to-Music](https://elevenlabs.io/docs/api-reference/music/video-to-music)
- [ElevenLabs Scribe 转录接口](https://elevenlabs.io/docs/api-reference/speech-to-text/convert)
- [FFmpeg 文档](https://ffmpeg.org/documentation.html)

## 本地部署与二次开发

以上命令启动的是**本机单用户服务**。终端保持运行即可使用，按 `Ctrl+C` 停止；重启时进入同一目录，激活同一虚拟环境，再执行启动命令。不同项目使用相同端口时，请停止前一个服务，或把 `--port` 改为未占用端口。

如需让服务长期运行，可由进程管理器管理同一条 Uvicorn 命令。正式向团队或公网提供服务之前，需要增加身份认证、用户数据隔离、任务队列、用量限制、日志脱敏和文件清理。当前仓库没有实现这些生产部署能力。

## 常见问题

| 问题 | 排查方向 |
|---|---|
| 找不到 `uvicorn` 或模块 | 确认已激活虚拟环境，并在项目根目录执行 `python -m pip install -r requirements.txt` |
| 找不到 FFmpeg / 无法读取媒体 | 检查 `ffmpeg -version`、`ffprobe -version`，安装后重启终端 |
| API 提示 401 / 403 | 检查本机 Key、对应产品权限和账号状态；不要把完整 Key 发到 Issue |
| API 提示 429 / 生成超时 | 检查额度、并发与网络；先用短素材验证，确认上游任务状态后再决定是否重新提交 |
| 浏览器无法播放 | 检查浏览器支持的封装与编码；可以下载到本地播放器检查 |
| 修改环境变量后仍未生效 | 在配置所在终端重启 Uvicorn |

## 参与改进

欢迎提交复现步骤、已脱敏报错和功能建议。漫剧对白被音乐遮住、译配字幕偏移、音乐情绪不匹配等具体场景，比单纯写“效果不好”更有帮助。请写明系统、Python / FFmpeg 版本、输入格式和最短复现流程；真实素材请先确认分享权限。

代码采用 [MIT License](LICENSE)。API 使用、生成内容、音视频素材与依赖软件的授权另行适用。

## AI 视频与漫剧声音工具箱

这四个项目可以独立使用，也可以通过导出文件串联。当前需要手动传递文件，并非已实现的一键工作流。

| 你现在遇到的问题 | 对应开源项目 | 主要交付 |
|---|---|---|
| 有画面，缺音乐方向 | [AI 音乐导演与视频配乐](https://github.com/lcnwys/elevenlabs-ai-music-video-scoring) | 音乐、编曲计划、创作草案 |
| 想编排配乐、音效和对白关系 | [AI 视频音频编辑器](https://github.com/lcnwys/elevenlabs-video-audio-studio) | 音频分轨、混音 WAV、工程 JSON |
| BGM 压住了角色台词 | [Auto Ducking 人声避让](https://github.com/lcnwys/elevenlabs-auto-ducking-video-audio) | 人声避让后的混音视频 |
| 中文视频需要其他语言版本 | [AI 视频翻译与配音](https://github.com/lcnwys/elevenlabs-video-dubbing-translation) | 译配视频、音频、上游可用字幕 |

例如：完成 AI 画面与对白 → 用音乐导演探索配乐 → 用音频编辑器编排音效 → 导出给剪映等软件完成成片；有其他语言需求时，再单独制作译配版本。

## 配套学习资源与二次开发

下面优先提供仓库内可读的源码、配置和样例，方便国内 AI 视频创作者先体验，再逐步理解技术。需要调用真实 AI 能力时，本机网络须能访问对应的 ElevenLabs API；AI 导演还需访问 OpenAI API。项目不内置网络代理或共享 Key。

| 项目内资源 | 能学到 / 复用什么 |
|---|---|
| [样例素材与讲话时间戳](samples/) | 无需先调用 API 即可体验样例混音 |
| [前端编辑器源码](frontend/) | 素材库、时间轴、波形、Web Audio 试听 |
| [混音核心](core.py) | 讲话区间、音量包络和 FFmpeg 混音 |
| [服务入口](app.py) | 项目与素材 API，便于研究接入自己的工具 |

AI 能力来自 ElevenLabs API；本项目侧重本地编辑器、交互和混音工作流的开发。

### 官方接口参考

| 你想了解什么 | 参考资料 |
|---|---|
| 让视频生成音乐 | [ElevenLabs Video-to-Music（英文）](https://elevenlabs.io/docs/api-reference/music/video-to-music) |
| 编辑音乐段落与计划 | [ElevenLabs Composition Plans（英文）](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans) |
| 提取讲话与词级时间戳 | [ElevenLabs Scribe（英文）](https://elevenlabs.io/docs/api-reference/speech-to-text/convert) |
| 创建翻译配音项目 | [ElevenLabs Dubbing（英文）](https://elevenlabs.io/docs/api-reference/dubbing/create-project) |

### 一起补充中文创作案例

欢迎在 Issue 中分享已脱敏的 AI 视频、漫剧、动态漫画或短剧声音问题，也欢迎提交经授权的短样片、中文提示词、安装排障和代码改进。建议注明：内容类型、系统环境、素材时长、遇到的问题及期望效果。公开分享前请去掉 Key、私人账号与客户敏感信息。

可以从“我遇到了什么具体问题”开始，不需要先理解所有音频技术。优先从上表中的实际源码、配置与示例入手，再逐步补充适合你的制作流程。

## ElevenLabs 接入与价格咨询

这个项目由独立开发者维护，希望帮助国内 AI 视频、AI 漫剧、动态漫画和短剧制作团队，把声音环节做成可试听、可修改、可复用的实际工作流。

如果你正在做**漫剧配音、短剧出海、视频配乐、音效制作、语音产品或批量 API 集成**，欢迎联系我，一起评估适合的产品、工作流和接入方式。我也可以提供**有价格优势的 ElevenLabs 方案报价**，具体方案、适用条件和价格以实际需求及单独报价为准。

**咨询邮箱：[lcnwys@gmail.com](mailto:lcnwys@gmail.com)**

为了更快给出建议，邮件中可以写明：

- 你在做什么内容或产品，以及一段已脱敏的需求说明。
- 每月预计视频/音频分钟数、目标语言、团队规模和是否需要 API。
- 希望先做样片验证，还是正在准备上线。

请不要在邮件或公开 Issue 中发送 API Key、账号密码或未获授权的客户素材。功能问题适合提 Issue；商务和价格咨询请发邮件。

> 这是独立社区项目，并非 ElevenLabs 官方产品。咨询和报价也不代表官方背书；ElevenLabs 的名称和商标归其权利人所有。
