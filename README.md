<p align="center">
  <img src="static/images/logo.png" alt="logo" width="500">
</p>

<div align="center">
  <h1>Mobile-Agent-E: 自进化移动助手，专为复杂任务设计</h1>
</div>

<!-- # Mobile-Agent-E: 自进化移动助手，专为复杂任务设计 -->
<!-- <div align="center">
    <a href="https://huggingface.co/spaces/junyangwang0410/Mobile-Agent"><img src="https://huggingface.co/datasets/huggingface/badges/raw/main/open-in-hf-spaces-sm-dark.svg" alt="Open in Spaces"></a>
    <a href="https://modelscope.cn/studios/wangjunyang/Mobile-Agent-v2"><img src="assets/Demo-ModelScope-brightgreen.svg" alt="Demo ModelScope"></a>
  <a href="https://arxiv.org/abs/2406.01014 "><img src="https://img.shields.io/badge/Arxiv-2406.01014-b31b1b.svg?logo=arXiv" alt=""></a>
  <a href="https://huggingface.co/papers/2406.01014"><img src="https://img.shields.io/badge/🤗-Paper%20In%20HF-red.svg" alt=""></a>
</div>
<br> -->
<p align="center">
<a href="https://x-plug.github.io/MobileAgent">🌐 Homepage</a>
•
<a href="https://arxiv.org/abs/2501.11733">🗃️ arXiv</a>
•
<a href="https://x-plug.github.io/MobileAgent/Mobile-Agent-E/static/pdf/mobile_agent_e_jan20_arxiv.pdf">📃 PDF </a>
•
<a href="https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-E" >💻 Code</a>
•
<a href="https://huggingface.co/datasets/mikewang/mobile_eval_e" >🤗 Data</a>


<div align="center">
Zhenhailong Wang<sup>1†</sup>, Haiyang Xu<sup>2†</sup>, Junyang Wang<sup>2</sup>, Xi Zhang<sup>2</sup>,
Ming Yan<sup>2</sup>, Ji Zhang<sup>2</sup>, Fei Huang<sup>2</sup>, Heng Ji<sup>1†</sup>
</div>
<br>
<div align="center">
{wangz3, hengji}@illinois.edu, shuofeng.xhy@alibaba-inc.com
</div>
<br>
<div align="center">
<sup>1</sup>University of Illinois Urbana-Champaign   <sup>2</sup>Alibaba Group
</div>
<div align="center">
<sup>†</sup>Corresponding author
</div>
<br>

<p align="center">
  <img src="static/images/new_teaser.png" alt="logo" width="900">
</p>

## 💻 环境设置
❗我们仅在 **Android OS** 上进行了测试。Mobile-Agent-E 目前不支持 **iOS**。

❗所有实验都在 Samsung Galaxy A15 设备上完成，在不同设备上的性能可能会有所差异。我们建议用户根据自己的设备和任务自定义初始提示。

### 安装
```
conda create -n mobile_agent_e python=3.10 -y
conda activate mobile_agent_e
pip install -r requirements.txt
```

### 准备通过 ADB 连接移动设备

