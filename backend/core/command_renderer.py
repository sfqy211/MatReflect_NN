"""命令渲染器：根据 OperationDef + 请求参数 + 模型配置，渲染出可执行的命令行。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.core.config import PROJECT_ROOT
from backend.core.conda import build_python_runner
from backend.models.train import (
    OperationArgDef,
    OperationDef,
    PostActionDef,
    TrainModelItem,
)

_TEMPLATE_RE = re.compile(r"\{\{(\w+(?:\.\w+)*)\}\}")


# ─── 变量解析核心 ─────────────────────────────────────────────────────────────


def resolve_template(template: str, context: dict) -> Optional[str]:
    """解析模板字符串中的 {{var.path}} 占位符。
    
    返回解析后的字符串，如果任一必需变量缺失则返回 None。
    """
    def _replacer(match: re.Match) -> str:
        path = match.group(1)
        value = resolve_path(path, context)
        if value is None:
            # 标记缺失，让调用方跳过
            return _MISSING_SENTINEL
        return str(value)

    result = _TEMPLATE_RE.sub(_replacer, template)
    if _MISSING_SENTINEL in result:
        return None
    return result


_MISSING_SENTINEL = "\x00__MISSING__\x00"
_FLAG_ONLY_SENTINEL = "\x00__FLAG_ONLY__\x00"


def resolve_path(path: str, context: dict):
    """按点分路径从 context 中取值。
    
    支持：
      request.xxx       → context["request"]["xxx"]
      runtime.xxx       → context["model"].runtime.get("xxx")
      default_paths.xxx → context["model"].default_paths.get("xxx")
      item              → context.get("item")
      item.stem         → Path(item).stem
      item.path         → 由 input_dir_source + item 拼接
    """
    if path == "python":
        return context.get("python")
    if path == "script":
        return context.get("script")
    if path == "cwd":
        return context.get("cwd")
    if path == "item":
        item = context.get("item")
        return item
    if path == "item.stem":
        item = context.get("item")
        if item is None:
            return None
        return Path(str(item)).stem
    if path == "item.path":
        return _resolve_item_path(context)

    parts = path.split(".", 1)
    if len(parts) >= 2:
        prefix, rest = parts[0], parts[1]
        if prefix == "request":
            return context.get("request", {}).get(rest)
        if prefix == "runtime":
            return context["model"].runtime.get(rest, "")
        if prefix == "default_paths":
            return context["model"].default_paths.get(rest, "")
    return None


def _resolve_item_path(context: dict) -> Optional[str]:
    """根据 input_dir_source 和 item 解析出完整路径，并做 PROJECT_ROOT 逃逸防护。"""
    model: TrainModelItem = context["model"]
    item = context.get("item")
    input_dir_source = context.get("input_dir_source", "")
    if item is None:
        return None
    if input_dir_source:
        dir_val = resolve_path(input_dir_source, context)
        if dir_val:
            base_path = Path(str(dir_val))
            if not base_path.is_absolute():
                base_path = (PROJECT_ROOT / base_path).resolve()
            else:
                base_path = base_path.resolve()
            resolved = (base_path / str(item)).resolve()
        else:
            resolved = (PROJECT_ROOT / str(item)).resolve()
    else:
        resolved = (PROJECT_ROOT / str(item)).resolve()

    # 路径逃逸防护：必须限制在 PROJECT_ROOT 内
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        raise ValueError(
            f"路径越界: {resolved} 不在 PROJECT_ROOT ({PROJECT_ROOT}) 内"
        )
    return str(resolved)


def resolve_source(source: str, context: dict):
    """解析单变量 source（非模板）。"""
    return resolve_path(source, context)


# ─── 命令渲染 ─────────────────────────────────────────────────────────────────


def _get_python_runner(conda_env: str) -> Tuple[List[str], bool]:
    return build_python_runner(conda_env)


def _resolve_working_dir(operation: OperationDef, model: TrainModelItem, context: dict) -> Path:
    wd_source = operation.working_dir or ""
    if wd_source:
        wd_val = resolve_template(wd_source, context)
        if wd_val:
            p = Path(str(wd_val))
            return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
    # fallback: model.runtime.working_dir
    wd = model.runtime.get("working_dir", "")
    if wd:
        p = Path(wd)
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
    return PROJECT_ROOT


def _build_command(
    operation: OperationDef,
    model: TrainModelItem,
    context: dict,
    item_override: Optional[str] = None,
) -> List[str]:
    """根据 OperationDef 和 context 构建单条命令。"""
    context = dict(context)
    if item_override is not None:
        context["item"] = item_override

    # Python runner — operation 级 conda_env 优先于 model 级
    conda_env = (operation.conda_env or model.runtime.get("conda_env", "")).strip()
    runner, _ = _get_python_runner(conda_env)
    cmd: list[str] = list(runner)

    # Script
    script_val = operation.script
    script_resolved = ""
    if script_val:
        script_path = Path(script_val)
        if not script_path.is_absolute():
            script_path = (PROJECT_ROOT / script_path).resolve()
        cmd.append(str(script_path))
        script_resolved = str(script_path)
    context["script"] = script_resolved

    # CUDA_VISIBLE_DEVICES 由调用方处理（通过 environment）

    # Args
    for arg_def in operation.args:
        resolved = _resolve_arg(arg_def, context)
        if resolved is None:
            continue
        if resolved == _FLAG_ONLY_SENTINEL:
            # 纯布尔开关：仅追加 flag，不追加值
            if arg_def.flag:
                cmd.append(arg_def.flag)
            continue
        if isinstance(resolved, list):
            # 多个值（merge 模式）
            if arg_def.flag:
                cmd.append(arg_def.flag)
            cmd.extend(str(v) for v in resolved)
        else:
            if arg_def.flag:
                cmd.append(arg_def.flag)
            cmd.append(str(resolved))

    return cmd


def _resolve_arg(arg_def: OperationArgDef, context: dict):
    """解析单条参数定义。"""
    # 直接值
    if arg_def.raw_value:
        return arg_def.raw_value

    # 条件 flag（布尔开关，如 --keepon）
    if arg_def.condition_source and not arg_def.source:
        cond_val = resolve_source(arg_def.condition_source, context)
        if cond_val and str(cond_val).lower() in ("true", "1", "yes"):
            if arg_def.is_flag:
                return _FLAG_ONLY_SENTINEL  # 纯布尔开关，仅追加 flag
            return arg_def.flag
        return None

    # 条件判断：condition_source 为假时跳过
    if arg_def.condition_source:
        cond_val = resolve_source(arg_def.condition_source, context)
        if not cond_val or str(cond_val).lower() in ("false", "0", "no", ""):
            return None

    # 普通 source 解析
    if arg_def.source:
        val = resolve_source(arg_def.source, context)
        if val is None or (isinstance(val, str) and not val.strip()):
            if arg_def.default is not None:
                return arg_def.default
            return None
        return val

    # 回退
    return None


def _collect_merge_inputs(operation: OperationDef, context: dict) -> List[str]:
    """收集 merge 模式下所有循环项的路径。"""
    loop_source = operation.loop_source
    if not loop_source:
        return []
    items = resolve_source(loop_source, context)
    if not items or not isinstance(items, list):
        return []
    input_dir_source = operation.input_dir_source or ""
    merged: list[str] = []
    for item_name in items:
        ctx = dict(context)
        ctx["input_dir_source"] = input_dir_source
        ctx["item"] = item_name
        path_val = _resolve_item_path(ctx)
        if path_val:
            merged.append(str(path_val))
    return merged


# ─── 公开渲染接口 ─────────────────────────────────────────────────────────────


def render_commands(
    operation: OperationDef,
    model: TrainModelItem,
    request_params: dict,
) -> list[dict]:
    """渲染操作对应的所有命令（含循环展开）。
    
    返回列表，每个元素包含：
      - command: list[str] 命令
      - cwd: str 工作目录
      - conda_env: str conda 环境名
      - label: str 步骤标签
      - item: Optional[str] 循环项名称
    """
    context = _build_context(model, request_params, operation)
    conda_env = (operation.conda_env or model.runtime.get("conda_env", "")).strip()
    wd = _resolve_working_dir(operation, model, context)

    commands: list[dict] = []

    if operation.sub_operations:
        # 多步操作 — 由调用方自行展开
        return commands

    loop_source = operation.loop_source
    raw_items = resolve_source(loop_source, context) if loop_source else None
    items: list = raw_items if isinstance(raw_items, list) else []
    is_loop = len(items) > 0

    if is_loop and operation.merge_inputs:
        # Merge 模式：所有循环项合并到一条命令
        ctx = dict(context)
        ctx["input_dir_source"] = operation.input_dir_source or ""
        merged = _collect_merge_inputs(operation, context)
        merged_context = dict(context)
        merged_context["item"] = None
        # 对于 merge 模式，args 中的第一个 source 会被替换为合并列表
        # 我们需要特殊处理：用合并的路径列表替换第一个位置参数
        cmd_parts = _build_command(operation, model, merged_context)
        # 替换脚本后的第一个参数为合并列表
        # 实际上更简单：直接在 context 中设置 merged_inputs
        # 但当前 _build_command 不支持直接 inject 列表
        # 所以我们换个方式：手动构建命令
        
        # 重新构建 context，使第一个位置参数的值变成 merged list
        cmd = []
        runner, _ = _get_python_runner(conda_env)
        cmd.extend(runner)
        script_val = operation.script
        if script_val:
            sp = Path(script_val)
            cmd.append(str((PROJECT_ROOT / sp).resolve() if not sp.is_absolute() else str(sp.resolve())))

        # 第一个位置参数（source="item.path" 之类）用 merged 替代
        first_pos = True
        for arg_def in operation.args:
            if first_pos and not arg_def.flag and arg_def.source in ("item.path", "item"):
                # 替换为合并的路径列表
                if merged:
                    cmd.extend(merged)
                first_pos = False
                continue
            first_pos = False
            resolved = _resolve_arg(arg_def, merged_context)
            if resolved is None:
                continue
            if arg_def.flag:
                cmd.append(arg_def.flag)
            cmd.append(str(resolved))

        commands.append({
            "command": cmd,
            "cwd": str(wd),
            "conda_env": conda_env,
            "label": operation.label,
            "item": None,
        })
    elif is_loop:
        # 串行循环模式：每个循环项生成一条命令
        for idx, item_name in enumerate(items):
            ctx = dict(context)
            ctx["input_dir_source"] = operation.input_dir_source or ""
            ctx["item"] = item_name
            cmd = _build_command(operation, model, ctx, item_override=item_name)
            label = f"{operation.label} [{idx + 1}/{len(items)}]"
            commands.append({
                "command": cmd,
                "cwd": str(wd),
                "conda_env": conda_env,
                "label": label,
                "item": item_name,
            })
    else:
        # 无循环，单条命令
        cmd = _build_command(operation, model, context)
        commands.append({
            "command": cmd,
            "cwd": str(wd),
            "conda_env": conda_env,
            "label": operation.label,
            "item": None,
        })

    return commands


def _build_context(
    model: TrainModelItem,
    request_params: dict,
    operation: Optional[OperationDef] = None,
) -> dict:
    """构建渲染上下文。"""
    context: dict = {
        "request": request_params or {},
        "model": model,
        "python": None,  # 由 renderer 自己生成
        "script": None,
        "cwd": None,
        "input_dir_source": operation.input_dir_source if operation else "",
    }
    return context


def get_operation(
    model: TrainModelItem,
    operation_id: str,
) -> Optional[OperationDef]:
    """从模型定义中获取操作配置。"""
    if not model.operations:
        return None
    return model.operations.get(operation_id)


def has_operation(model: TrainModelItem, operation_id: str) -> bool:
    """检查模型是否支持指定操作。"""
    op = get_operation(model, operation_id)
    return op is not None


def get_sub_operations(
    model: TrainModelItem,
    operation_id: str,
) -> list[tuple[str, OperationDef]]:
    """获取多步操作的子操作列表。"""
    op = get_operation(model, operation_id)
    if not op or not op.sub_operations:
        return []
    result: list[tuple[str, OperationDef]] = []
    for sub_op_id in op.sub_operations:
        sub_op = get_operation(model, sub_op_id)
        if sub_op:
            result.append((sub_op_id, sub_op))
    return result


def render_preview(
    model: TrainModelItem,
    operation_id: str,
    request_params: dict,
    single_item: Optional[str] = None,
) -> list[dict]:
    """预览命令（不执行）。"""
    op = get_operation(model, operation_id)
    if not op:
        raise ValueError(f"模型 {model.key} 未定义操作: {operation_id}")
    
    if single_item:
        context = _build_context(model, request_params, op)
        conda_env = (op.conda_env or model.runtime.get("conda_env", "")).strip()
        wd = _resolve_working_dir(op, model, context)
        ctx = dict(context)
        ctx["input_dir_source"] = op.input_dir_source or ""
        ctx["item"] = single_item
        cmd = _build_command(op, model, ctx, item_override=single_item)
        return [{
            "command": cmd,
            "cwd": str(wd),
            "conda_env": conda_env,
            "label": f"{op.label} (preview)",
            "item": single_item,
        }]
    
    return render_commands(op, model, request_params)
