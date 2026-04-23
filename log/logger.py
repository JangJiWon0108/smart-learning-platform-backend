"""
프로젝트 전용 로거(logger) 생성 모듈.

Python 기본 logging 모듈을 래핑해서
일관된 포맷으로 로그를 출력합니다.
"""

from __future__ import annotations

import logging

# 모든 로그 메시지 앞에 붙는 접두사
PREFIX = "[smart-learning]"


def get_logger(name: str) -> logging.Logger:
    """
    이름이 지정된 로거 객체를 반환합니다.

    같은 이름으로 여러 번 호출해도 핸들러가 중복 추가되지 않습니다.

    Args:
        name: 로거 이름 (예: "api", "agent", "nodes")
              실제 로거 이름은 "smart_learning.{name}" 형태가 됩니다.

    Returns:
        설정이 완료된 logging.Logger 객체

    사용 예시:
        log = get_logger("api")
        log.info("서버 시작")  # 출력: [smart-learning] 2024-01-01 12:00:00 | 서버 시작
    """
    # "smart_learning.api" 같은 계층적 이름으로 로거를 만듭니다
    logger = logging.getLogger(f"smart_learning.{name}")

    # 이미 핸들러가 설정되어 있으면 그대로 반환 (중복 방지)
    if logger.handlers:
        return logger

    # INFO 레벨 이상의 로그만 출력합니다 (DEBUG는 출력 안 함)
    logger.setLevel(logging.INFO)

    # 콘솔(터미널)에 출력하는 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 로그 출력 형식: "[smart-learning] 2024-01-01 12:00:00 | 메시지 내용"
    formatter = logging.Formatter(
        fmt=f"{PREFIX} %(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # 부모 로거로 이벤트가 전파되지 않도록 막습니다
    # (설정 안 하면 루트 로거에서 로그가 두 번 출력될 수 있음)
    logger.propagate = False

    return logger
