from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from dataclasses import dataclass, field
from MobileAgentE.api import encode_image
from MobileAgentE.controller import tap, swipe, type, back, home, switch_app, enter, save_screenshot_to_file
from MobileAgentE.text_localization import ocr
import copy
import re
import json
import time
import os

### Helper Functions ###

def add_response(role, prompt, chat_history, image=None):
    new_chat_history = copy.deepcopy(chat_history)
    if image:
        base64_image = encode_image(image)
        content = [
            {
                "type": "text", 
                "text": prompt
            },
            {
                "type": "image_url", 
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            },
        ]
    else:
        content = [
            {
            "type": "text", 
            "text": prompt
            },
        ]
    new_chat_history.append([role, content])
    return new_chat_history


def add_response_two_image(role, prompt, chat_history, image):
    new_chat_history = copy.deepcopy(chat_history)

    base64_image1 = encode_image(image[0])
    base64_image2 = encode_image(image[1])
    content = [
        {
            "type": "text", 
            "text": prompt
        },
        {
            "type": "image_url", 
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image1}"
            }
        },
        {
            "type": "image_url", 
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image2}"
            }
        },
    ]

    new_chat_history.append([role, content])
    return new_chat_history


def print_status(chat_history):
    print("*"*100)
    for chat in chat_history:
        print("role:", chat[0])
        print(chat[1][0]["text"] + "<image>"*(len(chat[1])-1) + "\n")
    print("*"*100)


def extract_json_object(text, json_type="dict"):
    """
    Extracts a JSON object from a text string.

    Parameters:
    - text (str): The text containing the JSON data.
    - json_type (str): The type of JSON structure to look for ("dict" or "list").

    Returns:
    - dict or list: The extracted JSON object, or None if parsing fails.
    """
    try:
        if "//" in text:
            # Remove comments starting with //
            text = re.sub(r'//.*', '', text)
        if "# " in text:
            # Remove comments starting with #
            text = re.sub(r'#.*', '', text)
        # Try to parse the entire text as JSON
        return json.loads(text)
    except json.JSONDecodeError:
        pass  # Not a valid JSON, proceed to extract from text

    # Define patterns for extracting JSON objects or arrays
    json_pattern = r"({.*?})" if json_type == "dict" else r"(\[.*?\])"

    # Search for JSON enclosed in code blocks first
    code_block_pattern = r"```json\s*(.*?)\s*```"
    code_block_match = re.search(code_block_pattern, text, re.DOTALL)
    if code_block_match:
        json_str = code_block_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass  # Failed to parse JSON inside code block

    # Fallback to searching the entire text
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue  # Try the next match

    # If all attempts fail, return None
    return None

########################


@dataclass
class InfoPool:
    """Keeping track of all information across the agents."""

    # User input / accumulated knowledge
    instruction: str = ""
    tips: str = ""
    shortcuts: dict = field(default_factory=dict)

    # Perception
    width: int = 1080
    height: int = 2340
    perception_infos_pre: list = field(default_factory=list) # List of clickable elements pre action
    keyboard_pre: bool = False # keyboard status pre action
    perception_infos_post: list = field(default_factory=list) # List of clickable elements post action
    keyboard_post: bool = False # keyboard status post action

    # Working memory
    summary_history: list = field(default_factory=list)  # List of action descriptions
    action_history: list = field(default_factory=list)  # List of actions
    action_outcomes: list = field(default_factory=list)  # List of action outcomes
    error_descriptions: list = field(default_factory=list)

    last_summary: str = ""  # Last action description
    last_action: str = ""  # Last action
    last_action_thought: str = ""  # Last action thought
    important_notes: str = ""
    
    error_flag_plan: bool = False # if an error is not solved for multiple attempts with the executor
    error_description_plan: bool = False # explanation of the error for modifying the plan

    # Planning
    plan: str = ""
    progress_status: str = ""
    progress_status_history: list = field(default_factory=list)
    finish_thought: str = ""
    current_subgoal: str = ""
    prev_subgoal: str = ""
    err_to_manager_thresh: int = 2

    # future tasks
    future_tasks: list = field(default_factory=list)


class BaseAgent(ABC):
    @abstractmethod
    def init_chat(self) -> list:
        pass
    @abstractmethod
    def get_prompt(self, info_pool: InfoPool) -> str:
        pass
    @abstractmethod
    def parse_response(self, response: str) -> dict:
        pass


