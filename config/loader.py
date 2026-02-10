from pathlib import Path
from platformdirs import user_config_dir, user_data_dir
from config.config import Config
from config.subagent_config import SubAgentConfig
from tomli import TOMLDecodeError
from utils.errors import ConfigError
from typing import Any
import tomli
import logging

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "config.toml"

AGENT_MD_FILE_NAME = "agent.md"


def get_config_dir() -> Path:
    return Path(user_config_dir("ai-agent"))


def get_system_config_path() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME


def get_data_dir() -> Path:
    return Path(user_data_dir("ai-agent"))


def _parse_toml(path: Path):
    try:
        with path.open("rb") as f:
            return tomli.load(f)
    except tomli.TOMLDecodeError as e:
        raise ConfigError(
            f"Failed to parse TOML config file {path} | Invalid TOML | {e}",
            config_file=str(path),
        ) from e
    except (OSError, IOError) as e:
        raise ConfigError(
            f"Failed to read TOML config file {path} | Invalid TOML | {e}",
            config_file=str(path),
        ) from e


def _validate_and_parse_subagents(subagents_data: list[dict[str, Any]]) -> list[SubAgentConfig]:
    """Validate and parse subagent configurations from TOML
    
    Args:
        subagents_data: List of raw subagent dictionaries from TOML
        
    Returns:
        List of validated SubAgentConfig objects
    """
    validated_subagents: list[SubAgentConfig] = []
    
    for idx, subagent_dict in enumerate(subagents_data):
        try:
            # Pydantic will handle all validation
            subagent_config = SubAgentConfig(**subagent_dict)
            validated_subagents.append(subagent_config)
            logger.info(f"Loaded custom subagent: {subagent_config.name}")
        except Exception as e:
            logger.warning(
                f"Skipping invalid subagent configuration at index {idx}: {e}"
            )
    
    return validated_subagents


def _get_agent_md_files(cwd: Path) -> Path | None:
    current = cwd.resolve()

    if current.is_dir():
        agent_md_path = current / AGENT_MD_FILE_NAME
        if agent_md_path.is_file():
            content = agent_md_path.read_text(encoding="utf-8")
            return content

    return None


def _get_project_config(cwd: Path) -> Path | None:
    current = cwd.resolve()
    agent_dir = current / ".ai-agent"

    if agent_dir.is_dir():
        config_path = agent_dir / CONFIG_FILE_NAME
        if config_path.is_file():
            return config_path

    parent = current.parent
    if parent != current:
        return _get_project_config(parent)

    return None


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def load_config(cwd: Path | None) -> Config:
    cwd = cwd or Path.cwd()
    system_path = get_system_config_path()

    config_dict: dict[str, Any] = {}

    if system_path.is_file():
        try:
            config_dict = _parse_toml(system_path)
        except ConfigError as e:
            logger.warning(f"Skipping invalid system config file {system_path}: {e}")

    project_path = _get_project_config(cwd)
    if project_path:
        try:
            project_config_dict = _parse_toml(project_path)
            config_dict = _merge_dicts(config_dict, project_config_dict)
        except ConfigError as e:
            logger.warning(f"Skipping invalid project config file {project_path}: {e}")

    if "cwd" not in config_dict:
        config_dict["cwd"] = str(cwd)

    if "developer_instructions" not in config_dict:
        if agent_md_content := _get_agent_md_files(cwd):
            config_dict["developer_instructions"] = agent_md_content
    
    # Process subagent configurations if present
    if "subagents" in config_dict:
        subagents_data = config_dict.get("subagents", [])
        if isinstance(subagents_data, list):
            config_dict["subagents"] = _validate_and_parse_subagents(subagents_data)
        else:
            logger.warning("Invalid 'subagents' section in config (expected array), ignoring")
            config_dict["subagents"] = []

    try:
        config = Config(**config_dict)
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}") from e
    return config
