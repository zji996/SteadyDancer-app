from __future__ import annotations

"""
DFloat11 compression utility for SteadyDancer-14B (Wan I2V 14B).

This script compresses the Wan transformer backbone weights from BF16 to
DFloat11 and writes them into a separate directory, e.g.:

    models/SteadyDancer-14B        # original BF16 checkpoints
    models/SteadyDancer-14B-df11   # DFloat11-compressed transformer

It is intentionally designed to be generic and offline:

- It only depends on:
  - the upstream Wan implementation under `third_party/SteadyDancer`
  - the DFloat11 library (`dfloat11` pip package or `third_party/DFloat11`)
- It does NOT modify any application or worker code.

Typical usage from the repo root (using the worker env via uv):

  uv run --project apps/worker python scripts/compress_steadydancer_dfloat11.py

This will:
- Resolve the SteadyDancer checkpoint directory as:
    1. --ckpt-dir, if provided
    2. $STEADYDANCER_CKPT_DIR, if set
    3. <MODELS_DIR or ./models>/SteadyDancer-14B
- Write the compressed model into:
    <ckpt_dir>-df11  (e.g. models/SteadyDancer-14B-df11)

The script is single-process and by default runs DFloat11's bit-exact
correctness check on CUDA: this can be memory-heavy for 14B models.
Pass --no-check-correctness to disable the check if you hit CUDA OOM.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Tuple

import torch
import torch.nn as nn


def _get_repo_root() -> Path:
    # scripts/compress_steadydancer_dfloat11.py -> scripts -> repo_root
    return Path(__file__).resolve().parents[1]


def _get_models_dir() -> Path:
    """
    Compute the models root directory from MODELS_DIR.

    - If MODELS_DIR is set, use it as-is.
    - Otherwise, default to <repo_root>/models based on this file's location.
    """
    env_value = os.getenv("MODELS_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()

    repo_root = _get_repo_root()
    return (repo_root / "models").resolve()


def _get_steady_repo(repo_root: Path) -> Path:
    steady_repo = repo_root / "third_party" / "SteadyDancer"
    if not steady_repo.exists():
        raise SystemExit(
            f"Expected upstream SteadyDancer repo at {steady_repo}, "
            "but it does not exist."
        )
    if str(steady_repo) not in sys.path:
        sys.path.insert(0, str(steady_repo))
    return steady_repo


def _resolve_ckpt_dir(explicit: str | None) -> Path:
    """
    Resolve the SteadyDancer checkpoint directory.

    Priority:
      1. Explicit --ckpt-dir
      2. STEADYDANCER_CKPT_DIR environment variable
      3. <MODELS_DIR>/SteadyDancer-14B
    """
    if explicit:
        return Path(explicit).expanduser().resolve()

    env_dir = os.getenv("STEADYDANCER_CKPT_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    return (_get_models_dir() / "SteadyDancer-14B").resolve()


def _default_save_dir(ckpt_dir: Path, explicit: str | None) -> Path:
    """
    Resolve the output directory for DFloat11-compressed weights.

    - If --save-dir is provided, use it as-is.
    - Otherwise, use "<ckpt_dir>-df11".
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    return ckpt_dir.with_name(ckpt_dir.name + "-df11")