class Manager(BaseAgent):

    def init_chat(self):
        operation_history = []
        sysetm_prompt = "您是一个用于操作手机的有用AI助手。您的目标是跟踪进度并制定高级计划来实现用户的请求。请像人类用户操作手机一样思考。"
        operation_history.append(["system", [{"type": "text", "text": sysetm_prompt}]])
        return operation_history

    def get_prompt(self, info_pool: InfoPool) -> str:
        prompt = "### 用户指令 ###\n"
        prompt += f"{info_pool.instruction}\n\n"

        if info_pool.plan == "":
            # 首次规划
            prompt += "---\n"
            prompt += "逐步思考并制定一个高级计划来实现用户的指令。如果请求复杂，将其分解为子目标。如果请求涉及探索，包括具体的子目标来量化调查步骤。截图显示了手机的起始状态。\n\n"
            
            if info_pool.shortcuts != {}:
                prompt += "### 过往经验中的可用快捷方式 ###\n"
                prompt += "我们还基于过往经验提供了一些快捷方式功能。这些快捷方式是预定义的操作序列，可能使计划更高效。每个快捷方式都包含一个前提条件，指定何时适合使用。如果您的计划暗示使用某些快捷方式，请确保在使用之前满足前提条件。请注意，您不一定需要在高级计划中包含这些快捷方式的名称；它们仅作为参考提供。\n"
                for shortcut, value in info_pool.shortcuts.items():
                    prompt += f"- {shortcut}: {value['description']} | 前提条件: {value['precondition']}\n"
                prompt += "\n"
            prompt += "---\n"

            prompt += "请按以下格式提供您的输出，包含三个部分：\n\n"
            prompt += "### 思考 ###\n"
            prompt += "对您的计划和子目标理由的详细解释。\n\n"
            prompt += "### 计划 ###\n"
            prompt += "1. 第一个子目标\n"
            prompt += "2. 第二个子目标\n"
            prompt += "...\n\n"
            prompt += "### 当前子目标 ###\n"
            prompt += "您应该首先处理的子目标。\n\n"
        else:
            # continue planning
            prompt += "### 当前计划 ###\n"
            prompt += f"{info_pool.plan}\n\n"
            prompt += "### 之前的子目标 ###\n"
            prompt += f"{info_pool.current_subgoal}\n\n"
            prompt += f"### 进度状态 ###\n"
            prompt += f"{info_pool.progress_status}\n\n"
            prompt += "### 重要笔记 ###\n"
            if info_pool.important_notes != "":
                prompt += f"{info_pool.important_notes}\n\n"
            else:
                prompt += "未记录重要笔记。\n\n"
            if info_pool.error_flag_plan:
                prompt += "### 可能卡住了！ ###\n"
                prompt += "您遇到了几次失败的尝试。以下是一些日志：\n"
                k = info_pool.err_to_manager_thresh
                recent_actions = info_pool.action_history[-k:]
                recent_summaries = info_pool.summary_history[-k:]
                recent_err_des = info_pool.error_descriptions[-k:]
                for i, (act, summ, err_des) in enumerate(zip(recent_actions, recent_summaries, recent_err_des)):
                    prompt += f"- 尝试: 操作: {act} | 描述: {summ} | 结果: 失败 | 反馈: {err_des}\n"

            prompt += "---\n"
            prompt += "上述部分提供了您正在遵循的计划、您正在处理的当前子目标、已取得的整体进度以及您记录的任何重要笔记的概述。截图显示了手机的当前状态。\n"
            prompt += "仔细评估当前状态，以确定任务是否已完全完成。如果用户的请求涉及探索，请确保您已进行了充分的调查。如果您确信不需要进一步的操作，请在输出中将任务标记为\"已完成\"。如果任务未完成，请概述下一步。如果您遇到错误而卡住，请逐步思考是否需要修改整体计划来解决错误。\n"
            prompt += "注意：如果当前情况阻止按原计划进行或需要用户澄清，请做出合理假设并相应修改计划。在这种情况下，请像用户一样行事。\n\n"

            if info_pool.shortcuts != {}:
                prompt += "### 过往经验中的可用快捷方式 ###\n"
                prompt += "我们还基于过往经验提供了一些快捷方式功能。这些快捷方式是预定义的操作序列，可能使计划更高效。每个快捷方式都包含一个前提条件，指定何时适合使用。如果您的计划暗示使用某些快捷方式，请确保在使用之前满足前提条件。请注意，您不一定需要在高级计划中包含这些快捷方式的名称；它们仅作为参考提供。\n"
                for shortcut, value in info_pool.shortcuts.items():
                    prompt += f"- {shortcut}: {value['description']} | 前提条件: {value['precondition']}\n"
                prompt += "\n"
            
            prompt += "---\n"
            prompt += "请按以下格式提供您的输出，包含三个部分：\n\n"
            prompt += "### 思考 ###\n"
            prompt += "对您的计划和子目标理由提供详细解释。\n\n"
            prompt += "### 计划 ###\n"
            prompt += "如果需要更新高级计划，请在此处提供更新的计划。否则，保持当前计划并在此处复制。\n\n"
            prompt += "### 当前子目标 ###\n"
            prompt += "要处理的下一个子目标。如果之前的子目标尚未完成，请在此处复制。如果所有子目标都已完成，请写\"已完成\"。\n"
        return prompt

    def parse_response(self, response: str) -> dict:
        thought = response.split("### 思考 ###")[-1].split("### 计划 ###")[0].replace("\n", " ").replace("  ", " ").strip()
        plan = response.split("### 计划 ###")[-1].split("### 当前子目标 ###")[0].replace("\n", " ").replace("  ", " ").strip()
        current_subgoal = response.split("### 当前子目标 ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        return {"thought": thought, "plan": plan, "current_subgoal": current_subgoal}


# 名称: {参数: [参数键], 描述: 描述}
ATOMIC_ACTION_SIGNITURES = {
    "Open_App": {
        "arguments": ["app_name"],
        "description": lambda info: "如果当前屏幕是主屏幕或应用屏幕，您可以使用此操作打开当前屏幕上可见的名为\"app_name\"的应用。"
    },
    "Tap": {
        "arguments": ["x", "y"],
        "description": lambda info: "点击当前屏幕中的位置 (x, y)。"
    },
    "Swipe": {
        "arguments": ["x1", "y1", "x2", "y2"],
        "description": lambda info: f"从位置 (x1, y1) 滑动到位置 (x2, y2)。要上下滑动查看更多内容，您可以根据所需的滚动距离调整y坐标偏移。例如，设置 x1 = x2 = {int(0.5 * info.width)}, y1 = {int(0.5 * info.height)}, y2 = {int(0.1 * info.height)} 将向上滑动以查看下方的其他内容。要在应用切换器屏幕中左右滑动选择打开的应用，请将x坐标偏移设置为至少 {int(0.5 * info.width)}。"
    },
    "Type": {
        "arguments": ["text"],
        "description": lambda info: "在输入框中输入\"text\"。"
    },
    "Enter": {
        "arguments": [],
        "description": lambda info: "输入后按回车键（对搜索很有用）。"
    },
    "Switch_App": {
        "arguments": [],
        "description": lambda info: "显示应用切换器以在已打开的应用之间切换。"
    },
    "Back": {
        "arguments": [],
        "description": lambda info: "返回到之前的状态。"
    },
    "Home": {
        "arguments": [],
        "description": lambda info: "返回到主页。"
    },
    "Wait": {
        "arguments": [],
        "description": lambda info: "等待10秒以给页面加载更多时间。"
    }
}

INIT_SHORTCUTS = {
    "Tap_Type_and_Enter": {
        "name": "Tap_Type_and_Enter",
        "arguments": ["x", "y", "text"],
        "description": "点击位置 (x, y) 的输入框，输入\"text\"，然后执行回车操作。对搜索和发送消息非常有用！",
        "precondition": "屏幕上有一个文本输入框，且没有之前输入的内容。",
        "atomic_action_sequence":[
            {"name": "Tap", "arguments_map": {"x":"x", "y":"y"}},
            {"name": "Type", "arguments_map": {"text":"text"}},
            {"name": "Enter", "arguments_map": {}}
        ]
    }
}


class Operator(BaseAgent):
    def __init__(self, adb_path):
        self.adb = adb_path

    def init_chat(self):
        operation_history = []
        sysetm_prompt = "您是一个用于操作手机的有用AI助手。您的目标是选择正确的操作来完成用户的指令。请像人类用户操作手机一样思考。"
        operation_history.append(["system", [{"type": "text", "text": sysetm_prompt}]])
        return operation_history

    def get_prompt(self, info_pool: InfoPool) -> str:
        prompt = "### 用户指令 ###\n"
        prompt += f"{info_pool.instruction}\n\n"

        prompt += "### 总体计划 ###\n"
        prompt += f"{info_pool.plan}\n\n"

        prompt += "### 进度状态 ###\n"
        if info_pool.progress_status != "":
            prompt += f"{info_pool.progress_status}\n\n"
        else:
            prompt += "尚无进度。\n\n"

        prompt += "### 当前子目标 ###\n"
        prompt += f"{info_pool.current_subgoal}\n\n"

        prompt += "### 屏幕信息 ###\n"
        prompt += (
            f"附加的图像是显示手机当前状态的截图。"
            f"其宽度和高度分别为 {info_pool.width} 和 {info_pool.height} 像素。\n"
        )
        prompt += (
            "为了帮助您更好地理解此截图中的内容，我们已提取了文本元素和图标的位置信息，包括搜索栏等交互元素。"
            "格式为：(坐标; 内容)。坐标为 [x, y]，其中 x 表示水平像素位置（从左到右），"
            "y 表示垂直像素位置（从上到下）。"
        )
        prompt += "提取的信息如下：\n"

        for clickable_info in info_pool.perception_infos_pre:
            if clickable_info['text'] != "" and clickable_info['text'] != "icon: None" and clickable_info['coordinates'] != (0, 0):
                prompt += f"{clickable_info['coordinates']}; {clickable_info['text']}\n"
        prompt += "\n"
        prompt += (
            "请注意，搜索栏通常是一个长的圆角矩形。如果没有显示搜索栏而您想要执行搜索，您可能需要点击搜索按钮，通常用放大镜图标表示。\n"
            "另外，上述信息可能不完全准确。"
            "您应该结合截图来获得更好的理解。"
        )
        prompt += "\n\n"

        prompt += "### 键盘状态 ###\n"
        if info_pool.keyboard_pre:
            prompt += "键盘已激活，您可以输入。"
        else:
            prompt += "键盘尚未激活，您无法输入。"
        prompt += "\n\n"

        if info_pool.tips != "":
            prompt += "### 提示 ###\n"
            prompt += "从之前与设备交互的经验中，您收集了以下可能对决定下一步操作有用的提示：\n"
            prompt += f"{info_pool.tips}\n\n"

        prompt += "### 重要笔记 ###\n"
        if info_pool.important_notes != "":
            prompt += "以下是您已记录的与用户请求相关的一些潜在重要内容：\n"
            prompt += f"{info_pool.important_notes}\n\n"
        else:
            prompt += "未记录重要笔记。\n\n"

        prompt += "---\n"
        prompt += "仔细检查上述提供的所有信息，并决定要执行的下一个操作。如果您注意到之前操作中有未解决的错误，请像人类用户一样思考并尝试纠正它们。您必须从原子操作或快捷方式中选择您的操作。快捷方式是预定义的操作序列，可用于加快流程。每个快捷方式都有一个前提条件，指定何时适合使用。如果您计划使用快捷方式，请首先确保当前手机状态满足其前提条件。\n\n"
        
        prompt += "#### 原子操作 ####\n"
        prompt += "原子操作函数以 `名称(参数): 描述` 的格式列出如下：\n"

        if info_pool.keyboard_pre:
            for action, value in ATOMIC_ACTION_SIGNITURES.items():
                prompt += f"- {action}({', '.join(value['arguments'])}): {value['description'](info_pool)}\n"
        else:
            for action, value in ATOMIC_ACTION_SIGNITURES.items():
                if "Type" not in action:
                    prompt += f"- {action}({', '.join(value['arguments'])}): {value['description'](info_pool)}\n"
            prompt += "注意：无法输入。键盘尚未激活。要输入文字，请通过点击输入框或使用快捷方式来激活键盘，快捷方式包括首先点击输入框。”\n"
        
        prompt += "\n"
        prompt += "#### 快捷方式 ####\n"
        if info_pool.shortcuts != {}:
            prompt += "快捷方式函数以 `名称(参数): 描述 | 前提条件: 前提条件` 的格式列出如下：\n"
            for shortcut, value in info_pool.shortcuts.items():
                prompt += f"- {shortcut}({', '.join(value['arguments'])}): {value['description']} | 前提条件: {value['precondition']}\n"
        else:
            prompt += "没有可用的快捷方式。\n"
        prompt += "\n"

        prompt += "### 最近操作历史 ###\n"
        if info_pool.action_history != []:
            prompt += "您之前执行的最近操作及其是否成功：\n"
            num_actions = min(5, len(info_pool.action_history))
            latest_actions = info_pool.action_history[-num_actions:]
            latest_summary = info_pool.summary_history[-num_actions:]
            latest_outcomes = info_pool.action_outcomes[-num_actions:]
            error_descriptions = info_pool.error_descriptions[-num_actions:]
            action_log_strs = []
            for act, summ, outcome, err_des in zip(latest_actions, latest_summary, latest_outcomes, error_descriptions):
                if outcome == "A":
                    action_log_str = f"操作: {act} | 描述: {summ} | 结果: 成功\n"
                else:
                    action_log_str = f"操作: {act} | 描述: {summ} | 结果: 失败 | 反馈: {err_des}\n"
                prompt += action_log_str
                action_log_strs.append(action_log_str)
            if latest_outcomes[-1] == "C" and "Tap" in action_log_strs[-1] and "Tap" in action_log_strs[-2]:
                prompt += "\n提示：如果多次点击操作都未能改变屏幕，请考虑使用\"滑动\"操作查看更多内容，或使用其他方式实现当前子目标。"
            
            prompt += "\n"
        else:
            prompt += "尚未执行任何操作。\n\n"

        prompt += "---\n"
        prompt += "请按以下格式提供您的输出，包含三个部分：\n"
        prompt += "### 思考 ###\n"
        prompt += "详细解释您选择该操作的理由。重要提示：如果您决定使用快捷方式，请首先验证其前提条件在当前手机状态下是否满足。例如，如果快捷方式要求手机处于主屏幕，请检查当前截图是否显示主屏幕。如果不是，请执行相应的原子操作。\n\n"

        prompt += "### 操作 ###\n"
        prompt += "从提供的选项中仅选择一个操作或快捷方式。重要提示：不要返回无效操作如null或stop。不要重复之前失败的操作。\n"
        prompt += "尽可能使用快捷方式来加快流程，但要确保满足前提条件。\n"
        prompt += "您必须使用有效的JSON格式提供您的决定，指定操作的名称和参数。例如，如果您选择在位置(100, 200)点击，您应该写{\"name\":\"Tap\", \"arguments\":{\"x\":100, \"y\":100}}。如果操作不需要参数，如Home，请在\"arguments\"字段中填入null。确保参数键与操作函数的签名完全匹配。\n\n"
        
        prompt += "### 描述 ###\n"
        prompt += "对所选操作和预期结果的简要描述。"
        return prompt

    def execute_atomic_action(self, action: str, arguments: dict, **kwargs) -> None:
        adb_path = self.adb
        
        if "Open_App".lower() == action.lower():
            screenshot_file = kwargs["screenshot_file"]
            ocr_detection = kwargs["ocr_detection"]
            ocr_recognition = kwargs["ocr_recognition"]
            app_name = arguments["app_name"].strip()
            text, coordinate = ocr(screenshot_file, ocr_detection, ocr_recognition)
            for ti in range(len(text)):
                if app_name == text[ti]:
                    name_coordinate = [int((coordinate[ti][0] + coordinate[ti][2])/2), int((coordinate[ti][1] + coordinate[ti][3])/2)]
                    tap(adb_path, name_coordinate[0], name_coordinate[1]- int(coordinate[ti][3] - coordinate[ti][1]))# 
                    break
            if app_name in ['Fandango', 'Walmart', 'Best Buy']:
                # additional wait time for app loading
                time.sleep(10)
            time.sleep(10)
        
        elif "Tap".lower() == action.lower():
            x, y = int(arguments["x"]), int(arguments["y"])
            tap(adb_path, x, y)
            time.sleep(5)
        
        elif "Swipe".lower() == action.lower():
            x1, y1, x2, y2 = int(arguments["x1"]), int(arguments["y1"]), int(arguments["x2"]), int(arguments["y2"])
            swipe(adb_path, x1, y1, x2, y2)
            time.sleep(5)
            
        elif "Type".lower() == action.lower():
            text = arguments["text"]
            type(adb_path, text)
            time.sleep(3)

        elif "Enter".lower() == action.lower():
            enter(adb_path)
            time.sleep(10)

        elif "Back".lower() == action.lower():
            back(adb_path)
            time.sleep(3)
        
        elif "Home".lower() == action.lower():
            home(adb_path)
            time.sleep(3)
        
        elif "Switch_App".lower() == action.lower():
            switch_app(adb_path)
            time.sleep(3)
        
        elif "Wait".lower() == action.lower():
            time.sleep(10)
        
    def execute(self, action_str: str, info_pool: InfoPool, screenshot_log_dir=None, iter="", **kwargs) -> None:
        action_object = extract_json_object(action_str)
        if action_object is None:
            print("Error! Invalid JSON for executing action: ", action_str)
            return None, 0, None
        action, arguments = action_object["name"], action_object["arguments"]
        action = action.strip()

        # execute atomic action
        if action in ATOMIC_ACTION_SIGNITURES:
            print("Executing atomic action: ", action, arguments)
            self.execute_atomic_action(action, arguments, info_pool=info_pool, **kwargs)
            if screenshot_log_dir is not None:
                time.sleep(1)
                screenshot_file = os.path.join(screenshot_log_dir, f"{iter}__{action.replace(' ', '')}.png")
                save_screenshot_to_file(self.adb, screenshot_file)
            return action_object, 1, None # number of atomic actions executed
        # execute shortcut
        elif action in info_pool.shortcuts:
            print("Executing shortcut: ", action)
            shortcut = info_pool.shortcuts[action]
            for i, atomic_action in enumerate(shortcut["atomic_action_sequence"]):
                try:
                    atomic_action_name = atomic_action["name"]
                    if atomic_action["arguments_map"] is None or len(atomic_action["arguments_map"]) == 0:
                        atomic_action_args = None
                    else:
                        atomic_action_args = {}
                        for atomic_arg_key, value in atomic_action["arguments_map"].items():
                            if value in arguments: # if the mapped key is in the shortcut arguments
                                atomic_action_args[atomic_arg_key] = arguments[value]
                            else: # if not: the values are directly passed
                                atomic_action_args[atomic_arg_key] = value
                    print(f"\t Executing sub-step {i}:", atomic_action_name, atomic_action_args, "...")
                    self.execute_atomic_action(atomic_action_name, atomic_action_args, info_pool=info_pool, **kwargs)
                    # log screenshot during shortcut execution
                    if screenshot_log_dir is not None:
                        time.sleep(1)
                        screenshot_file = os.path.join(screenshot_log_dir, f"{iter}__{action.replace(' ', '')}__{i}-{atomic_action_name.replace(' ', '')}.png")
                        save_screenshot_to_file(self.adb, screenshot_file)
                        
                except Exception as e:
                    e += f"\nError in executing step {i}: {atomic_action_name} {atomic_action_args}"
                    print("Error in executing shortcut: ", action, e)
                    return action_object, i, e
            return action_object, len(shortcut["atomic_action_sequence"]), None
        else:
            if action.lower() in ["null", "none", "finish", "exit", "stop"]:
                print("Agent choose to finish the task. Action: ", action)
            else:
                print("Error! Invalid action name: ", action)
            info_pool.finish_thought = info_pool.last_action_thought
            return None, 0, None

    def parse_response(self, response: str) -> dict:
        thought = response.split("### 思考 ###")[-1].split("### 操作 ###")[0].replace("\n", " ").replace("  ", " ").strip()
        action = response.split("### 操作 ###")[-1].split("### 描述 ###")[0].replace("\n", " ").replace("  ", " ").strip()
        description = response.split("### 描述 ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        return {"thought": thought, "action": action, "description": description}


class ActionReflector(BaseAgent):
    def init_chat(self) -> list:
        operation_history = []
        sysetm_prompt = "您是一个用于操作手机的有用AI助手。您的目标是验证最后一个操作是否产生了预期的行为，并跟踪整体进度。"
        operation_history.append(["system", [{"type": "text", "text": sysetm_prompt}]])
        return operation_history

    def get_prompt(self, info_pool: InfoPool) -> str:
        prompt = "### 用户指令 ###\n"
        prompt += f"{info_pool.instruction}\n\n"

        prompt += "### 进度状态 ###\n"
        if info_pool.progress_status != "":
            prompt += f"{info_pool.progress_status}\n\n"
        else:
            prompt += "尚无进度。\n\n"

        prompt += "### 当前子目标 ###\n"
        prompt += f"{info_pool.current_subgoal}\n\n"

        prompt += "---\n"
        prompt += f"附加的两张图像是您最后一个操作前后的两张手机截图。"
        prompt += f"宽度和高度分别为 {info_pool.width} 和 {info_pool.height} 像素。\n"
        prompt += (
            "为了帮助您更好地感知这些截图中的内容，我们已提取了文本元素和图标的位置信息。"
            "格式为：(坐标; 内容)。坐标为 [x, y]，其中 x 表示水平像素位置（从左到右），"
            "y 表示垂直像素位置（从上到下）。\n"
        )
        prompt += (
            "请注意，这些信息可能不完全准确。"
            "您应该结合截图来获得更好的理解。"
        )
        prompt += "\n\n"

        prompt += "### 操作前屏幕信息 ###\n"
        for clickable_info in info_pool.perception_infos_pre:
            if clickable_info['text'] != "" and clickable_info['text'] != "icon: None" and clickable_info['coordinates'] != (0, 0):
                prompt += f"{clickable_info['coordinates']}; {clickable_info['text']}\n"
        prompt += "\n"
        prompt += "操作前键盘状态："
        if info_pool.keyboard_pre:
            prompt += "键盘已激活，您可以输入。"
        else:
            prompt += "键盘尚未激活，您无法输入。"
        prompt += "\n\n"


        prompt += "### 操作后屏幕信息 ###\n"
        for clickable_info in info_pool.perception_infos_post:
            if clickable_info['text'] != "" and clickable_info['text'] != "icon: None" and clickable_info['coordinates'] != (0, 0):
                prompt += f"{clickable_info['coordinates']}; {clickable_info['text']}\n"
        prompt += "\n"
        prompt += "操作后键盘状态："
        if info_pool.keyboard_post:
            prompt += "键盘已激活，您可以输入。"
        else:
            prompt += "键盘尚未激活，您无法输入。"
        prompt += "\n\n"

        prompt += "---\n"
        prompt += "### 最近操作 ###\n"
        # assert info_pool.last_action != ""
        prompt += f"操作：{info_pool.last_action}\n"
        prompt += f"预期：{info_pool.last_summary}\n\n"

        prompt += "---\n"
        prompt += "Carefully examine the information provided above to determine whether the last action produced the expected behavior. If the action was successful, update the progress status accordingly. If the action failed, identify the failure mode and provide reasoning on the potential reason causing this failure. Note that for the “Swipe” action, it may take multiple attempts to display the expected content. Thus, for a \"Swipe\" action, if the screen shows new content, it usually meets the expectation.\n\n"

        prompt += "请按以下格式提供您的输出，包含三个部分：\n\n"
        prompt += "### 结果 ###\n"
        prompt += "从以下选项中选择。请给出您的答案\"A\"、\"B\"或\"C\"：\n"
        prompt += "A：成功或部分成功。最后一个操作的结果符合预期。\n"
        prompt += "B：失败。最后一个操作导致进入错误页面。我需要返回到之前的状态。\n"
        prompt += "C：失败。最后一个操作没有产生任何变化。\n\n"

        prompt += "### 错误描述 ###\n"
        prompt += "如果操作失败，请提供错误的详细描述和导致此失败的潜在原因。如果操作成功，请在此处填写\"None\"。\n\n"

        prompt += "### 进度状态 ###\n"
        prompt += "如果操作成功或部分成功，请更新进度状态。如果操作失败，请复制之前的进度状态。\n"

        return prompt

    def parse_response(self, response: str) -> dict:
        outcome = response.split("### 结果 ###")[-1].split("### 错误描述 ###")[0].replace("\n", " ").replace("  ", " ").strip()
        error_description = response.split("### 错误描述 ###")[-1].split("### 进度状态 ###")[0].replace("\n", " ").replace("  ", " ").strip()
        progress_status = response.split("### 进度状态 ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        return {"outcome": outcome, "error_description": error_description, "progress_status": progress_status}


class Notetaker(BaseAgent):
    def init_chat(self) -> list:
        operation_history = []
        sysetm_prompt = "您是一个用于操作手机的有用AI助手。您的目标是记录与用户请求相关的重要内容。"
        operation_history.append(["system", [{"type": "text", "text": sysetm_prompt}]])
        return operation_history

    def get_prompt(self, info_pool: InfoPool) -> str:
        prompt = "### 用户指令 ###\n"
        prompt += f"{info_pool.instruction}\n\n"

        prompt += "### 总体计划 ###\n"
        prompt += f"{info_pool.plan}\n\n"

        prompt += "### 当前子目标 ###\n"
        prompt += f"{info_pool.current_subgoal}\n\n"

        prompt += "### 进度状态 ###\n"
        prompt += f"{info_pool.progress_status}\n\n"

        prompt += "### 现有重要笔记 ###\n"
        if info_pool.important_notes != "":
            prompt += f"{info_pool.important_notes}\n\n"
        else:
            prompt += "未记录重要笔记。\n\n"

        prompt += "### 当前屏幕信息 ###\n"
        prompt += (
            f"附加的图像是显示手机当前状态的截图。"
            f"其宽度和高度分别为 {info_pool.width} 和 {info_pool.height} 像素。\n"
        )
        prompt += (
            "为了帮助您更好地感知此截图中的内容，我们已提取了文本元素和图标的位置信息。"
            "格式为：(坐标; 内容)。坐标为 [x, y]，其中 x 表示水平像素位置（从左到右），"
            "y 表示垂直像素位置（从上到下）。"
        )
        prompt += "提取的信息如下：\n"

        for clickable_info in info_pool.perception_infos_post:
            if clickable_info['text'] != "" and clickable_info['text'] != "icon: None" and clickable_info['coordinates'] != (0, 0):
                prompt += f"{clickable_info['coordinates']}; {clickable_info['text']}\n"
        prompt += "\n"
        prompt += (
            "请注意，此信息可能不完全准确。"
            "您应该结合截图来获得更好的理解。"
        )
        prompt += "\n\n"

        prompt += "---\n"
        prompt += "仔细检查上述信息，以识别需要记录的任何重要内容。重要提示：不要记录低级操作；只跟踪与用户请求相关的重要文本或视觉信息。\n\n"

        prompt += "请按以下格式提供您的输出：\n"
        prompt += "### 重要笔记 ###\n"
        prompt += "更新的重要笔记，结合旧的和新的。如果没有新内容需要记录，请复制现有的重要笔记。\n"

        return prompt

    def parse_response(self, response: str) -> dict:
        important_notes = response.split("### 重要笔记 ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        return {"important_notes": important_notes}


SHORTCUT_EXMPALE = """
{
    "name": "Tap_Type_and_Enter",
    "arguments": ["x", "y", "text"],
    "description": "点击位置 (x, y) 的输入框，输入\"text\"，然后执行回车操作（对搜索和发送消息很有用）。",
    "precondition": "屏幕上有一个文本输入框。",
    "atomic_action_sequence":[
        {"name": "Tap", "arguments_map": {"x":"x", "y":"y"}},
        {"name": "Type", "arguments_map": {"text":"text"}},
        {"name": "Enter", "arguments_map": {}}
    ]
}
"""


class ExperienceReflectorShortCut(BaseAgent):
    def init_chat(self) -> list:
        operation_history = []
        sysetm_prompt = "您是一个专门从事手机操作的有用AI助手。您的目标是反思过去的经验并提供见解以改善未来的交互。"
        operation_history.append(["system", [{"type": "text", "text": sysetm_prompt}]])
        return operation_history

    def get_prompt(self, info_pool: InfoPool) -> str:
        prompt = "### 当前任务 ###\n"
        prompt += f"{info_pool.instruction}\n\n"

        prompt += "### 总体计划 ###\n"
        prompt += f"{info_pool.plan}\n\n"

        prompt += "### 进度状态 ###\n"
        prompt += f"{info_pool.progress_status}\n\n"

        prompt += "### 原子操作 ###\n"
        prompt += "以下是原子操作，格式为 `名称(参数): 描述`：\n"
        for action, value in ATOMIC_ACTION_SIGNITURES.items():
            prompt += f"{action}({', '.join(value['arguments'])}): {value['description'](info_pool)}\n"
        prompt += "\n"

        prompt += "### 过往经验中的现有快捷方式 ###\n"
        if info_pool.shortcuts != {}:
            prompt += "以下是您已创建的一些现有快捷方式：\n"
            for shortcut, value in info_pool.shortcuts.items():
                prompt += f"- {shortcut}({', '.join(value['arguments'])}): {value['description']} | 前提条件: {value['precondition']}\n"
        else:
            prompt += "未提供快捷方式。\n"
        prompt += "\n"

        prompt += "### 完整操作历史 ###\n"
        if info_pool.action_history != []:
            latest_actions = info_pool.action_history
            latest_summary = info_pool.summary_history
            action_outcomes = info_pool.action_outcomes
            error_descriptions = info_pool.error_descriptions
            progress_status_history = info_pool.progress_status_history
            for act, summ, outcome, err_des, progress in zip(latest_actions, latest_summary, action_outcomes, error_descriptions, progress_status_history):
                if outcome == "A":
                    prompt += f"- 操作: {act} | 描述: {summ} | 结果: 成功 | 进度: {progress}\n"
                else:
                    prompt += f"- 操作: {act} | 描述: {summ} | 结果: 失败 | 反馈: {err_des}\n"
            prompt += "\n"
        else:
            prompt += "尚未执行任何操作。\n\n"

        if len(info_pool.future_tasks) > 0:
            prompt += "---\n"
            prompt += "### 未来任务 ###\n"
            prompt += "以下是您将来可能被要求执行的一些任务：\n"
            for task in info_pool.future_tasks:
                prompt += f"- {task}\n"
            prompt += "\n"

        prompt += "---\n"
        prompt += "仔细反思当前任务的交互历史。检查是否有任何子目标是通过一系列成功操作完成的，并且可以合并为新的\"快捷方式\"以提高未来任务的效率？这些快捷方式是由一系列原子操作组成的子程序，可以在特定前提条件下执行。例如，在搜索栏中点击、输入和回车文本，或在Notes中创建新笔记。"

        prompt += "请按以下格式提供您的输出：\n\n"

        prompt += "### 新快捷方式 ###\n"
        prompt += "如果您决定创建一个新的快捷方式（不在现有快捷方式中），请以有效的JSON格式提供您的快捷方式对象，详细信息如下。如果不创建，请在此处填写\"None\"。\n"
        prompt += "快捷方式对象包含以下字段：name、arguments、description、precondition和atomic_action_sequence。参数中的键需要是唯一的。atomic_action_sequence是一个字典列表，每个字典包含原子操作的名称以及其原子参数名称到快捷方式参数名称的映射。如果atomic_action_sequence中的原子操作不需要任何参数，请将`arguments_map`设置为空字典。\n"
        prompt += "重要提示：快捷方式必须仅包含上面列出的原子操作。只有在您确信它对未来有用时才创建新的快捷方式。确保不包含功能过于相似的重复快捷方式。\n"
        prompt += "专业提示：避免创建参数过多的快捷方式，例如涉及在不同位置的多次点击。快捷方式所需的所有坐标参数都应在当前屏幕上可见。想象一下，当您开始执行快捷方式时，您基本上是盲目的。\n"
        prompt += f"按照下面的示例格式化快捷方式。避免添加可能导致json.loads()错误的注释。\n {SHORTCUT_EXMPALE}\n\n"
        return prompt

    def add_new_shortcut(self, short_cut_str: str, info_pool: InfoPool) -> str:
        if short_cut_str is None or short_cut_str == "None":
            return
        short_cut_object = extract_json_object(short_cut_str)
        if short_cut_object is None:
            print("Error! Invalid JSON for adding new shortcut: ", short_cut_str)
            return
        short_cut_name = short_cut_object["name"]
        if short_cut_name in info_pool.shortcuts:
            print("Error! The shortcut already exists: ", short_cut_name)
            return
        info_pool.shortcuts[short_cut_name] = short_cut_object
        print("Updated short_cuts:", info_pool.shortcuts)

    def parse_response(self, response: str) -> dict:
        new_shortcut = response.split("### 新快捷方式 ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        return {"new_shortcut": new_shortcut}


class ExperienceReflectorTips(BaseAgent):
    def init_chat(self) -> list:
        operation_history = []
        sysetm_prompt = "您是一个专门从事手机操作的有用AI助手。您的目标是反思过去的经验并提供见解以改善未来的交互。"
        operation_history.append(["system", [{"type": "text", "text": sysetm_prompt}]])
        return operation_history

    def get_prompt(self, info_pool: InfoPool) -> str:
        prompt = "### 当前任务 ###\n"
        prompt += f"{info_pool.instruction}\n\n"

        prompt += "### 总体计划 ###\n"
        prompt += f"{info_pool.plan}\n\n"

        prompt += "### 进度状态 ###\n"
        prompt += f"{info_pool.progress_status}\n\n"
    
        prompt += "### 过往经验中的现有提示 ###\n"
        if info_pool.tips != "":
            prompt += f"{info_pool.tips}\n\n"
        else:
            prompt += "未记录提示。\n\n"

        prompt += "### 完整操作历史 ###\n"
        if info_pool.action_history != []:
            latest_actions = info_pool.action_history
            latest_summary = info_pool.summary_history
            action_outcomes = info_pool.action_outcomes
            error_descriptions = info_pool.error_descriptions
            progress_status_history = info_pool.progress_status_history
            for act, summ, outcome, err_des, progress in zip(latest_actions, latest_summary, action_outcomes, error_descriptions, progress_status_history):
                if outcome == "A":
                    prompt += f"- 操作: {act} | 描述: {summ} | 结果: 成功 | 进度: {progress}\n"
                else:
                    prompt += f"- 操作: {act} | 描述: {summ} | 结果: 失败 | 反馈: {err_des}\n"
            prompt += "\n"
        else:
            prompt += "尚未执行任何操作。\n\n"
            
        if len(info_pool.future_tasks) > 0:
            prompt += "---\n"
            # if the setting provides future tasks explicitly
            prompt += "### 未来任务 ###\n"
            prompt += "以下是您将来可能被要求执行的一些任务：\n"
            for task in info_pool.future_tasks:
                prompt += f"- {task}\n"
            prompt += "\n"

        prompt += "---\n"
        prompt += "仔细反思当前任务的交互历史。检查是否有任何通用提示可能对处理未来任务有用，例如关于防止某些常见错误的建议？\n\n"

        prompt += "请按以下格式提供您的输出：\n\n"

        prompt += "### 更新的提示 ###\n"
        prompt += "如果您有任何重要的新提示要添加（不在现有提示中），请将它们与当前列表结合。如果没有新提示，只需在此处复制现有提示。保持您的提示简洁和通用。\n"
        return prompt

    def parse_response(self, response: str) -> dict:
        updated_tips = response.split("### 更新的提示 ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        return {"updated_tips": updated_tips}


class ExperienceRetrieverShortCut(BaseAgent):
    def init_chat(self) -> list:
        operation_history = []
        sysetm_prompt = "您是一个专门从事手机操作的有用AI助手。您的目标是从过往经验中选择与当前任务相关的快捷方式。"
        operation_history.append(["system", [{"type": "text", "text": sysetm_prompt}]])
        return operation_history

    def get_prompt(self, instruction, shortcuts) -> str:
        
        prompt = "### 过往经验中的现有快捷方式 ###\n"
        for shortcut, value in shortcuts.items():
            prompt += f"- 名称: {shortcut} | 描述: {value['description']}\n"

        prompt += "\n"
        prompt += "### 当前任务 ###\n"
        prompt += f"{instruction}\n\n"

        prompt += "---\n"
        prompt += "仔细检查上述提供的信息，选择对当前任务有帮助的快捷方式。删除与当前任务无关的快捷方式。\n"

        prompt += "请按以下格式提供您的输出：\n\n"
        prompt += "### 选定的快捷方式 ###\n"
        prompt += "以选定快捷方式名称列表的形式提供您的答案：[\"shortcut1\", \"shortcut2\", ...]。如果没有相关的快捷方式，请在此处填写\"None\"。\n"
        return prompt
    
    def parse_response(self, response: str) -> dict:
        selected_shortcuts_str = response.split("### 选定的快捷方式 ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        try:
            selected_shortcut_names = extract_json_object(selected_shortcuts_str, json_type="list")
            selected_shortcut_names = [s.strip() for s in selected_shortcut_names]
        except:
            selected_shortcut_names = []
            
        return {"selected_shortcut_names": selected_shortcut_names}


class ExperienceRetrieverTips(BaseAgent):
    def init_chat(self) -> list:
        operation_history = []
        sysetm_prompt = "您是一个专门从事手机操作的有用AI助手。您的目标是从过往经验中选择与当前任务相关的提示。"
        operation_history.append(["system", [{"type": "text", "text": sysetm_prompt}]])
        return operation_history

    def get_prompt(self, instruction, tips) -> str:
        prompt = "### 过往经验中的现有提示 ###\n"
        prompt += f"{tips}\n\n"

        prompt += "\n"
        prompt += "### 当前任务 ###\n"
        prompt += f"{instruction}\n\n"

        prompt += "---\n"
        prompt += "仔细检查上述提供的信息，选择对当前任务有帮助的提示。删除与当前任务无关的提示。\n"

        prompt += "请按以下格式提供您的输出：\n\n"
        prompt += "### 选定的提示 ###\n"
        prompt += "通常有用且与当前任务相关的提示。可以随意重新组织要点。如果没有相关提示，请在此处填写\"None\"。\n"

        return prompt
    
    def parse_response(self, response: str) -> dict:
        selected_tips = response.split("### 选定的提示 ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        return {"selected_tips": selected_tips}