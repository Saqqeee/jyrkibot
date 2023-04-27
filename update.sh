#!/bin/bash
install_dir="/home/$(whoami)"
clone_dir="jyrkibot"
python_cmd="python3"
github="gh"
launch="main.py"

if [[ -d .git ]]
then
    install_dir="${PWD}/../"
    clone_dir="${PWD##*/}"
fi

cd "${install_dir}"/
if [[ -d "${clone_dir}" ]]
then
    cd "${clone_dir}"/
    "${github}" repo sync
    exec "${python_cmd}" main.py
fi