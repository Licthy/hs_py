import os
import json
import logging
import time
from typing import List, Dict, Tuple, Optional
from PIL import ImageGrab
import pyautogui
import cv2
import numpy as np
from dataclasses import dataclass, asdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('autoclicker.log'), logging.StreamHandler()]
)


@dataclass
class ImageConfig:
    """图片配置项"""
    name: str
    path: str
    grayscale: bool = False
    threshold: float = 0.8
    relative_click: Tuple[int, int] = (0, 0)
    max_attempts: int = 3
    skip_after_fails: int = 2
    execute_count: int = -1  # -1表示无限次


@dataclass
class Config:
    """主配置类"""
    images: List[ImageConfig]
    loop_delay: float = 1.0
    click_delay: float = 0.5


class ImageAutoClicker:
    """图像自动点击器"""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.current_counts = {img.name: 0 for img in self.config.images}
        self.fail_counts = {img.name: 0 for img in self.config.images}
        pyautogui.FAILSAFE = True  # 启用安全特性，鼠标移动到左上角可终止程序

    def _load_config(self, config_path: str) -> Config:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            images = []
            for img_data in config_data.get('images', []):
                img = ImageConfig(
                    name=img_data['name'],
                    path=img_data['path'],
                    grayscale=img_data.get('grayscale', False),
                    threshold=img_data.get('threshold', 0.8),
                    relative_click=tuple(img_data.get('relative_click', [0, 0])),
                    max_attempts=img_data.get('max_attempts', 3),
                    skip_after_fails=img_data.get('skip_after_fails', 2),
                    execute_count=img_data.get('execute_count', -1)
                )
                images.append(img)

            return Config(
                images=images,
                loop_delay=config_data.get('loop_delay', 1.0),
                click_delay=config_data.get('click_delay', 0.5)
            )
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            raise

    def _locate_image(self, template_path: str, grayscale: bool, threshold: float) -> Optional[Tuple[int, int]]:
        """在屏幕上查找图像"""
        try:
            # 加载模板图像
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                logging.error(f"无法加载模板图像: {template_path}")
                return None

            if grayscale:
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            # 获取屏幕截图
            screenshot = ImageGrab.grab()
            screenshot_np = np.array(screenshot)
            screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

            if grayscale:
                screenshot_cv = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)

            # 模板匹配
            result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                h, w = template.shape[:2]
                top_left = max_loc
                center = (top_left[0] + w // 2, top_left[1] + h // 2)
                return center
            else:
                return None
        except Exception as e:
            logging.error(f"图像识别过程中出错: {e}")
            return None

    def _click_position(self, position: Tuple[int, int], relative: Tuple[int, int]) -> None:
        """点击指定位置"""
        x = position[0] + relative[0]
        y = position[1] + relative[1]
        pyautogui.click(x, y)
        logging.info(f"点击位置: ({x}, {y})")

    def run(self) -> None:
        """运行自动点击器"""
        logging.info("自动点击器已启动")
        try:
            while True:
                all_done = True

                for img_config in self.config.images:
                    # 检查是否达到执行次数上限
                    if img_config.execute_count >= 0 and self.current_counts[
                        img_config.name] >= img_config.execute_count:
                        logging.debug(f"{img_config.name} 已达到执行次数上限")
                        continue

                    # 检查是否达到失败跳过次数
                    if self.fail_counts[img_config.name] >= img_config.skip_after_fails:
                        logging.info(f"{img_config.name} 已达到失败跳过次数，跳过此次检查")
                        self.fail_counts[img_config.name] = 0
                        continue

                    all_done = False

                    # 尝试查找图像
                    position = None
                    for attempt in range(img_config.max_attempts):
                        position = self._locate_image(
                            img_config.path,
                            img_config.grayscale,
                            img_config.threshold
                        )

                        if position:
                            logging.info(f"找到图像 {img_config.name}，相似度: {img_config.threshold}")
                            self._click_position(position, img_config.relative_click)
                            self.current_counts[img_config.name] += 1
                            self.fail_counts[img_config.name] = 0
                            time.sleep(self.config.click_delay)
                            break
                        else:
                            logging.info(f"尝试 {attempt + 1}/{img_config.max_attempts}: 未找到图像 {img_config.name}")
                            time.sleep(0.5)

                    if not position:
                        self.fail_counts[img_config.name] += 1
                        logging.warning(
                            f"未找到图像 {img_config.name}，失败次数: {self.fail_counts[img_config.name]}/{img_config.skip_after_fails}")

                # 如果所有图像都达到执行次数上限，退出循环
                if all_done:
                    logging.info("所有图像都已达到执行次数上限，程序退出")
                    break

                # 循环延迟
                logging.debug(f"循环结束，等待 {self.config.loop_delay} 秒")
                time.sleep(self.config.loop_delay)

        except KeyboardInterrupt:
            logging.info("用户手动终止程序")
        except Exception as e:
            logging.error(f"程序运行过程中出错: {e}")


if __name__ == "__main__":
    config_path = "config.json"
    clicker = ImageAutoClicker(config_path)
    clicker.run()
