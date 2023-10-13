#!/bin/bash
install_dir="/home/$(whoami)"
clone_dir="jyrkibot"
python_cmd="python3"
github="gh"
launch="main.py"

# If .git is found in current working directory,
# reset the paths to make sure we get them right
if [[ -d .git ]]
then
    install_dir="${PWD}/../"
    clone_dir="${PWD##*/}"
fi

cd "${install_dir}"/
if [[ -d "${clone_dir}" ]]
then
    cd "${clone_dir}"/

    # Sync with the repository before doing anything stupid
    "${github}" repo sync

    # Create a virtual environment if one doesn't exist
    if [[ ! -d "/env " ]]
    then
        python -m venv env
    fi

    # Activate virtual environment and install pip-tools
    source env/bin/activate
    pip install pip-tools

    # Update dependencies and start the bot
    pip-sync
    exec "${python_cmd}" "${launch}"
fi