1. 下载 [Android Debug Bridge](https://developer.android.com/tools/releases/platform-tools?hl=en)。
2. 在您的 Android 手机上打开 ADB 调试开关，需要先在开发者选项中启用。
3. 用数据线将手机连接到电脑，并选择"传输文件"。
4. 测试您的 ADB 环境：```/path/to/adb devices```。如果显示已连接的设备，则准备工作完成。
5. 如果您使用的是 MAC 或 Linux 系统，请确保开启 adb 权限：```sudo chmod +x /path/to/adb```
6. 如果您使用的是 Windows 系统，路径将是 ```xx/xx/adb.exe```

### 在您的移动设备上安装 ADB Keyboard
1. 下载 ADB keyboard [apk](https://github.com/senzhk/adbkeyboard/blob/master/adbkeyboard.apk) 安装包。
2. 点击 apk 在您的移动设备上安装。
3. 在系统设置中将默认输入法切换为"ADB Keyboard"。

### Agent 配置
请参考 `inference_agent_E.py` 中的 `# Edit your Setting #` 部分来自定义您的 agent 的所有配置。您可以直接修改宏定义，或通过设置以下环境变量来控制其中一些配置：

1. ADB 路径
    ```
    export ADB_PATH="your/path/to/adb"
    ```
2. 主干模型和 API 密钥：您可以从 OpenAI、Gemini、Claude、Qwen 和 GLM 中选择；按如下方式设置相应的密钥：
    ```
    export BACKBONE_TYPE="OpenAI"
    export OPENAI_API_KEY="your-openai-key"
    ```
    ```
    export BACKBONE_TYPE="Gemini"
    export GEMINI_API_KEY="your-gemini-key"
    ```
    ```
    export BACKBONE_TYPE="Claude"
    export CLAUDE_API_KEY="your-claude-key"
    ```
    ```
    export BACKBONE_TYPE="Qwen"
    export QWEN_REASONING_API_KEY="your-qwen-reasoning-key"
    ```
    ```
    export BACKBONE_TYPE="GLM"
    export GLM_API_KEY="your-glm-api-key"
    ```
3. GLM-4.5-x 模型配置（新增）：
    - GLM-4.5-x 是智谱AI推出的新旗舰模型，具有强大的推理、编码和智能体能力
    - 按照此链接获取 [智谱AI API Key](https://docs.bigmodel.cn/cn/guide/start/quick-start)
    - 设置 GLM API 密钥：
        ```
        export BACKBONE_TYPE="GLM"
        export GLM_API_KEY="your-glm-api-key"
        ```
    - GLM-4.5-x 支持深度思考模式，提供更深层次的推理分析
    - 模型特点：高性能、强推理、极速响应，适合智能体应用

4. 感知器：默认情况下，感知器中的图标描述模型（`CAPTION_MODEL`）使用来自 Qwen API 的"qwen-vl-max"：
    - 按照此链接获取 [Qwen API Key](https://help.aliyun.com/document_detail/2712195.html?spm=a2c4g.2712569.0.0.5d9e730aymB3jH)
    - 设置 Qwen API 密钥：
        ```
        export QWEN_API_KEY="your-qwen-api-key"
        ```
    - 您可以在 `inference_agent_E.py` 中将 `CAPTION_MODEL` 设置为"qwen-vl-max"以获得更好的感知性能，但价格更高。
    - 如果您的机器配备了高性能 GPU，您也可以选择在本地托管图标描述模型：(1) 将 `CAPTION_CALL_METHOD` 设置为"local"；(2) 根据 GPU 规格将 `CAPTION_MODEL` 设置为'qwen-vl-chat'或'qwen-vl-chat-int4'。

5. 自定义初始提示：您可以根据您的特定设备和需求定制 agent 的提示。为此，请修改 `inference_agent_E.py` 中的 `INIT_TIPS`。在 `data/custom_tips_example_for_cn_apps.txt` 中提供了针对小红书和淘宝等中文应用的自定义提示示例。

## 🚀 快速开始

agent 可以在 `individual`（执行独立任务）或 `evolution`（执行带有进化的任务序列）两种设置下运行。我们提供了以下示例 shell 脚本：

- 运行独立任务：
    ```
    bash scripts/run_task.sh
    ```

- 运行带有自进化的任务序列。此脚本加载来自 `data/custom_tasks_example.json` 的示例 json 文件。
    ```
    bash scripts/run_tasks_evolution.sh
    ```

## 🤗 Mobile-Eval-E 基准测试
提出的 Mobile-Eval-E 基准测试可以在 `data/Mobile-Eval-E` 中找到，也可以在 [Huggingface Datasets](https://huggingface.co/datasets/mikewang/mobile_eval_e) 上找到。


## 📚 引用

```bibtex
@article{wang2025mobile,
  title={Mobile-Agent-E: Self-Evolving Mobile Assistant for Complex Tasks},
  author={Wang, Zhenhailong and Xu, Haiyang and Wang, Junyang and Zhang, Xi and Yan, Ming and Zhang, Ji and Huang, Fei and Ji, Heng},
  journal={arXiv preprint arXiv:2501.11733},
  year={2025}
}
```


启动项目：
. .\config_local.ps1
python run.py --instruction "打开微信" --run_name "test"