def _copy_auxiliary_files(src: Path, dst: Path) -> None:
    """
    Copy non-weight assets (tokenizer files, configs, README, etc.)
    from the original checkpoint directory into the DF11 directory.

    We intentionally skip:
      - 原始 diffusion BF16 权重：
          diffusion_pytorch_model-*.safetensors
          diffusion_pytorch_model.safetensors
          diffusion_pytorch_model.safetensors.index.json
      - 除 VAE 以外的 .pth / .safetensors 权重文件（如 T5 / CLIP），
        这些在 DF11 目录中仅以 DF11 子目录形式出现，避免重复存储原始权重。
      - 原始 config.json（DF11 会写入自己的 config.json，仅包含 dfloat11_config）。
      - Hidden lock/cursor directories (e.g. .lock) that are only used by
        download tools.
    """
    dst.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        name = item.name

        # Skip hidden cache/lock dirs to keep DF11 dir tidy.
        if name.startswith("."):
            continue

        # Skip original diffusion transformer weights and index.
        if name.startswith("diffusion_pytorch_model") and name.endswith(".safetensors"):
            continue
        if name == "diffusion_pytorch_model.safetensors.index.json":
            continue

        # Skip non-VAE .pth / .safetensors weight files (e.g. T5 / CLIP).
        # VAE 权重 Wan2.1_VAE.pth 需要保留在 DF11 目录中，保证完整性。
        if item.is_file() and item.suffix in {".pth", ".safetensors"} and name != "Wan2.1_VAE.pth":
            continue

        # Skip original config.json – DF11 will emit its own config.json.
        if name == "config.json":
            continue

        dest = dst / name
        if item.is_dir():
            if dest.exists():
                continue
            shutil.copytree(item, dest)
        else:
            if dest.exists():
                continue
            shutil.copy2(item, dest)


def _import_dfloat11(repo_root: Path):
    """
    Import the DFloat11 library.

    Preference:
      1. The installed `dfloat11` pip package.
      2. The vendored copy under third_party/DFloat11.
    """
    try:
        import dfloat11  # type: ignore[import]
        return dfloat11
    except ImportError:
        local_pkg = repo_root / "third_party" / "DFloat11"
        if local_pkg.exists():
            sys.path.insert(0, str(local_pkg))
            try:
                import dfloat11  # type: ignore[import]
                return dfloat11
            except ImportError:
                pass

    raise SystemExit(
        "ERROR: Could not import 'dfloat11'.\n"
        "Install it into the worker environment, for example:\n"
        "  uv run --project apps/worker pip install 'dfloat11[cuda12]'\n"
        "or ensure third_party/DFloat11 is available on PYTHONPATH."
    )


def _load_wan_model(ckpt_dir: Path) -> nn.Module:
    """
    Load the Wan diffusion backbone (WanModel) from a local checkpoint dir.

    This mirrors the upstream WanI2VDancer behavior, but only instantiates
    the transformer backbone. All weights are loaded on CPU in bfloat16.
    """
    repo_root = _get_repo_root()
    _get_steady_repo(repo_root)

    try:
        import wan  # type: ignore[import]
        from wan.modules.model_dancer import WanModel  # type: ignore[import]
    except Exception as exc:  # pragma: no cover - import-time failure
        raise SystemExit(
            "ERROR: Failed to import WanModel from third_party/SteadyDancer.\n"
            "Make sure the upstream submodule is checked out and its "
            "Python dependencies are satisfied."
        ) from exc

    print(f"[DF11] Loading WanModel.from_pretrained from {ckpt_dir} ...")
    model = WanModel.from_pretrained(
        str(ckpt_dir),
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=False,
    )
    model.eval()
    # Ensure all Linear/Embedding weights are in bfloat16 for DFloat11.
    model.to(torch.bfloat16)
    return model


def _build_pattern_dict(root_module: nn.Module) -> Dict[str, Tuple[str, ...]]:
    """
    Automatically build a DFloat11 pattern_dict for WanModel.

    Strategy:
      - Treat every nn.Linear / nn.Embedding under the root module as a
        separate DF11 block.
      - Use the fully-qualified module name as the regex pattern.
      - For simple Linear/Embedding modules, DFloat11 ignores attr_names
        and directly compresses the module's own `weight`.
    """
    pattern_dict: Dict[str, Tuple[str, ...]] = {}

    for name, module in root_module.named_modules():
        if isinstance(module, (nn.Linear, nn.Embedding)):
            pattern_dict[name] = ()

    if not pattern_dict:
        raise RuntimeError(
            "No Linear/Embedding modules found under WanModel; nothing to compress."
        )

    print(f"[DF11] Will compress {len(pattern_dict)} Linear/Embedding modules.")
    return pattern_dict


