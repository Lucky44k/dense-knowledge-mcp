#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if command -v uv >/dev/null 2>&1; then
    uv tool install --force "${project_dir}[mcp]"
elif command -v pipx >/dev/null 2>&1; then
    pipx install --force "${project_dir}[mcp]"
else
    python_bin=${PYTHON:-python3}
    data_dir=${XDG_DATA_HOME:-"$HOME/.local/share"}
    install_dir="${data_dir}/dense-knowledge/venv"
    bin_dir="${HOME}/.local/bin"

    "$python_bin" -m venv "$install_dir"
    "$install_dir/bin/python" -m pip install --upgrade pip
    "$install_dir/bin/python" -m pip install "${project_dir}[mcp]"
    mkdir -p "$bin_dir"
    ln -sf "$install_dir/bin/mmp" "$bin_dir/mmp"
    ln -sf "$install_dir/bin/mmp-server" "$bin_dir/mmp-server"

    case ":${PATH}:" in
        *":${bin_dir}:"*) ;;
        *)
            printf '%s\n' \
                "Installed, but ${bin_dir} is not on PATH." \
                "Add it to your shell profile before running mmp."
            ;;
    esac
fi

printf '%s\n' \
    "Dense Knowledge is installed." \
    "Run 'mmp setup' to choose a memory directory and configure LM Studio."