def _override_threads_per_block(dfloat11_module, threads_per_block: int | None) -> None:
    """
    Optionally override the global threads_per_block used by DFloat11.

    This mirrors the wrapper described in docs/DFloat11_intro.md and updates
    the internal `dfloat11.dfloat11.threads_per_block` tuple so that both
    compression and the saved dfloat11_config reflect the override.
    """
    if not threads_per_block or threads_per_block <= 0:
        return

    try:
        # Newer DFloat11 layouts.
        import dfloat11.dfloat11 as df11_internal  # type: ignore[import]
    except Exception:  # pragma: no cover - fallback for non-standard layouts
        df11_internal = dfloat11_module

    print(f"[DF11] Overriding threads_per_block to {threads_per_block}.")
    df11_internal.threads_per_block = (threads_per_block,)


def _patch_dfloat11_get_luts(dfloat11_module) -> None:
    """
    Monkey-patch dfloat11.get_luts to avoid the UnboundLocalError in the
    upstream implementation (curr_val referenced before assignment).

    The logic is copied from dfloat11_utils.get_luts, with one fix:
    - Initialize curr_val for each LUT row so that even if a byte value
      is not present in bytes_dict, we never read an undefined variable.
    """
    try:
        import dfloat11.dfloat11 as df11_internal  # type: ignore[import]
    except Exception:  # pragma: no cover - fallback if layout differs
        df11_internal = dfloat11_module

    import numpy as _np  # local aliases to avoid polluting global namespace
    import torch as _torch

    def _safe_get_luts(table):
        prefixes = [""]

        for key, (bits, val) in table.items():
            if isinstance(key, int):
                prefix = bin(val)[2:].rjust(bits, "0")[: ((bits - 1) // 8 * 8)]
                if prefix not in prefixes:
                    prefixes.append(prefix)

        prefixes.sort(key=len)

        luts = _np.zeros((len(prefixes), 256), dtype=_np.uint8)

        for pi, p in enumerate(prefixes):
            bytes_dict = {}
            pl = len(p) // 8
            for key, (bits, val) in table.items():
                if isinstance(key, int):
                    bin_val = bin(val)[2:].rjust(bits, "0")

                    if bin_val.startswith(p):
                        if (bits - 1) // 8 == pl:
                            dict_key = int(bin_val[(pl * 8) :].ljust(8, "0"), 2)
                            dict_value = key
                        else:
                            dict_key = int(bin_val[(pl * 8) : (pl * 8 + 8)], 2)
                            dict_value = 256 - prefixes.index(bin_val[: (pl * 8 + 8)])

                        if dict_key in bytes_dict and bytes_dict[dict_key] != dict_value:
                            raise ValueError(f"Key {dict_key} already exists in {bytes_dict}")
                        else:
                            bytes_dict[dict_key] = dict_value

            # Upstream implementation prints bytes_dict; keep for debugging.
            print(bytes_dict)

            # FIX: ensure curr_val is always initialized, even if bytes_dict is empty
            # or if the first few byte values are not present.
            curr_val = next(iter(bytes_dict.values()), 0)
            for i in range(256):
                if i in bytes_dict:
                    curr_val = bytes_dict[i]
                luts[pi, i] = curr_val

        lens = _np.zeros((1, 256), dtype=_np.uint8)
        for key, (bits, val) in table.items():
            if isinstance(key, int):
                lens[-1, key] = bits

        return _torch.from_numpy(_np.concatenate((luts, lens), axis=0))

    # Apply monkey patch.
    try:
        df11_internal.get_luts = _safe_get_luts  # type: ignore[assignment]
        print("[DF11] Patched dfloat11.get_luts with safe implementation.")
    except Exception:
        # Best effort – if patching fails, keep original behavior.
        print("[DF11] Warning: failed to patch dfloat11.get_luts; using upstream implementation.")


def _selective_compress_model(
    dfloat11_module,
    *,
    model: nn.Module,
    pattern_dict: Dict[str, Tuple[str, ...]],
    save_path: str,
    compression_threshold: float = 100.0,
) -> None:
    """
    A selective variant of dfloat11.compress_model:

    - 仅支持我们当前用到的场景：
      - pattern_dict 的 key 是完整 module 名（精确匹配），value 为空元组；
      - 只压缩 nn.Linear / nn.Embedding；
      - 只支持 save_single_file=True（写入一个 model.safetensors）。
    - 对每个模块计算实际压缩比：
        compressed_size / original_size * 100
      若压缩比 > compression_threshold（默认 100%）则跳过该模块，
      保留原始 BF16 权重。
    - 仅将实际参与 DF11 压缩的模块写入 dfloat11_config.pattern_dict。
    """
    import dfloat11.dfloat11 as df11_internal  # type: ignore[import]
    from safetensors.torch import save_file
    import numpy as np
    import re

    os.makedirs(save_path, exist_ok=True)

    bytes_per_thread = df11_internal.bytes_per_thread
    threads_per_block = df11_internal.threads_per_block
    version = df11_internal.version
    get_codec = df11_internal.get_codec
    get_32bit_codec = df11_internal.get_32bit_codec
    get_luts = df11_internal.get_luts
    encode_weights = df11_internal.encode_weights

    block_index = 0
    save_model = True
    compressed_patterns: set[str] = set()

    for pattern, attr_names in pattern_dict.items():
        # 目前我们只使用空 attr_names，且 pattern 是精确 module 名。
        if attr_names:
            raise RuntimeError(
                "Selective DF11 compression currently only supports empty attr_names."
            )

        for full_name, sub_module in model.named_modules():
            if not re.fullmatch(pattern, full_name):
                continue

            # 只处理 Linear / Embedding，其他类型模块跳过。
            if not isinstance(sub_module, (nn.Linear, nn.Embedding)):
                continue

            block_index += 1
            if block_index <= 0:
                # 目前不支持 block_range 子集，若需要可以扩展。
                continue

            weights: list[torch.Tensor] = []
            assert sub_module.weight.data.dtype == torch.bfloat16, (
                f"Expected weights to be in bfloat16 format for compression, "
                f"but '{full_name}' has dtype {sub_module.weight.data.dtype}"
            )
            weights.append(sub_module.weight.data.detach().cpu().flatten())

            total_elems = sum(w.numel() for w in weights)

            _codec, _counter = get_codec(torch.cat(weights))
            codec, _, table = get_32bit_codec(_counter)
            codec.print_code_table()

            luts = get_luts(table)

            encoded, other_8bits, output_positions, gaps, split_positions = encode_weights(
                weights, codec, bytes_per_thread, threads_per_block[0]
            )

            # 与 dfloat11_utils.encode_weights 中相同的压缩率计算方式。
            compressed_bytes = (
                encoded.numel()
                + other_8bits.numel()
                + output_positions.numel() * 4
                + gaps.numel()
            )
            original_bytes = total_elems * 2  # BF16: 2 bytes per element
            factor = compressed_bytes * 100.0 / original_bytes

            if factor > compression_threshold:
                print(
                    f"[DF11] Skipping module {full_name}: "
                    f"compression factor {factor:.2f}% > {compression_threshold}%."
                )
                # 保持原始权重，不删除 weight，也不注册 DF11 buffer。
                continue

            print(
                f"[DF11] Compressing module {full_name}: "
                f"compression factor {factor:.2f}% <= {compression_threshold}%."
            )

            # 删除原始权重，注册 DF11 buffer，行为与官方 compress_model 一致。
            delattr(sub_module, "weight")

            sub_module.register_buffer("luts", luts)
            sub_module.register_buffer("encoded_exponent", encoded)
            sub_module.register_buffer("sign_mantissa", other_8bits)
            sub_module.register_buffer(
                "output_positions", output_positions.view(torch.uint8)
            )
            sub_module.register_buffer("gaps", gaps)
            sub_module.register_buffer("split_positions", split_positions)

            compressed_patterns.add(pattern)

        if not save_model:
            break

    if save_model:
        # 仅将实际参与压缩的 pattern 写入 config。
        compressed_pattern_dict: Dict[str, Tuple[str, ...]] = {
            k: v for k, v in pattern_dict.items() if k in compressed_patterns
        }

        dfloat11_config = {
            "version": version,
            "threads_per_block": threads_per_block,
            "bytes_per_thread": bytes_per_thread,
            "pattern_dict": compressed_pattern_dict,
        }
        if hasattr(model, "config"):
            try:
                model.config.dfloat11_config = dfloat11_config
            except Exception:
                pass

        # 单文件 safetensors 输出。
        save_file(model.state_dict(), os.path.join(save_path, "model.safetensors"))

        # 写入 / 合并 config.json（若已有其他字段，保留原内容）。
        cfg_path = os.path.join(save_path, "config.json")
        save_config = True
        config: dict = {}
        if os.path.exists(cfg_path):
            try:
                import json as _json

                with open(cfg_path, "r", encoding="utf-8") as f:
                    config = _json.load(f)
                if "dfloat11_config" in config and isinstance(
                    config["dfloat11_config"], dict
                ):
                    save_config = False
            except Exception:
                # 如果现有 config.json 读失败，就覆盖它。
                config = {}
                save_config = True

        if save_config:
            import json as _json

            config["dfloat11_config"] = dfloat11_config
            with open(cfg_path, "w", encoding="utf-8") as f:
                _json.dump(config, f, indent=2)


def _compress_t5_encoder(
    *,
    dfloat11_module,
    ckpt_dir: Path,
    save_dir: Path,
    check_correctness: bool,
) -> None:
    """
    DF11-compress the T5 text encoder checkpoint used by Wan I2V 14B.

    Output layout:
      <save_dir>/t5_df11/
        - model.safetensors
        - config.json (with dfloat11_config)
    """
    repo_root = _get_repo_root()
    _get_steady_repo(repo_root)

    try:
        from wan.configs import WAN_CONFIGS  # type: ignore[import]
        from wan.modules.t5 import umt5_xxl  # type: ignore[import]
    except Exception as exc:  # pragma: no cover - import-time failure
        print(
            "[DF11][T5] Skipping T5 compression: failed to import wan configs or T5 modules.",
            file=sys.stderr,
        )
        return

    cfg = WAN_CONFIGS.get("i2v-14B")
    if cfg is None:
        print(
            "[DF11][T5] Skipping T5 compression: WAN_CONFIGS['i2v-14B'] not found.",
            file=sys.stderr,
        )
        return

    t5_ckpt = ckpt_dir / cfg.t5_checkpoint
    if not t5_ckpt.exists():
        print(
            f"[DF11][T5] Skipping T5 compression: checkpoint not found at {t5_ckpt}.",
            file=sys.stderr,
        )
        return

    t5_save_dir = save_dir / "t5_df11"
    if (t5_save_dir / "model.safetensors").exists():
        print(f"[DF11][T5] Detected existing DF11 T5 under {t5_save_dir}, skipping.")
        return

    t5_save_dir.mkdir(parents=True, exist_ok=True)

    print(f"[DF11][T5] Loading encoder weights from {t5_ckpt} ...")
    # Initialize encoder-only UMT5 in bfloat16 on CPU.
    model = umt5_xxl(
        encoder_only=True,
        return_tokenizer=False,
        dtype=torch.bfloat16,
        device="cpu",
    ).eval().requires_grad_(False)

    state_dict = torch.load(t5_ckpt, map_location="cpu")
    model.load_state_dict(state_dict)
    model.to(torch.bfloat16)

    pattern_dict = _build_pattern_dict(model)

    print(f"[DF11][T5] Compressing into {t5_save_dir} (selective) ...")
    if check_correctness:
        dfloat11_module.compress_model(
            model=model,
            pattern_dict=pattern_dict,
            save_path=str(t5_save_dir),
            block_range=[0, 10_000_000],
            save_single_file=True,
            check_correctness=True,
        )
    else:
        _selective_compress_model(
            dfloat11_module,
            model=model,
            pattern_dict=pattern_dict,
            save_path=str(t5_save_dir),
            compression_threshold=100.0,
        )


def _compress_clip_model(
    *,
    dfloat11_module,
    ckpt_dir: Path,
    save_dir: Path,
    check_correctness: bool,
) -> None:
    """
    DF11-compress the CLIP checkpoint used by Wan I2V 14B.

    Note: the original CLIP checkpoint is in float16; we instantiate the
    model in bfloat16 and let PyTorch convert the weights on load. The DF11
    model will therefore be bit-exact w.r.t. the BF16-converted weights, not
    the original FP16 checkpoint.

    Output layout:
      <save_dir>/clip_df11/
        - model.safetensors
        - config.json (with dfloat11_config)
    """
    repo_root = _get_repo_root()
    _get_steady_repo(repo_root)

    try:
        from wan.configs import WAN_CONFIGS  # type: ignore[import]
        from wan.modules.clip import clip_xlm_roberta_vit_h_14  # type: ignore[import]
    except Exception as exc:  # pragma: no cover - import-time failure
        print(
            "[DF11][CLIP] Skipping CLIP compression: failed to import wan configs or CLIP modules.",
            file=sys.stderr,
        )
        return

    cfg = WAN_CONFIGS.get("i2v-14B")
    if cfg is None:
        print(
            "[DF11][CLIP] Skipping CLIP compression: WAN_CONFIGS['i2v-14B'] not found.",
            file=sys.stderr,
        )
        return

    clip_ckpt = ckpt_dir / cfg.clip_checkpoint
    if not clip_ckpt.exists():
        print(
            f"[DF11][CLIP] Skipping CLIP compression: checkpoint not found at {clip_ckpt}.",
            file=sys.stderr,
        )
        return

    clip_save_dir = save_dir / "clip_df11"
    if (clip_save_dir / "model.safetensors").exists():
        print(
            f"[DF11][CLIP] Detected existing DF11 CLIP under {clip_save_dir}, skipping."
        )
        return

    clip_save_dir.mkdir(parents=True, exist_ok=True)

    print(f"[DF11][CLIP] Loading CLIP model and weights from {clip_ckpt} ...")
    # Initialize CLIP in bfloat16 on CPU; weights will be converted from FP16.
    model = clip_xlm_roberta_vit_h_14(
        pretrained=False,
        return_transforms=False,
        return_tokenizer=False,
        dtype=torch.bfloat16,
        device="cpu",
    )
    model = model.eval().requires_grad_(False)

    state_dict = torch.load(clip_ckpt, map_location="cpu")
    model.load_state_dict(state_dict)
    model.to(torch.bfloat16)

    pattern_dict = _build_pattern_dict(model)

    print(f"[DF11][CLIP] Compressing into {clip_save_dir} (selective) ...")
    if check_correctness:
        dfloat11_module.compress_model(
            model=model,
            pattern_dict=pattern_dict,
            save_path=str(clip_save_dir),
            block_range=[0, 10_000_000],
            save_single_file=True,
            check_correctness=True,
        )
    else:
        _selective_compress_model(
            dfloat11_module,
            model=model,
            pattern_dict=pattern_dict,
            save_path=str(clip_save_dir),
            compression_threshold=100.0,
        )



def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compress SteadyDancer-14B Wan transformer weights with DFloat11.",
    )
    parser.add_argument(
        "--ckpt-dir",
        type=str,
        default=None,
        help=(
            "Path to the SteadyDancer checkpoint directory. "
            "Defaults to $STEADYDANCER_CKPT_DIR or <MODELS_DIR>/SteadyDancer-14B."
        ),
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default=None,
        help=(
            "Directory where DF11-compressed weights will be written. "
            "Defaults to '<ckpt_dir>-df11', e.g. models/SteadyDancer-14B-df11."
        ),
    )
    parser.add_argument(
        "--threads-per-block",
        type=int,
        default=0,
        help=(
            "Override DFloat11 CUDA threads_per_block (global setting). "
            "Use 0 to keep the upstream default."
        ),
    )
    parser.add_argument(
        "--no-check-correctness",
        action="store_true",
        help=(
            "Disable DF11 GPU bit-for-bit correctness check. "
            "This saves VRAM and time but skips validation."
        ),
    )
    parser.add_argument(
        "--skip-t5",
        action="store_true",
        help="Skip DF11 compression for the T5 text encoder checkpoint.",
    )
    parser.add_argument(
        "--skip-clip",
        action="store_true",
        help="Skip DF11 compression for the CLIP checkpoint.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    repo_root = _get_repo_root()

    ckpt_dir = _resolve_ckpt_dir(args.ckpt_dir)
    if not ckpt_dir.exists():
        raise SystemExit(f"Checkpoint directory does not exist: {ckpt_dir}")

    # Basic sanity check that this looks like a Wan-style transformer dir.
    if not (ckpt_dir / "config.json").exists():
        raise SystemExit(f"No config.json found under checkpoint dir: {ckpt_dir}")
    if not any(ckpt_dir.glob("diffusion_pytorch_model-*.safetensors")) and not (
        ckpt_dir / "diffusion_pytorch_model.safetensors"
    ).exists():
        raise SystemExit(
            f"Expected diffusion_pytorch_model*.safetensors under {ckpt_dir}, "
            "but none were found."
        )

    save_dir = _default_save_dir(ckpt_dir, args.save_dir)
    save_dir.parent.mkdir(parents=True, exist_ok=True)

    print(f"Resolved SteadyDancer ckpt dir: {ckpt_dir}")
    print(f"DFloat11 output directory:     {save_dir}")

    # First copy over non-weight assets (configs, tokenizers, README, etc.)
    # so that <ckpt_dir>-df11 保留必要的元数据，但不重复原始 BF16 权重文件。
    print("[DF11] Copying non-weight assets into DF11 directory ...")
    _copy_auxiliary_files(ckpt_dir, save_dir)

    dfloat11_module = _import_dfloat11(repo_root)
    _patch_dfloat11_get_luts(dfloat11_module)
    _override_threads_per_block(dfloat11_module, args.threads_per_block)

    model = _load_wan_model(ckpt_dir)
    pattern_dict = _build_pattern_dict(model)

    print("[DF11] Starting compression (Wan diffusion backbone, selective) ...")
    if args.no_check_correctness:
        _selective_compress_model(
            dfloat11_module,
            model=model,
            pattern_dict=pattern_dict,
            save_path=str(save_dir),
            compression_threshold=100.0,
        )
    else:
        # 若需要开启 correctness check，则退回官方 compress_model 实现。
        dfloat11_module.compress_model(
            model=model,
            pattern_dict=pattern_dict,
            save_path=str(save_dir),
            block_range=[0, 10_000_000],
            save_single_file=True,
            check_correctness=True,
        )

    # Optionally compress the T5 text encoder checkpoint into a separate
    # DF11 directory under save_dir.
    if not args.skip_t5:
        _compress_t5_encoder(
            dfloat11_module=dfloat11_module,
            ckpt_dir=ckpt_dir,
            save_dir=save_dir,
            check_correctness=not args.no_check_correctness,
        )

    # Optionally compress the CLIP checkpoint into a separate DF11 directory.
    if not args.skip_clip:
        _compress_clip_model(
            dfloat11_module=dfloat11_module,
            ckpt_dir=ckpt_dir,
            save_dir=save_dir,
            check_correctness=not args.no_check_correctness,
        )

    print("\n[DF11] Compression completed.")
    print(f"DFloat11 model saved under: {save_dir}")
    print(
        "You can now point DFloat11Model.from_pretrained to this directory "
        "when wiring DF11 into your SteadyDancer pipeline."
    )


if __name__ == "__main__":
    main()
